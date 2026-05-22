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
    def __init__(self, username, preferences=None, subscriptions=None):
        self.username = username
        self.preferences = preferences or {}
        self.subscriptions = subscriptions or []


class DummySubscription:
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
    def __init__(self, is_admin=False, can_access_premium=False):
        self.isAdmin = is_admin
        self.permissions = {"canAccessPremiumModules": can_access_premium}


class AccessControlTestCase(unittest.TestCase):
    def test_normalize_billing_state_defaults_to_trial(self):
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
        context = build_access_context(DummyUser("admin"))
        self.assertEqual(context["role"], "admin")
        self.assertTrue(context["isAdmin"])
        self.assertTrue(context["billing"]["isPaid"])
        self.assertTrue(context["permissions"]["canManageQuestionBank"])

    def test_build_access_context_uses_active_subscription(self):
        context = build_access_context(DummyUser("ssy", subscriptions=[DummySubscription(used_minutes=3)]))

        self.assertTrue(context["billing"]["isPaid"])
        self.assertEqual(context["billing"]["planType"], BILLING_PLAN_HOURLY)
        self.assertEqual(context["billing"]["remainingMinutes"], 177)
        self.assertEqual(context["billing"]["remainingSeconds"], 10620)
        self.assertTrue(context["permissions"]["canAccessPremiumModules"])

    def test_build_access_context_caps_daily_remaining_at_total_remaining(self):
        subscription = DummySubscription(used_minutes=18, daily_used_minutes=6)
        subscription.last_reset_date = date.today()

        context = build_access_context(DummyUser("ssy", subscriptions=[subscription]))

        self.assertEqual(context["billing"]["remainingMinutes"], 162)
        self.assertEqual(context["billing"]["remainingDailyMinutes"], 162)

    def test_trial_user_only_can_start_trial_question(self):
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_exam_start_access(trial_user, [TRIAL_QUESTION_ID])

        with self.assertRaises(HTTPException):
            ensure_exam_start_access(trial_user, ["q002"])

    def test_trial_user_only_can_read_trial_question(self):
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_question_read_access(trial_user, TRIAL_QUESTION_ID)

        with self.assertRaises(HTTPException):
            ensure_question_read_access(trial_user, "q002")

    def test_trial_user_random_questions_are_limited_to_single_item(self):
        trial_user = DummyAuthUser(is_admin=False, can_access_premium=False)
        ensure_random_question_access(trial_user, 1)

        with self.assertRaises(HTTPException):
            ensure_random_question_access(trial_user, 5)


if __name__ == "__main__":
    unittest.main()
