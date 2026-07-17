"""
权益选择测试确认多份套餐并存时，后端扣减的是用户正在使用的那一份。

用户可能同时拥有月卡、小时包、人工补发和已退款权益；如果排序或每日重置逻辑错了，
就会出现剩余 60 分钟长期不减少、已失效权益被优先展示或扣错套餐的问题。

@param: 无；setUp 创建隔离数据库和多种权益组合。
@return: 无直接返回；断言通过表示权益选择、每日重置和扣减仍符合现网口径。
@raises ImportError: 订阅服务、ORM 模型或数据库依赖缺失时会失败。
"""
import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, User, UserSubscription
from app.schemas.common import AuthUser
from app.schemas.common import UsageReportRequest
from app.services.subscription_service import get_subscription_status, switch_subscription
from app.services.usage_service import report_usage


class SubscriptionSelectionTestCase(unittest.TestCase):
    """
    多权益选择用例集合，专门防止“最新权益、可用权益、用户选中的权益”三者混淆。

    微信支付、人工补发和退款都会让一个用户名下同时挂多份权益；这些用例直接验证服务层口径，
    避免只靠前端展示顺序判断该扣哪一份。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 权益选择、重置或扣减口径退化时由断言报告。
    """
    def setUp(self):
        """
        为每个用例创建独立内存库，避免套餐选择状态互相污染。

        这些用例关心排序和选中状态，复用数据库很容易把上一个用例的 active selection 带进来。

        @param: 无；测试框架自动调用。
        @return: None；数据库会话写入实例字段供用例使用。
        @raises AssertionError: 建库失败或表结构异常时由测试框架报告。
        """
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def _register_mysql_collation(dbapi_conn, _):
            dbapi_conn.create_collation(
                "utf8mb4_0900_ai_ci",
                lambda left, right: (left > right) - (left < right),
            )

        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        """
        关闭本用例数据库连接，确保下一条权益用例从干净状态开始。

        这里不做业务断言，只负责释放 SQLAlchemy 会话和内存库连接。

        @param: 无；测试框架自动调用。
        @return: None；关闭会话和引擎。
        @raises: 不主动抛出业务异常；连接释放异常会由测试框架暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_status_prefers_usable_paid_subscription_over_newer_inactive_subscription(self):
        """
        新创建但不可用的权益不能盖过仍可用的付费权益。

        退款或扣完的套餐通常比旧小时包更新；如果只按 created_at 排序，用户会看到“有余额却不能用”的假状态。

        @param: 无；构造一份可用小时包和一份更新的 inactive 月卡。
        @return: None；状态优先选择可用小时包时通过。
        @raises AssertionError: 后端错误优先返回不可用权益时失败。
        """
        user = User(username="ssy", hashed_password="x")
        paid = UserSubscription(
            username="ssy",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时套餐",
            status="active",
            is_trial=False,
            total_minutes=180,
            used_minutes=18,
            daily_limit_minutes=180,
            daily_used_minutes=6,
            last_reset_date=date.today(),
            created_at=datetime.now() - timedelta(minutes=10),
        )
        inactive_newer = UserSubscription(
            username="ssy",
            package_code="monthly_1h_day",
            plan_type="monthly",
            plan_name="包月每日1小时",
            status="inactive",
            is_trial=False,
            total_minutes=1800,
            used_minutes=1800,
            daily_limit_minutes=60,
            daily_used_minutes=60,
            last_reset_date=date.today(),
            created_at=datetime.now(),
        )
        self.db.add_all([user, paid, inactive_newer])
        self.db.commit()

        status = get_subscription_status(self.db, AuthUser(username="ssy"))

        self.assertEqual(status["packageCode"], "trial_3h")
        self.assertTrue(status["canUse"])
        self.assertEqual(status["remainingMinutes"], 162)
        self.assertEqual(status["remainingDailyMinutes"], 162)

    def test_status_resets_stale_daily_usage_before_calculating_remaining(self):
        """
        跨天后先清零每日已用，再计算当天剩余时长。

        包月每日限额和小时包日限额都依赖这个重置；顺序反了会让用户第二天仍被昨天用量拦住。

        @param: 无；构造 last_reset_date 为昨天的权益。
        @return: None；每日用量归零且总余额不变时通过。
        @raises AssertionError: 每日用量没有重置或余额计算顺序错误时失败。
        """
        user = User(username="ssy", hashed_password="x")
        subscription = UserSubscription(
            username="ssy",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时套餐",
            status="active",
            is_trial=False,
            total_minutes=180,
            used_minutes=18,
            daily_limit_minutes=180,
            daily_used_minutes=18,
            last_reset_date=date.today() - timedelta(days=1),
        )
        self.db.add_all([user, subscription])
        self.db.commit()

        status = get_subscription_status(self.db, AuthUser(username="ssy"))

        self.assertEqual(status["dailyUsedMinutes"], 0)
        self.assertEqual(status["remainingMinutes"], 162)
        self.assertEqual(status["remainingDailyMinutes"], 162)

    def test_status_keeps_multiple_entitlements_and_allows_switching_active_one(self):
        """
        多份有效权益要全部返回，同时允许用户切换当前扣减目标。

        用户可能买了月卡又保留小时包；页面需要看到完整权益列表，后端也要记住用户选择的是哪一份。

        @param: 无；构造小时包和月卡两份 active 权益。
        @return: None；列表完整且切换后只有一份 active selection 时通过。
        @raises AssertionError: 权益被丢失、选中状态重复或切换失败时失败。
        """
        user = User(username="ssy", hashed_password="x")
        hourly = UserSubscription(
            username="ssy",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时套餐",
            status="active",
            is_trial=False,
            total_minutes=180,
            used_minutes=61,
            daily_limit_minutes=180,
            daily_used_minutes=49,
            last_reset_date=date.today(),
            created_at=datetime.now() - timedelta(days=1),
        )
        monthly = UserSubscription(
            username="ssy",
            package_code="monthly_1h_day",
            plan_type="monthly",
            plan_name="包月套餐 1小时/天",
            status="active",
            is_trial=False,
            total_minutes=1800,
            used_minutes=0,
            daily_limit_minutes=60,
            daily_used_minutes=0,
            last_reset_date=date.today(),
            created_at=datetime.now(),
        )
        self.db.add_all([user, hourly, monthly])
        self.db.commit()

        status = get_subscription_status(self.db, AuthUser(username="ssy"))

        self.assertEqual(status["packageCode"], "monthly_1h_day")
        self.assertEqual(status["activePlanCount"], 2)
        self.assertTrue(status["stacked"])
        self.assertEqual({item["packageCode"] for item in status["entitlements"]}, {"trial_3h", "monthly_1h_day"})

        switched = switch_subscription(self.db, AuthUser(username="ssy"), hourly.id)

        self.assertEqual(switched["packageCode"], "trial_3h")
        self.assertEqual(switched["activeSubscriptionId"], hourly.id)
        active_items = [item for item in switched["entitlements"] if item["isActiveSelection"]]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["packageCode"], "trial_3h")

    def test_expired_active_subscription_is_not_reported_as_usable(self):
        """
        到期但 status 仍是 active 的权益，不能再被快照当作可用。

        这类历史脏数据会让前台显示 active、剩余很多分钟，但实际接口因过期校验拒绝使用。

        @param: 无；构造 end_at 已过期但 status 仍为 active 的订阅。
        @return: None；快照和 preferences 都应将其视为不可用。
        @raises AssertionError: 过期权益仍被展示为可用时失败。
        """
        user = User(username="ssy", hashed_password="x")
        expired = UserSubscription(
            username="ssy",
            package_code="monthly_1h_day",
            plan_type="monthly",
            plan_name="包月套餐 1小时/天",
            status="active",
            is_trial=False,
            total_minutes=1800,
            used_minutes=49,
            daily_limit_minutes=60,
            daily_used_minutes=0,
            last_reset_date=date.today(),
            start_at=datetime(2026, 5, 23, 7, 37, 10),
            end_at=datetime(2026, 6, 22, 7, 37, 10),
            created_at=datetime(2026, 5, 23, 7, 37, 11),
        )
        self.db.add_all([user, expired])
        self.db.commit()

        status = get_subscription_status(self.db, AuthUser(username="ssy"))

        self.assertEqual(status["planType"], "trial")
        self.assertTrue(status["isTrialUser"])
        self.assertTrue(status["canUse"])
        self.assertEqual(status["remainingMinutes"], 180)
        self.assertEqual(status["remainingDailyMinutes"], 180)
        self.assertEqual(status["activePlanCount"], 0)
        self.assertEqual(status["entitlements"], [])
        self.assertNotIn("activeSubscriptionId", user.preferences)

    def test_usage_rejects_expired_active_subscription_without_deducting(self):
        """
        用量上报不能扣减已过期但 status 仍为 active 的权益。

        即使历史 preferences 还指向过期权益，服务端也要在扣量前重新检查有效期。

        @param: 无；构造过期月卡和一次考试记录。
        @return: None；上报失败且权益用量不变时通过。
        @raises AssertionError: 过期权益被扣减或返回成功时失败。
        """
        user = User(username="ssy", hashed_password="x")
        expired = UserSubscription(
            username="ssy",
            package_code="monthly_1h_day",
            plan_type="monthly",
            plan_name="包月套餐 1小时/天",
            status="active",
            is_trial=False,
            total_minutes=1800,
            used_minutes=49,
            daily_limit_minutes=60,
            daily_used_minutes=0,
            last_reset_date=date.today(),
            start_at=datetime(2026, 5, 23, 7, 37, 10),
            end_at=datetime(2026, 6, 22, 7, 37, 10),
            created_at=datetime(2026, 5, 23, 7, 37, 11),
        )
        exam = Exam(id="exam_expired", user_id="ssy", question_ids=["q002"])
        self.db.add_all([user, expired, exam])
        self.db.commit()

        result = report_usage(
            self.db,
            AuthUser(username="ssy"),
            UsageReportRequest(examId="exam_expired", questionId="q002", usageSeconds=61),
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["allowed"])
        self.assertEqual(result["subscriptionId"], expired.id)
        self.assertEqual(expired.used_minutes, 49)
        status = get_subscription_status(self.db, AuthUser(username="ssy"))
        self.assertEqual(status["planType"], "trial")
        self.assertEqual(status["entitlements"], [])

    def test_usage_deducts_selected_entitlement(self):
        """
        上报训练用量时必须扣用户当前选中的权益。

        这是“时长似乎没有削减”这类问题的核心防线：如果服务层忽略 active selection，
        用户切到小时包后仍可能扣月卡，或者反过来显示不一致。

        @param: 无；先切到小时包，再上报 61 秒训练用量。
        @return: None；只扣选中的小时包、月卡不变时通过。
        @raises AssertionError: 扣错权益或扣减分钟进位错误时失败。
        """
        user = User(username="ssy", hashed_password="x")
        hourly = UserSubscription(
            username="ssy",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时套餐",
            status="active",
            is_trial=False,
            total_minutes=180,
            used_minutes=61,
            daily_limit_minutes=180,
            daily_used_minutes=49,
            last_reset_date=date.today(),
            created_at=datetime.now() - timedelta(days=1),
        )
        monthly = UserSubscription(
            username="ssy",
            package_code="monthly_1h_day",
            plan_type="monthly",
            plan_name="包月套餐 1小时/天",
            status="active",
            is_trial=False,
            total_minutes=1800,
            used_minutes=0,
            daily_limit_minutes=60,
            daily_used_minutes=0,
            last_reset_date=date.today(),
            created_at=datetime.now(),
        )
        exam = Exam(id="exam_switch", user_id="ssy", question_ids=["q002"])
        self.db.add_all([user, hourly, monthly, exam])
        self.db.commit()
        switch_subscription(self.db, AuthUser(username="ssy"), hourly.id)

        result = report_usage(
            self.db,
            AuthUser(username="ssy"),
            UsageReportRequest(examId="exam_switch", questionId="q002", usageSeconds=61),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["subscriptionId"], hourly.id)
        self.assertEqual(result["packageCode"], "trial_3h")
        self.assertEqual(hourly.used_minutes, 63)
        self.assertEqual(monthly.used_minutes, 0)


if __name__ == "__main__":
    unittest.main()
