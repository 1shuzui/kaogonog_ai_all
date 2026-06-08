"""
这个文件负责权益套餐的有效期、每日限额和用时余额；所有练习入口都应该从这里确认还能不能继续使用。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import User, UserSubscription
from app.schemas.common import AuthUser

from app.services.user_service import get_user_or_404


DEFAULT_TRIAL_TOTAL_MINUTES = 180
ACTIVE_SUBSCRIPTION_PREF_KEY = "activeSubscriptionId"


def _ensure_daily_reset(subscription: UserSubscription) -> None:
    today = date.today()
    if subscription.last_reset_date != today:
        subscription.daily_used_minutes = 0
        subscription.last_reset_date = today


def _list_user_subscriptions(db: Session, username: str) -> list[UserSubscription]:
    subscriptions = db.query(UserSubscription).filter(UserSubscription.username == username).order_by(
        UserSubscription.created_at.desc(),
        UserSubscription.id.desc(),
    ).all()
    for subscription in subscriptions:
        _ensure_daily_reset(subscription)
    return subscriptions


def _get_active_subscription_preference(user: User) -> int:
    prefs = user.preferences if isinstance(user.preferences, dict) else {}
    try:
        return int(prefs.get(ACTIVE_SUBSCRIPTION_PREF_KEY) or 0)
    except (TypeError, ValueError):
        return 0


def _set_active_subscription_preference(user: User, subscription: UserSubscription | None) -> None:
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    if subscription:
        prefs[ACTIVE_SUBSCRIPTION_PREF_KEY] = int(subscription.id or 0)
    else:
        prefs.pop(ACTIVE_SUBSCRIPTION_PREF_KEY, None)
    user.preferences = prefs


def _latest_subscription(db: Session, username: str) -> UserSubscription | None:
    user = db.query(User).filter(User.username == username).first()
    subscriptions = _list_user_subscriptions(db, username)
    if not subscriptions:
        return None

    preferred_id = _get_active_subscription_preference(user) if user else 0
    if preferred_id:
        preferred = next((subscription for subscription in subscriptions if int(subscription.id or 0) == preferred_id), None)
        if preferred and _subscription_can_use(preferred):
            return preferred

    usable_paid = [
        subscription
        for subscription in subscriptions
        if _subscription_can_use(subscription) and not bool(subscription.is_trial)
    ]
    if usable_paid:
        return usable_paid[0]

    usable_any = [subscription for subscription in subscriptions if _subscription_can_use(subscription)]
    if usable_any:
        return usable_any[0]

    return subscriptions[0]


def _subscription_can_use(subscription: UserSubscription) -> bool:
    if subscription.status != "active":
        return False
    if subscription.end_at and subscription.end_at <= datetime.now(subscription.end_at.tzinfo):
        return False
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)
    remaining_minutes = max(total_minutes - used_minutes, 0)
    remaining_daily_quota = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes
    remaining_daily_minutes = min(remaining_minutes, remaining_daily_quota)
    return remaining_minutes > 0 and remaining_daily_minutes > 0


def _serialize_subscription(subscription: UserSubscription, active_subscription_id: int = 0) -> dict:
    _ensure_daily_reset(subscription)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)
    remaining_minutes = max(total_minutes - used_minutes, 0)
    remaining_daily_quota = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes
    remaining_daily_minutes = min(remaining_minutes, remaining_daily_quota)
    can_use = subscription.status == "active" and remaining_minutes > 0 and (daily_limit_minutes <= 0 or remaining_daily_minutes > 0)
    subscription_id = int(subscription.id or 0)

    return {
        "id": subscription_id,
        "subscriptionId": subscription_id,
        "isActiveSelection": active_subscription_id > 0 and subscription_id == active_subscription_id,
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
        "sourceOrderNo": subscription.source_order_no or "",
        "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
    }


def _sync_user_preferences_subscription(
    user: User,
    subscription: UserSubscription | None,
    entitlements: list[dict] | None = None,
) -> dict:
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
            "stacked": False,
            "activePlanCount": 0,
            "entitlements": [],
        }
        user.preferences = prefs
        return prefs["subscription"]

    active_subscription_id = _get_active_subscription_preference(user)
    snapshot = _serialize_subscription(subscription, active_subscription_id)
    entitlement_list = entitlements if entitlements is not None else [snapshot]
    usable_entitlements = [item for item in entitlement_list if item.get("canUse") and not item.get("isTrialUser")]
    snapshot = {
        **snapshot,
        "hasActivePlan": snapshot["canUse"],
        "activeSubscriptionId": int(subscription.id or 0),
        "stacked": len(usable_entitlements) > 1,
        "activePlanCount": len(usable_entitlements),
        "entitlements": entitlement_list,
    }
    prefs["subscription"] = snapshot
    user.preferences = prefs
    return snapshot


def get_subscription_status(db: Session, current_user: AuthUser) -> dict:
    """
    get_subscription_status 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, current_user.username)
    subscriptions = _list_user_subscriptions(db, user.username)
    subscription = _select_subscription(user, subscriptions)
    entitlements = [_serialize_subscription(item, int(subscription.id or 0) if subscription else 0) for item in subscriptions]
    if subscription and _get_active_subscription_preference(user) != int(subscription.id or 0):
        _set_active_subscription_preference(user, subscription)
        entitlements = [_serialize_subscription(item, int(subscription.id or 0)) for item in subscriptions]
    prev_prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    snapshot = _sync_user_preferences_subscription(user, subscription, entitlements)
    current_prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    if prev_prefs.get("subscription") != current_prefs.get("subscription"):
        db.commit()
    return snapshot


def _select_subscription(user: User, subscriptions: list[UserSubscription]) -> UserSubscription | None:
    if not subscriptions:
        return None

    preferred_id = _get_active_subscription_preference(user)
    if preferred_id:
        preferred = next((subscription for subscription in subscriptions if int(subscription.id or 0) == preferred_id), None)
        if preferred and _subscription_can_use(preferred):
            return preferred

    usable_paid = [subscription for subscription in subscriptions if _subscription_can_use(subscription) and not bool(subscription.is_trial)]
    if usable_paid:
        return usable_paid[0]

    usable_any = [subscription for subscription in subscriptions if _subscription_can_use(subscription)]
    if usable_any:
        return usable_any[0]

    return subscriptions[0]


def switch_subscription(db: Session, current_user: AuthUser, subscription_id: int) -> dict:
    """
    switch_subscription 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param subscription_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    subscriptions = _list_user_subscriptions(db, user.username)
    subscription = next((item for item in subscriptions if int(item.id or 0) == int(subscription_id or 0)), None)
    if not subscription:
        raise HTTPException(status_code=404, detail="权益不存在")
    if not _subscription_can_use(subscription):
        raise HTTPException(status_code=400, detail="该权益当前不可用，不能切换")
    _set_active_subscription_preference(user, subscription)
    entitlements = [_serialize_subscription(item, int(subscription.id or 0)) for item in subscriptions]
    snapshot = _sync_user_preferences_subscription(user, subscription, entitlements)
    db.commit()
    return snapshot


def check_subscription_access(db: Session, current_user: AuthUser, mode: str = "practice") -> dict:
    """
    check_subscription_access 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param mode: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
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
