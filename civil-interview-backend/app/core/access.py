"""
用户访问权限与权益快照模块。

PC 和小程序会隐藏很多入口，但真正的管理员、付费和试用边界必须由后端兜住。这里把历史 billing 字段、新订阅表、内置管理员账号和用户 preferences 统一整理成一个 access_context，避免退款、题库维护、权益扣减、试用入口在不同路由里得到不一致的“是否可用”答案。

@param: 模块本身无入参；业务输入来自 User ORM 对象、preferences 字典和订阅关系。
@return: 导出权限判断与权益快照函数，供认证依赖和服务层生成统一 isAdmin/isPaid/permissions 结果。
@raises ImportError: 缺少 FastAPI、时间或配置依赖时会在导入阶段失败。
@raises HTTPException: 管理员断言失败时由 require_admin_or_403 抛出 403。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from time import time

from fastapi import HTTPException, status

ADMIN_USERNAME = "admin"
TRIAL_QUESTION_ID = "q001"
BILLING_PLAN_TRIAL = "trial"
BILLING_PLAN_HOURLY = "hourly"
BILLING_PLAN_MONTHLY = "monthly"
VALID_BILLING_PLANS = {
    BILLING_PLAN_TRIAL,
    BILLING_PLAN_HOURLY,
    BILLING_PLAN_MONTHLY,
}


def normalize_billing_state(raw_state: dict | None = None) -> dict:
    """
    统一整理旧版本地权益字段，避免历史用户的 preferences 形状不同导致权限判断前后不一致。

    这里仍兼容 billing 字典，是因为早期订单和新订阅表会在一段时间内并存。

    @param raw_state: 用户偏好里的 billing 字典；可能来自旧版前端、本地测试或历史订单快照。
    @return: 规范后的权益状态，包含套餐类型、剩余秒数、月卡到期时间和订单摘要。
    @raises: 不主动包装底层错误；异常会沿调用栈向上传递。
    """
    raw_state = raw_state if isinstance(raw_state, dict) else {}
    plan_type = str(raw_state.get("planType") or BILLING_PLAN_TRIAL)
    if plan_type not in VALID_BILLING_PLANS:
        plan_type = BILLING_PLAN_TRIAL

    order_history = []
    if isinstance(raw_state.get("orderHistory"), list):
        for order in raw_state["orderHistory"][:20]:
            if not isinstance(order, dict):
                continue
            order_history.append(
                {
                    "id": str(order.get("id") or ""),
                    "planType": str(order.get("planType") or ""),
                    "title": str(order.get("title") or ""),
                    "amount": max(0, int(float(order.get("amount") or 0))),
                    "status": str(order.get("status") or "paid"),
                    "summary": str(order.get("summary") or ""),
                    "createdAt": max(0, int(float(order.get("createdAt") or 0))),
                }
            )

    return {
        "planType": plan_type,
        "remainingSeconds": max(0, int(float(raw_state.get("remainingSeconds") or 0))),
        "monthlyExpireAt": max(0, int(float(raw_state.get("monthlyExpireAt") or 0))),
        "activatedAt": max(0, int(float(raw_state.get("activatedAt") or 0))),
        "orderHistory": order_history,
    }


def is_admin_username(username: str | None) -> bool:
    """
    判断内置管理员账号，避免各个后台路由分别硬编码 admin 名称。

    当前项目没有完整 RBAC，先把管理员身份收在一个小函数里，后续迁移角色表时影响面更小。

    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @return: True 表示命中当前内置管理员账号，False 表示普通用户。
    @raises: 不主动包装底层错误；异常会沿调用栈向上传递。
    """
    return str(username or "").strip().lower() == ADMIN_USERNAME


def has_paid_access_from_billing(billing_state: dict | None, now_ms: int | None = None) -> bool:
    """
    从旧版 billing 状态判断是否仍有付费权益，给还没迁到订阅表的用户兜底。

    月卡看过期时间，小时包看剩余秒数；试用永远不能在这里被当成付费。

    @param billing_state: 旧版本地权益状态；为空或字段异常时按试用处理。
    @param now_ms: 当前时间戳毫秒值；测试可传固定时间以验证过期判断。
    @return: True 表示旧版权益仍可访问付费功能，False 表示需要开通。
    @raises: 不主动包装底层错误；异常会沿调用栈向上传递。
    """
    state = normalize_billing_state(billing_state)
    current_ms = int(now_ms if now_ms is not None else time() * 1000)

    if state["planType"] == BILLING_PLAN_MONTHLY:
        return state["monthlyExpireAt"] > current_ms
    if state["planType"] == BILLING_PLAN_HOURLY:
        return state["remainingSeconds"] > 0
    return False


def _timestamp_ms(value) -> int:
    if not value:
        return 0
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return int(value.timestamp() * 1000)
        return int(value.astimezone(timezone.utc).timestamp() * 1000)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _is_subscription_expired(end_at) -> bool:
    if not end_at:
        return False
    if not isinstance(end_at, datetime):
        return False
    now = datetime.now(end_at.tzinfo or timezone.utc)
    if end_at.tzinfo is None:
        now = datetime.now()
    return end_at <= now


def _subscription_snapshot(subscription) -> dict | None:
    if not subscription:
        return None
    if str(getattr(subscription, "status", "") or "") != "active":
        return None
    if bool(getattr(subscription, "is_trial", False)):
        return None
    if _is_subscription_expired(getattr(subscription, "end_at", None)):
        return None

    total_minutes = max(0, int(getattr(subscription, "total_minutes", 0) or 0))
    used_minutes = max(0, int(getattr(subscription, "used_minutes", 0) or 0))
    daily_limit_minutes = max(0, int(getattr(subscription, "daily_limit_minutes", 0) or 0))
    raw_daily_used = max(0, int(getattr(subscription, "daily_used_minutes", 0) or 0))
    last_reset_date = getattr(subscription, "last_reset_date", None)
    daily_used_minutes = raw_daily_used if last_reset_date == date.today() else 0
    remaining_minutes = max(total_minutes - used_minutes, 0)
    remaining_daily_quota = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes
    remaining_daily_minutes = min(remaining_minutes, remaining_daily_quota)
    can_use = remaining_minutes > 0 and (daily_limit_minutes <= 0 or remaining_daily_minutes > 0)
    if not can_use:
        return None

    return {
        "planType": str(getattr(subscription, "plan_type", "") or BILLING_PLAN_HOURLY),
        "planName": str(getattr(subscription, "plan_name", "") or ""),
        "status": "active",
        "remainingMinutes": remaining_minutes,
        "remainingDailyMinutes": remaining_daily_minutes,
        "dailyLimitMinutes": daily_limit_minutes,
        "usedMinutes": used_minutes,
        "totalMinutes": total_minutes,
        "monthlyExpireAt": _timestamp_ms(getattr(subscription, "end_at", None)),
    }


def _latest_paid_subscription_snapshot(user) -> dict | None:
    subscriptions = getattr(user, "subscriptions", None) or []
    snapshots = []
    preferences = user.preferences if isinstance(getattr(user, "preferences", None), dict) else {}
    try:
        preferred_id = int(preferences.get("activeSubscriptionId") or 0)
    except (TypeError, ValueError):
        preferred_id = 0
    for subscription in subscriptions:
        snapshot = _subscription_snapshot(subscription)
        if not snapshot:
            continue
        created_at = getattr(subscription, "created_at", None)
        sub_id = int(getattr(subscription, "id", 0) or 0)
        snapshot = {
            **snapshot,
            "id": sub_id,
            "subscriptionId": sub_id,
            "isActiveSelection": preferred_id > 0 and sub_id == preferred_id,
            "packageCode": str(getattr(subscription, "package_code", "") or ""),
        }
        snapshots.append((_timestamp_ms(created_at), sub_id, snapshot))
    if not snapshots:
        return None
    if preferred_id:
        preferred = next((item for item in snapshots if item[1] == preferred_id), None)
        if preferred:
            return preferred[2]
    snapshots.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return snapshots[0][2]


def build_access_context(user) -> dict:
    """
    给当前用户生成统一权限快照，让 PC、小程序和后台拿到同一套 isAdmin/isPaid 判断。

    这里同时读旧 billing 和新 subscription，是为了在支付迁移期不误伤已经购买的用户。

    @param user: 当前业务用户对象；多端登录和权益扣减都依赖它保持同一账号口径。
    @return: 权限快照，包含角色、付费状态和可访问模块。
    @raises: 不主动包装底层错误；异常会沿调用栈向上传递。
    """
    preferences = user.preferences if isinstance(getattr(user, "preferences", None), dict) else {}
    billing_state = normalize_billing_state(preferences.get("billing"))
    subscription_state = _latest_paid_subscription_snapshot(user)
    is_admin = is_admin_username(getattr(user, "username", ""))
    has_subscription_access = subscription_state is not None
    is_paid = is_admin or has_subscription_access or has_paid_access_from_billing(billing_state)
    if subscription_state:
        billing_state = {
            **billing_state,
            **subscription_state,
            "remainingSeconds": subscription_state["remainingMinutes"] * 60,
        }

    return {
        "role": "admin" if is_admin else "user",
        "isAdmin": is_admin,
        "billing": {
            **billing_state,
            "isPaid": is_paid,
        },
        "permissions": {
            "canManageQuestionBank": is_admin,
            "canAccessPremiumModules": is_paid,
        },
    }


def ensure_admin_access(current_user) -> None:
    """
    拦住非管理员访问题库、退款和定向备面维护入口。

    管理端按钮隐藏只能改善体验，真正的权限必须在服务端再判断一次。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: None；校验通过即静默返回。
    @raises HTTPException: 当前用户不是管理员时抛出 403。
    """
    if getattr(current_user, "isAdmin", False):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="仅管理员可使用题库管理功能",
    )


def ensure_paid_access(current_user, detail: str = "当前功能需付费开通后使用") -> None:
    """
    拦住未开通用户进入需要消耗权益的练习和分析能力。

    前端提示不可信，服务端需要在真正开始扣时长、评分或生成题目前再确认一次。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param detail: 权限不足时返回给端侧的提示文案。
    @return: None；校验通过即静默返回。
    @raises HTTPException: 当前用户没有管理员或付费权益时抛出 403。
    """
    if getattr(current_user, "isAdmin", False):
        return
    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_question_read_access(current_user, question_id: str) -> None:
    """
    限制试用用户只能查看指定试用题，避免直接请求题库接口绕过套餐。

    管理员和付费用户放行；普通试用用户只允许访问 q001。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @return: None；校验通过即静默返回。
    @raises HTTPException: 未付费用户读取非试用题时抛出 403。
    """
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    if str(question_id or "").strip() == TRIAL_QUESTION_ID:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅可查看指定试用题，开通后可使用完整题目",
    )


def ensure_exam_start_access(current_user, question_ids: list[str] | None) -> None:
    """
    开始考试前检查题目集合，防止试用用户提交多题模考请求。

    这一步放在考试创建前，是为了避免数据库里留下无权开始的半成品考试记录。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param question_ids: 题目相关数据；真实题源、题型分类和能力维度需要分开处理。
    @return: None；校验通过即静默返回。
    @raises HTTPException: 未付费用户尝试开始非试用考试时抛出 403。
    """
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    normalized_ids = [str(question_id or "").strip() for question_id in (question_ids or []) if str(question_id or "").strip()]
    if normalized_ids == [TRIAL_QUESTION_ID]:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅可体验指定试用题，开通后可使用完整模考功能",
    )


def ensure_random_question_access(current_user, count: int) -> None:
    """
    控制随机抽题数量，保证未付费用户不能一次抽完整套题。

    试用保留单题体验；多题抽取会消耗更重的题库和评分资源，需要开通后使用。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param count: 请求抽取的题目数量；试用态最多允许 1 题。
    @return: None；校验通过即静默返回。
    @raises HTTPException: 未付费用户请求多题随机抽取时抛出 403。
    """
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    if int(count or 0) <= 1:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅支持单题体验，开通后可抽取完整模考试题",
    )
