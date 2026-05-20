from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, UsageRecord, User, UserSubscription
from app.schemas.common import AuthUser, UsageReportRequest
from app.services.subscription_service import _ensure_daily_reset, _latest_subscription, _sync_user_preferences_subscription

DEFAULT_TRIAL_TOTAL_MINUTES = 180


def _get_user(db: Session, current_user: AuthUser) -> User:
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _ensure_default_trial_subscription(db: Session, username: str) -> UserSubscription:
    subscription = _latest_subscription(db, username)
    if subscription:
        _ensure_daily_reset(subscription)
        return subscription

    subscription = UserSubscription(
        username=username,
        package_code="trial_3h",
        plan_type="trial",
        plan_name="试用版",
        status="active",
        is_trial=True,
        trial_completed=False,
        total_minutes=DEFAULT_TRIAL_TOTAL_MINUTES,
        used_minutes=0,
        daily_limit_minutes=DEFAULT_TRIAL_TOTAL_MINUTES,
        daily_used_minutes=0,
        last_reset_date=date.today(),
        extra_payload={"autoCreated": True},
    )
    db.add(subscription)
    db.flush()
    return subscription


def report_usage(db: Session, current_user: AuthUser, data: UsageReportRequest) -> dict:
    user = _get_user(db, current_user)
    exam = db.query(Exam).filter(Exam.id == data.examId, Exam.user_id == current_user.username).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")

    subscription = _ensure_default_trial_subscription(db, current_user.username)
    _ensure_daily_reset(subscription)

    additional_minutes = max(int((data.usageSeconds + 59) // 60), 0)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)

    remaining_minutes_before = max(total_minutes - used_minutes, 0)
    remaining_daily_before = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes_before
    if total_minutes <= 0 or remaining_minutes_before <= 0 or (daily_limit_minutes > 0 and remaining_daily_before <= 0):
        snapshot = _sync_user_preferences_subscription(user, subscription)
        db.commit()
        return {
            "success": False,
            "examId": data.examId,
            "questionId": data.questionId or "",
            "usageType": data.usageType,
            "usageSeconds": data.usageSeconds,
            "addedMinutes": 0,
            "usedMinutes": subscription.used_minutes,
            "dailyUsedMinutes": subscription.daily_used_minutes,
            "remainingMinutes": snapshot["remainingMinutes"],
            "remainingDailyMinutes": snapshot["remainingDailyMinutes"],
            "allowed": False,
            "reason": "当前订阅额度不足",
        }

    billable_minutes = min(additional_minutes, remaining_minutes_before)
    if daily_limit_minutes > 0:
        billable_minutes = min(billable_minutes, remaining_daily_before)

    subscription.used_minutes = used_minutes + billable_minutes
    subscription.daily_used_minutes = daily_used_minutes + billable_minutes
    if subscription.used_minutes >= total_minutes:
        subscription.status = "inactive"

    record = UsageRecord(
        username=current_user.username,
        exam_id=data.examId,
        question_id=data.questionId,
        usage_type=data.usageType,
        usage_seconds=data.usageSeconds,
        billed_minutes=billable_minutes,
        extra_payload={"reportedMinutes": additional_minutes},
    )
    db.add(record)

    snapshot = _sync_user_preferences_subscription(user, subscription)
    db.commit()

    return {
        "success": True,
        "examId": data.examId,
        "questionId": data.questionId or "",
        "usageType": data.usageType,
        "usageSeconds": data.usageSeconds,
        "addedMinutes": billable_minutes,
        "usedMinutes": subscription.used_minutes,
        "dailyUsedMinutes": subscription.daily_used_minutes,
        "remainingMinutes": snapshot["remainingMinutes"],
        "remainingDailyMinutes": snapshot["remainingDailyMinutes"],
        "allowed": snapshot["canUse"],
        "subscriptionStatus": subscription.status,
    }
