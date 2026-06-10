"""
管理员人工权益调整服务，负责按用户名查询权益、补发人工时长、扣减指定权益和记录调整流水。

这条链路是客服/运营处理问题的后台能力，不属于真实支付链路：补发不会创建 `payment_orders`，
扣减不会伪造 `usage_records`，所有变动都写入 `entitlement_adjustments`，用改前/改后快照保留证据。
误操作不删除旧流水，而是通过反向调整修正余额。这样普通用户只看到可用余额变化，管理员和后续 AI 能追踪谁在什么原因下改了什么。

@param: 服务函数接收数据库 Session、管理员身份、目标用户名、补发请求或扣减请求。
@return: 返回用户权益详情、调整结果、最新权益摘要或分页调整流水。
@raises HTTPException: 非管理员、用户不存在、权益不存在、参数越界、原因类型无效或扣减超过剩余时长时抛出 HTTP 错误。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access
from app.models.entities import EntitlementAdjustment, PaymentOrder, User, UserSubscription
from app.schemas.common import AuthUser, EntitlementDeductRequest, EntitlementGrantRequest
from app.services.subscription_service import _ensure_daily_reset, _list_user_subscriptions, _select_subscription, _sync_user_preferences_subscription
from app.services.user_service import get_user_or_404


VALID_REASON_TYPES = {"客服补偿", "活动赠送", "测试账号", "退款扣减", "误操作修正", "其他"}


def _parse_datetime(value: str, field_name: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name}格式不正确") from exc
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _clean_reason(reason_type: str) -> str:
    value = str(reason_type or "").strip()
    if value not in VALID_REASON_TYPES:
        raise HTTPException(status_code=400, detail="调整原因类型不正确")
    return value


def _clean_remark(remark: str) -> str:
    value = str(remark or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="调整备注不能为空")
    return value[:1000]


def _remaining_minutes(subscription: UserSubscription) -> int:
    _ensure_daily_reset(subscription)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    return max(total_minutes - used_minutes, 0)


def _remaining_daily_minutes(subscription: UserSubscription) -> int:
    remaining = _remaining_minutes(subscription)
    daily_limit = int(subscription.daily_limit_minutes or 0)
    daily_used = int(subscription.daily_used_minutes or 0)
    if daily_limit <= 0:
        return remaining
    return min(remaining, max(daily_limit - daily_used, 0))


def _serialize_subscription(subscription: UserSubscription) -> dict:
    _ensure_daily_reset(subscription)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit = int(subscription.daily_limit_minutes or 0)
    daily_used = int(subscription.daily_used_minutes or 0)
    remaining = max(total_minutes - used_minutes, 0)
    remaining_daily = min(remaining, max(daily_limit - daily_used, 0)) if daily_limit > 0 else remaining
    return {
        "id": int(subscription.id or 0),
        "subscriptionId": int(subscription.id or 0),
        "username": subscription.username,
        "packageCode": subscription.package_code,
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "isTrial": bool(subscription.is_trial),
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "totalMinutes": total_minutes,
        "usedMinutes": used_minutes,
        "dailyLimitMinutes": daily_limit,
        "dailyUsedMinutes": daily_used,
        "remainingMinutes": remaining,
        "remainingDailyMinutes": remaining_daily,
        "lastResetDate": subscription.last_reset_date.isoformat() if subscription.last_reset_date else "",
        "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
        "endAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "sourceOrderNo": subscription.source_order_no or "",
        "extraPayload": subscription.extra_payload if isinstance(subscription.extra_payload, dict) else {},
        "createdAt": subscription.created_at.isoformat() if subscription.created_at else "",
    }


def _serialize_adjustment(record: EntitlementAdjustment) -> dict:
    return {
        "id": int(record.id or 0),
        "targetUsername": record.target_username,
        "subscriptionId": int(record.subscription_id or 0) if record.subscription_id else None,
        "actionType": record.action_type,
        "minutesDelta": int(record.minutes_delta or 0),
        "beforeSnapshot": record.before_snapshot if isinstance(record.before_snapshot, dict) else {},
        "afterSnapshot": record.after_snapshot if isinstance(record.after_snapshot, dict) else {},
        "reasonType": record.reason_type,
        "remark": record.remark or "",
        "operator": record.operator or "",
        "createdAt": record.created_at.isoformat() if record.created_at else "",
    }


def _serialize_user(user: User) -> dict:
    return {
        "username": user.username,
        "fullName": user.full_name or "",
        "email": user.email or "",
        "province": user.province or "",
        "disabled": bool(user.disabled),
        "registeredAt": user.registered_at.isoformat() if user.registered_at else "",
        "createdAt": user.created_at.isoformat() if user.created_at else "",
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else "",
        "lastActiveAt": user.last_active_at.isoformat() if user.last_active_at else "",
    }


def _sync_subscription_snapshot(db: Session, user: User) -> dict:
    subscriptions = _list_user_subscriptions(db, user.username)
    selected = _select_subscription(user, subscriptions)
    entitlements = []
    active_id = int(selected.id or 0) if selected else 0
    for item in subscriptions:
        snapshot = _serialize_subscription(item)
        snapshot["canUse"] = item.status == "active" and snapshot["remainingMinutes"] > 0 and snapshot["remainingDailyMinutes"] > 0
        snapshot["isActiveSelection"] = active_id > 0 and int(item.id or 0) == active_id
        entitlements.append(snapshot)
    return _sync_user_preferences_subscription(user, selected, entitlements)


def _order_summary(db: Session, username: str) -> dict:
    orders = db.query(PaymentOrder).filter(PaymentOrder.username == username).all()
    paid_orders = [order for order in orders if order.status == "paid"]
    return {
        "totalOrders": len(orders),
        "paidOrders": len(paid_orders),
        "refundedOrders": len([order for order in orders if order.status == "refunded"]),
        "totalPaidAmount": round(sum(float(order.amount or 0) for order in paid_orders), 2),
    }


def _user_detail(db: Session, user: User, recent_limit: int = 5) -> dict:
    subscriptions = [_serialize_subscription(item) for item in _list_user_subscriptions(db, user.username)]
    adjustments = db.query(EntitlementAdjustment).filter(
        EntitlementAdjustment.target_username == user.username,
    ).order_by(EntitlementAdjustment.created_at.desc(), EntitlementAdjustment.id.desc()).limit(recent_limit).all()
    return {
        "user": _serialize_user(user),
        "orderSummary": _order_summary(db, user.username),
        "subscriptionSummary": _sync_subscription_snapshot(db, user),
        "entitlements": subscriptions,
        "recentAdjustments": [_serialize_adjustment(item) for item in adjustments],
    }


def list_admin_users(db: Session, current_user: AuthUser, username: str = "", page: int = 1, page_size: int = 20) -> dict:
    """
    list_admin_users 为管理员搜索用户提供轻量列表，避免权益管理页直接拉全站用户。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param username: 搜索关键字；按用户名、昵称和邮箱做模糊匹配，主口径仍是用户名。
    @param page: 页码，从 1 开始。
    @param page_size: 每页条数。
    @return: 返回用户列表、分页和基础权益摘要。
    @raises HTTPException: 非管理员或参数非法时抛出。
    """
    ensure_admin_access(current_user)
    safe_page = max(int(page or 1), 1)
    safe_page_size = min(max(int(page_size or 20), 1), 100)
    query = db.query(User)
    keyword = str(username or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(or_(User.username.like(pattern), User.full_name.like(pattern), User.email.like(pattern)))
    total = query.count()
    users = query.order_by(User.last_active_at.desc(), User.id.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    rows = []
    for user in users:
        subscriptions = _list_user_subscriptions(db, user.username)
        remaining = sum(_remaining_minutes(item) for item in subscriptions if item.status == "active")
        rows.append({
            **_serialize_user(user),
            "entitlementCount": len(subscriptions),
            "remainingMinutes": remaining,
            "orderSummary": _order_summary(db, user.username),
        })
    return {"list": rows, "total": total, "page": safe_page, "pageSize": safe_page_size}


def get_admin_user_entitlements(db: Session, current_user: AuthUser, username: str) -> dict:
    """
    get_admin_user_entitlements 返回单个用户的权益、订单摘要和最近调整记录。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param username: 目标用户账号。
    @return: 返回用户权益详情。
    @raises HTTPException: 非管理员或用户不存在时抛出。
    """
    ensure_admin_access(current_user)
    user = get_user_or_404(db, username)
    detail = _user_detail(db, user)
    db.commit()
    return detail


def grant_user_entitlement(db: Session, current_user: AuthUser, username: str, data: EntitlementGrantRequest) -> dict:
    """
    grant_user_entitlement 创建人工补发权益，不创建支付订单，保证售后补偿和微信虚拟支付分账清楚。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param username: 目标用户账号。
    @param data: 路由层校验后的补发请求体。
    @return: 返回最新用户详情和本次调整流水。
    @raises HTTPException: 非管理员、参数非法或用户不存在时抛出。
    """
    ensure_admin_access(current_user)
    user = get_user_or_404(db, username)
    reason_type = _clean_reason(data.reasonType)
    remark = _clean_remark(data.remark)
    start_at = _parse_datetime(data.startAt, "开始时间")
    end_at = _parse_datetime(data.endAt, "到期时间")
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="到期时间必须晚于开始时间")
    total_minutes = int(data.totalMinutes or 0)
    daily_limit = int(data.dailyLimitMinutes or 0)
    if daily_limit > total_minutes:
        raise HTTPException(status_code=400, detail="每日限额不能超过总分钟数")
    subscription = UserSubscription(
        username=user.username,
        package_code="manual_grant",
        plan_type="manual",
        plan_name=f"人工补发 {total_minutes} 分钟",
        status="active",
        is_trial=False,
        trial_completed=False,
        total_minutes=total_minutes,
        used_minutes=0,
        daily_limit_minutes=daily_limit,
        daily_used_minutes=0,
        last_reset_date=date.today(),
        start_at=start_at,
        end_at=end_at,
        source_order_no="",
        extra_payload={
            "source": "admin_manual_grant",
            "reasonType": reason_type,
            "remark": remark,
            "operator": current_user.username,
        },
    )
    db.add(subscription)
    db.flush()
    after_snapshot = _serialize_subscription(subscription)
    adjustment = EntitlementAdjustment(
        target_username=user.username,
        subscription_id=subscription.id,
        action_type="grant",
        minutes_delta=total_minutes,
        before_snapshot={},
        after_snapshot=after_snapshot,
        reason_type=reason_type,
        remark=remark,
        operator=current_user.username,
    )
    db.add(adjustment)
    _sync_subscription_snapshot(db, user)
    db.commit()
    db.refresh(adjustment)
    db.refresh(subscription)
    return {"success": True, "adjustment": _serialize_adjustment(adjustment), "detail": _user_detail(db, user)}


def deduct_user_entitlement(db: Session, current_user: AuthUser, username: str, data: EntitlementDeductRequest) -> dict:
    """
    deduct_user_entitlement 通过增加指定权益的已用分钟数完成扣减，避免伪造用量流水或篡改订单。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param username: 目标用户账号。
    @param data: 路由层校验后的扣减请求体。
    @return: 返回最新用户详情和本次调整流水。
    @raises HTTPException: 非管理员、参数非法、权益不存在或扣减越界时抛出。
    """
    ensure_admin_access(current_user)
    user = get_user_or_404(db, username)
    reason_type = _clean_reason(data.reasonType)
    remark = _clean_remark(data.remark)
    subscription = db.query(UserSubscription).filter(
        UserSubscription.id == data.subscriptionId,
        UserSubscription.username == user.username,
    ).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="目标权益不存在")
    before_snapshot = _serialize_subscription(subscription)
    remaining = int(before_snapshot["remainingMinutes"] or 0)
    deduct_minutes = int(data.deductMinutes or 0)
    if deduct_minutes > remaining:
        raise HTTPException(status_code=400, detail="扣减分钟数超过该权益剩余额度")
    subscription.used_minutes = int(subscription.used_minutes or 0) + deduct_minutes
    daily_limit = int(subscription.daily_limit_minutes or 0)
    if daily_limit > 0:
        subscription.daily_used_minutes = min(daily_limit, int(subscription.daily_used_minutes or 0) + deduct_minutes)
    if subscription.used_minutes >= int(subscription.total_minutes or 0):
        subscription.status = "inactive"
    extra = dict(subscription.extra_payload) if isinstance(subscription.extra_payload, dict) else {}
    extra["lastAdminDeduction"] = {
        "deductMinutes": deduct_minutes,
        "reasonType": reason_type,
        "remark": remark,
        "operator": current_user.username,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    subscription.extra_payload = extra
    after_snapshot = _serialize_subscription(subscription)
    adjustment = EntitlementAdjustment(
        target_username=user.username,
        subscription_id=subscription.id,
        action_type="deduct",
        minutes_delta=-deduct_minutes,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        reason_type=reason_type,
        remark=remark,
        operator=current_user.username,
    )
    db.add(adjustment)
    _sync_subscription_snapshot(db, user)
    db.commit()
    db.refresh(adjustment)
    db.refresh(subscription)
    return {"success": True, "adjustment": _serialize_adjustment(adjustment), "detail": _user_detail(db, user)}


def list_entitlement_adjustments(
    db: Session,
    current_user: AuthUser,
    username: str = "",
    action_type: str = "",
    operator: str = "",
    start_at: str = "",
    end_at: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    list_entitlement_adjustments 提供全局权益调整流水，方便管理员按用户、动作和时间查账。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param username: 目标用户筛选。
    @param action_type: 调整类型筛选。
    @param operator: 操作者筛选。
    @param start_at: 开始时间筛选。
    @param end_at: 结束时间筛选。
    @param page: 页码，从 1 开始。
    @param page_size: 每页条数。
    @return: 返回调整流水列表和分页信息。
    @raises HTTPException: 非管理员或筛选参数非法时抛出。
    """
    ensure_admin_access(current_user)
    safe_page = max(int(page or 1), 1)
    safe_page_size = min(max(int(page_size or 20), 1), 100)
    query = db.query(EntitlementAdjustment)
    if username:
        query = query.filter(EntitlementAdjustment.target_username.like(f"%{str(username).strip()}%"))
    if action_type:
        query = query.filter(EntitlementAdjustment.action_type == str(action_type).strip())
    if operator:
        query = query.filter(EntitlementAdjustment.operator.like(f"%{str(operator).strip()}%"))
    if start_at:
        query = query.filter(EntitlementAdjustment.created_at >= _parse_datetime(start_at, "开始时间"))
    if end_at:
        query = query.filter(EntitlementAdjustment.created_at <= _parse_datetime(end_at, "结束时间"))
    total = query.count()
    records = query.order_by(EntitlementAdjustment.created_at.desc(), EntitlementAdjustment.id.desc()).offset(
        (safe_page - 1) * safe_page_size
    ).limit(safe_page_size).all()
    return {"list": [_serialize_adjustment(item) for item in records], "total": total, "page": safe_page, "pageSize": safe_page_size}
