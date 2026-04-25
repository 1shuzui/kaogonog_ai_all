import unittest

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
    def __init__(self, username, preferences=None):
        self.username = username
        self.preferences = preferences or {}


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
