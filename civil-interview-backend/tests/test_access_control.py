"""
这个测试文件守住 `test_access_control` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    DummyUser 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def __init__(self, username, preferences=None, subscriptions=None):
        self.username = username
        self.preferences = preferences or {}
        self.subscriptions = subscriptions or []


class DummySubscription:
    """
    DummySubscription 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
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
    DummyAuthUser 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def __init__(self, is_admin=False, can_access_premium=False):
        self.isAdmin = is_admin
        self.permissions = {"canAccessPremiumModules": can_access_premium}


class AccessControlTestCase(unittest.TestCase):
    """
    AccessControlTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def test_normalize_billing_state_defaults_to_trial(self):
        """
        test_normalize_billing_state_defaults_to_trial 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_paid_access_accepts_active_monthly_and_hourly 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_build_access_context_marks_admin_as_paid 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        context = build_access_context(DummyUser("admin"))
        self.assertEqual(context["role"], "admin")
        self.assertTrue(context["isAdmin"])
        self.assertTrue(context["billing"]["isPaid"])
        self.assertTrue(context["permissions"]["canManageQuestionBank"])

    def test_build_access_context_uses_active_subscription(self):
        """
        test_build_access_context_uses_active_subscription 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        context = build_access_context(DummyUser("ssy", subscriptions=[DummySubscription(used_minutes=3)]))

        self.assertTrue(context["billing"]["isPaid"])
        self.assertEqual(context["billing"]["planType"], BILLING_PLAN_HOURLY)
        self.assertEqual(context["billing"]["remainingMinutes"], 177)
        self.assertEqual(context["billing"]["remainingSeconds"], 10620)
        self.assertTrue(context["permissions"]["canAccessPremiumModules"])

    def test_build_access_context_caps_daily_remaining_at_total_remaining(self):
        """
        test_build_access_context_caps_daily_remaining_at_total_remaining 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        subscription = DummySubscription(used_minutes=18, daily_used_minutes=6)
        subscription.last_reset_date = date.today()

        context = build_access_context(DummyUser("ssy", subscriptions=[subscription]))

        self.assertEqual(context["billing"]["remainingMinutes"], 162)
        self.assertEqual(context["billing"]["remainingDailyMinutes"], 162)

    def test_trial_user_only_can_start_trial_question(self):
        """
        test_trial_user_only_can_start_trial_question 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_exam_start_access(trial_user, [TRIAL_QUESTION_ID])

        with self.assertRaises(HTTPException):
            ensure_exam_start_access(trial_user, ["q002"])

    def test_trial_user_only_can_read_trial_question(self):
        """
        test_trial_user_only_can_read_trial_question 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_question_read_access(trial_user, TRIAL_QUESTION_ID)

        with self.assertRaises(HTTPException):
            ensure_question_read_access(trial_user, "q002")

    def test_trial_user_random_questions_are_limited_to_single_item(self):
        """
        test_trial_user_random_questions_are_limited_to_single_item 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
        """
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_random_question_access(trial_user, 1)

        with self.assertRaises(HTTPException):
            ensure_random_question_access(trial_user, 5)


if __name__ == "__main__":
    unittest.main()
