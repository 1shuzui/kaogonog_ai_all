"""
权益余额服务层，统一计算套餐有效期、总剩余分钟、每日剩余分钟、试用权益和当前选中的可用权益。

练习、定向备面、全真模拟、试用题和小程序套餐页都依赖这里判断用户还能不能继续使用。这里不创建支付订单，
也不记录真实答题用量；它只根据 `user_subscriptions` 的状态和使用分钟计算可用性，并在跨天时重置每日用量。
多份权益并存时通过用户偏好记录当前选择，避免系统自动切到用户不想消耗的套餐。

@param: 服务函数接收数据库 Session、当前用户、权益 ID 或需要消耗的分钟数。
@return: 返回权益状态、可用性检查结果、切换后的当前权益或同步后的用户偏好快照。
@raises HTTPException: 用户不存在、权益不存在、权益不可用或剩余分钟不足时抛出 HTTP 错误。
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


def _subscription_is_expired(subscription: UserSubscription) -> bool:
    if not subscription.end_at:
        return False
    now = datetime.now(subscription.end_at.tzinfo or None)
    return subscription.end_at <= now


def _serialize_subscription(subscription: UserSubscription, active_subscription_id: int = 0) -> dict:
    _ensure_daily_reset(subscription)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)
    remaining_minutes = max(total_minutes - used_minutes, 0)
    remaining_daily_quota = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes
    remaining_daily_minutes = min(remaining_minutes, remaining_daily_quota)
    expired = _subscription_is_expired(subscription)
    can_use = subscription.status == "active" and not expired and remaining_minutes > 0 and (daily_limit_minutes <= 0 or remaining_daily_minutes > 0)
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
        "status": "expired" if expired else subscription.status,
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
    读取当前用户最适合使用的权益快照。

    用户可能同时有试用、小时包、月卡和人工补发权益；这里按 active preference、可用付费权益、试用权益
    的顺序选中当前权益，并把完整 entitlements 列表同步回 preferences，保证 PC 和小程序看到同一余额。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 当前权益快照，包含剩余总时长、今日剩余、可用状态、选中权益和全部权益列表。
    @raises HTTPException: 当前用户在数据库中不存在时由 get_user_or_404 抛出 404。
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

    return None


def switch_subscription(db: Session, current_user: AuthUser, subscription_id: int) -> dict:
    """
    手动切换当前消耗的权益。

    同一用户可能拥有多条可用权益，允许用户切换是为了优先消耗指定套餐；但只能切到本人且当前可用的权益，
    避免端侧传入过期或他人 subscriptionId 造成扣量错位。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param subscription_id: 目标 UserSubscription 主键。
    @return: 切换后的权益快照。
    @raises HTTPException: 权益不存在时抛出 404，权益不可用时抛出 400。
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
    检查当前用户是否还能进入指定训练模式。

    前端可以禁用按钮，但额度判断必须以后端为准。这里复用 get_subscription_status 的快照，并把不可用原因
    转成用户可读文案，方便套餐页、考场页和定向备面共用同一解释。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param mode: 调用场景标识，例如 practice、exam 或 targeted；当前主要用于响应回显和前端提示。
    @return: allowed、reason、mode 和完整 subscription 快照。
    @raises HTTPException: 当前用户不存在时由 get_subscription_status 向上抛出。
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
