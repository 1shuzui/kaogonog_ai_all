import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, User, UserSubscription
from app.schemas.common import AuthUser
from app.schemas.common import UsageReportRequest
from app.services.subscription_service import get_subscription_status, switch_subscription
from app.services.usage_service import report_usage


class SubscriptionSelectionTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_status_prefers_usable_paid_subscription_over_newer_inactive_subscription(self):
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

    def test_usage_deducts_selected_entitlement(self):
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
