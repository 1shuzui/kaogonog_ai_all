"""
访问控制测试关注“谁能开始/读取哪些题”这一层硬边界。

小程序审核要求未登录用户可以先浏览，但真正开始试用题、随机练习或付费训练时必须被后端再次拦截；
同时管理员账号和人工权益会绕过部分前端入口，所以这些用例直接测试 `app.core.access`，避免只靠页面显隐造成越权。

@param: 无；测试数据由本文件内的轻量假用户和假权益对象构造。
@return: 无直接返回；pytest/unittest 通过断言结果判断访问边界是否仍然有效。
@raises ImportError: 访问控制常量、FastAPI 异常类或项目包路径缺失时，导入阶段会失败。
"""
import unittest
from datetime import date

from fastapi import HTTPException

from app.core.access import (
    BILLING_PLAN_HOURLY,
    BILLING_PLAN_MONTHLY,
    BILLING_PLAN_TRIAL,
    TRIAL_QUESTION_ID,
    build_access_context,
    ensure_exam_start_access,
    ensure_question_read_access,
    ensure_random_question_access,
    has_paid_access_from_billing,
    normalize_billing_state,
)


class DummyUser:
    """
    构造最小用户对象，专门模拟访问控制真正读取的字段。

    不使用 ORM User 是为了让这些用例只验证权限规则，不被数据库默认值、关系加载或会话状态干扰。

    @param username: 用来触发管理员识别或普通用户权益判断的用户名。
    @param preferences: 用户偏好快照，覆盖旧 billing 字段兼容场景。
    @param subscriptions: 用户拥有的权益对象列表，用于验证新订阅表优先级。
    @return: 可传给 `build_access_context` 的轻量用户替身。
    @raises: 不主动抛出异常；字段缺失风险由访问控制函数暴露。
    """
    def __init__(self, username, preferences=None, subscriptions=None):
        self.username = username
        self.preferences = preferences or {}
        self.subscriptions = subscriptions or []


class DummySubscription:
    """
    构造最小权益对象，覆盖小时包、月卡、试用和已失效权益的组合。

    访问控制只关心剩余分钟、每日限额、状态和试用标记；用轻量对象能把测试焦点固定在扣时规则上。

    @param plan_type: 套餐类型，区分小时包、月卡和试用。
    @param plan_name: 展示给前端的套餐名称。
    @param total_minutes: 权益总分钟数。
    @param used_minutes: 已消耗分钟数。
    @param daily_limit_minutes: 每日可用上限。
    @param daily_used_minutes: 当日已用分钟数。
    @param status: 权益状态，测试 active/refunded/expired 等边界。
    @param is_trial: 是否试用权益，影响试用题访问范围。
    @return: 可传给访问控制上下文构造函数的权益替身。
    @raises: 不主动抛出异常；非法组合会在断言中暴露。
    """
    def __init__(
        self,
        plan_type=BILLING_PLAN_HOURLY,
        plan_name="3小时套餐",
        total_minutes=180,
        used_minutes=0,
        daily_limit_minutes=180,
        daily_used_minutes=0,
        status="active",
        is_trial=False,
    ):
        self.id = 1
        self.created_at = None
        self.status = status
        self.is_trial = is_trial
        self.plan_type = plan_type
        self.plan_name = plan_name
        self.total_minutes = total_minutes
        self.used_minutes = used_minutes
        self.daily_limit_minutes = daily_limit_minutes
        self.daily_used_minutes = daily_used_minutes
        self.last_reset_date = None
        self.end_at = None


class DummyAuthUser:
    """
    构造接口鉴权后用户对象，专门验证“按钮之外”的后端拦截。

    前端可以隐藏入口，但试用题、随机题和管理员权限最终都必须由后端字段决定。

    @param is_admin: 是否管理员，用于验证管理员绕过付费限制但不绕过管理权限。
    @param can_access_premium: 是否拥有付费模块访问权。
    @return: 可传给 `ensure_*_access` 的鉴权用户替身。
    @raises: 不主动抛出异常；权限不足由被测函数抛出 HTTPException。
    """
    def __init__(self, is_admin=False, can_access_premium=False):
        self.isAdmin = is_admin
        self.permissions = {"canAccessPremiumModules": can_access_premium}


class AccessControlTestCase(unittest.TestCase):
    """
    访问控制用例集合，覆盖试用、付费、管理员和每日限额几条最容易混淆的路径。

    这些断言不关心页面怎么展示，只确认服务端最终裁决不会因为前端改版而漂移。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 任一权限边界退化时由断言报告。
    """
    def test_normalize_billing_state_defaults_to_trial(self):
        """
        空 billing 快照必须落到试用态，而不是误判成付费或管理员。

        老用户偏好里可能没有新订阅字段；默认值保守一点，可以避免未付费用户直接进入训练。

        @param: 无；直接传入空字典。
        @return: None；默认快照符合试用口径时通过。
        @raises AssertionError: 默认 billing 口径被改成非试用态时失败。
        """
        self.assertEqual(
            normalize_billing_state({}),
            {
                "planType": BILLING_PLAN_TRIAL,
                "remainingSeconds": 0,
                "monthlyExpireAt": 0,
                "activatedAt": 0,
                "orderHistory": [],
            },
        )

    def test_paid_access_accepts_active_monthly_and_hourly(self):
        """
        月卡看过期时间，小时包看剩余秒数，两套付费判断不能混用。

        微信虚拟支付同时售卖包月和时长权益；如果只按一种字段判断，会让有效套餐被误拦或过期套餐继续可用。

        @param: 无；构造三种 billing 快照直接测试。
        @return: None；付费状态按套餐类型正确识别时通过。
        @raises AssertionError: 月卡/小时包判断口径混淆时失败。
        """
        self.assertTrue(
            has_paid_access_from_billing(
                {"planType": BILLING_PLAN_MONTHLY, "monthlyExpireAt": 2_000},
                now_ms=1_000,
            )
        )
        self.assertTrue(
            has_paid_access_from_billing(
                {"planType": BILLING_PLAN_HOURLY, "remainingSeconds": 600},
                now_ms=1_000,
            )
        )
        self.assertFalse(
            has_paid_access_from_billing(
                {"planType": BILLING_PLAN_MONTHLY, "monthlyExpireAt": 500},
                now_ms=1_000,
            )
        )

    def test_build_access_context_marks_admin_as_paid(self):
        """
        管理员在调试和维护时要视作有付费访问权。

        管理员可能需要进入题库、定向备面和评分页面排查问题，但这不应该依赖真实订单或人工补发权益。

        @param: 无；用 admin 用户名触发管理员上下文。
        @return: None；管理员权限和付费态同步生效时通过。
        @raises AssertionError: 管理员无法访问付费模块或管理权限缺失时失败。
        """
        context = build_access_context(DummyUser("admin"))
        self.assertEqual(context["role"], "admin")
        self.assertTrue(context["isAdmin"])
        self.assertTrue(context["billing"]["isPaid"])
        self.assertTrue(context["permissions"]["canManageQuestionBank"])

    def test_build_access_context_uses_active_subscription(self):
        """
        访问上下文必须优先读取当前有效订阅表，而不是只信旧 preferences 快照。

        人工补发、退款扣减和微信支付确认都会改 `user_subscriptions`；旧快照滞后时仍要展示真实余额。

        @param: 无；构造已用 3 分钟的小时包。
        @return: None；剩余分钟和付费权限来自有效权益时通过。
        @raises AssertionError: 仍按旧快照或错误权益计算余额时失败。
        """
        context = build_access_context(DummyUser("ssy", subscriptions=[DummySubscription(used_minutes=3)]))

        self.assertTrue(context["billing"]["isPaid"])
        self.assertEqual(context["billing"]["planType"], BILLING_PLAN_HOURLY)
        self.assertEqual(context["billing"]["remainingMinutes"], 177)
        self.assertEqual(context["billing"]["remainingSeconds"], 10620)
        self.assertTrue(context["permissions"]["canAccessPremiumModules"])

    def test_build_access_context_caps_daily_remaining_at_total_remaining(self):
        """
        每日剩余额不能大于总剩余额。

        用户问过“60 分钟怎么没有扣减”，这类问题常来自日限额和总余额显示口径不一致。

        @param: 无；构造总余额小于日限额余额的权益。
        @return: None；每日可用被总剩余分钟封顶时通过。
        @raises AssertionError: 页面可能显示超过真实可用时长时失败。
        """
        subscription = DummySubscription(used_minutes=18, daily_used_minutes=6)
        subscription.last_reset_date = date.today()

        context = build_access_context(DummyUser("ssy", subscriptions=[subscription]))

        self.assertEqual(context["billing"]["remainingMinutes"], 162)
        self.assertEqual(context["billing"]["remainingDailyMinutes"], 162)

    def test_trial_user_only_can_start_trial_question(self):
        """
        试用用户只能开始固定试用题，不能借随机题或真实题库绕过权益。

        审核要求先浏览后登录，但真正试用仍要记录账号状态；这个边界防止试用入口扩大成免费训练入口。

        @param: 无；构造无付费权限的普通用户。
        @return: None；固定试用题放行、普通题拒绝时通过。
        @raises HTTPException: 被测函数按预期拒绝非试用题。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_exam_start_access(trial_user, [TRIAL_QUESTION_ID])

        with self.assertRaises(HTTPException):
            ensure_exam_start_access(trial_user, ["q002"])

    def test_trial_user_only_can_read_trial_question(self):
        """
        试用用户读取题目详情也只能读固定试用题。

        只限制开始考试不够，题库详情页或历史入口也可能直接请求题目内容。

        @param: 无；构造无付费权限的普通用户。
        @return: None；固定试用题可读、普通题不可读时通过。
        @raises HTTPException: 被测函数按预期拒绝非试用题。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_question_read_access(trial_user, TRIAL_QUESTION_ID)

        with self.assertRaises(HTTPException):
            ensure_question_read_access(trial_user, "q002")

    def test_trial_user_random_questions_are_limited_to_single_item(self):
        """
        试用用户随机抽题最多只能请求 1 道。

        这个限制防止未付费用户通过批量随机接口一次性拿到多题。

        @param: 无；构造无付费权限的普通用户。
        @return: None；单题放行、多题拒绝时通过。
        @raises HTTPException: 被测函数按预期拒绝批量抽题。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_random_question_access(trial_user, 1)

        with self.assertRaises(HTTPException):
            ensure_random_question_access(trial_user, 5)


if __name__ == "__main__":
    unittest.main()
