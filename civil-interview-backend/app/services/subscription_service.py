from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import User, UserSubscription
from app.schemas.common import AuthUser

DEFAULT_TRIAL_TOTAL_MINUTES = 180


def _get_user(db: Session, current_user: AuthUser) -> User:
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _ensure_daily_reset(subscription: UserSubscription) -> None:
    today = date.today()
    if subscription.last_reset_date != today:
        subscription.daily_used_minutes = 0
        subscription.last_reset_date = today


def _latest_subscription(db: Session, username: str) -> UserSubscription | None:
    subscriptions = db.query(UserSubscription).filter(UserSubscription.username == username).order_by(
        UserSubscription.created_at.desc(),
        UserSubscription.id.desc(),
    )
    return subscriptions.first()


def _sync_user_preferences_subscription(user: User, subscription: UserSubscription | None) -> dict:
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    if not subscription:
        prefs["subscription"] = {
            "isTrialUser": True,
            "trialCompleted": False,
            "hasActivePlan": True,
            "planType": "trial",
            "planName": "试用版",
            "status": "active",
            "totalMinutes": DEFAULT_TRIAL_TOTAL_MINUTES,
            "usedMinutes": 0,
            "dailyLimitMinutes": DEFAULT_TRIAL_TOTAL_MINUTES,
            "dailyUsedMinutes": 0,
            "remainingMinutes": DEFAULT_TRIAL_TOTAL_MINUTES,
            "remainingDailyMinutes": DEFAULT_TRIAL_TOTAL_MINUTES,
            "expiresAt": "",
            "canUse": True,
        }
        user.preferences = prefs
        return prefs["subscription"]

    _ensure_daily_reset(subscription)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)
    remaining_minutes = max(total_minutes - used_minutes, 0)
    remaining_daily_minutes = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes
    can_use = subscription.status == "active" and remaining_minutes > 0 and (daily_limit_minutes <= 0 or remaining_daily_minutes > 0)

    snapshot = {
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "hasActivePlan": can_use,
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": total_minutes,
        "usedMinutes": used_minutes,
        "dailyLimitMinutes": daily_limit_minutes,
        "dailyUsedMinutes": daily_used_minutes,
        "remainingMinutes": remaining_minutes,
        "remainingDailyMinutes": remaining_daily_minutes,
        "expiresAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "canUse": can_use,
        "packageCode": subscription.package_code,
    }
    prefs["subscription"] = snapshot
    user.preferences = prefs
    return snapshot


def get_subscription_status(db: Session, current_user: AuthUser) -> dict:
    user = _get_user(db, current_user)
    subscription = _latest_subscription(db, user.username)
    snapshot = _sync_user_preferences_subscription(user, subscription)
    db.commit()
    return snapshot


def check_subscription_access(db: Session, current_user: AuthUser, mode: str = "practice") -> dict:
    subscription = get_subscription_status(db, current_user)
    allowed = subscription["canUse"]
    reason = ""
    if not allowed:
        if subscription["remainingMinutes"] <= 0:
            reason = "总使用时长已用完"
        elif subscription["dailyLimitMinutes"] > 0 and subscription["remainingDailyMinutes"] <= 0:
            reason = "今日可用时长已用完"
        elif subscription["status"] != "active":
            reason = "当前订阅未生效"
        else:
            reason = "当前订阅不可用"
    return {
        "allowed": allowed,
        "reason": reason,
        "mode": mode,
        "remainingMinutes": subscription["remainingMinutes"],
        "remainingDailyMinutes": subscription["remainingDailyMinutes"],
        "planType": subscription["planType"],
        "trialCompleted": subscription["trialCompleted"],
    }
