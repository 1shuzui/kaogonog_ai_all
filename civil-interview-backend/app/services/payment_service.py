from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import AuthUser, PaymentCallbackRequest, PaymentOrderCreateRequest, PaymentRefundApplyRequest, PaymentRefundStatsRequest
from app.services.wechat_pay_service import wechat_pay_service

logger = logging.getLogger(__name__)

PENDING_STATUS = "pending"
PAID_STATUS = "paid"
REFUND_STATUS = "refunded"
REFUND_PENDING_STATUS = "refund_pending"


def _get_user(db: Session, current_user: AuthUser) -> User:
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _get_package_or_404(db: Session, package_code: str) -> SubscriptionPackage:
    package = db.query(SubscriptionPackage).filter(
        SubscriptionPackage.package_code == package_code,
        SubscriptionPackage.is_active.is_(True),
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="套餐不存在或不可用")
    return package


def _effective_package_type(package: SubscriptionPackage) -> str:
    package_type = str(package.package_type or "").strip() or "trial"
    if package_type == "trial" and float(package.price or 0) > 0 and int(package.total_minutes or 0) > 0:
        return "hourly"
    return package_type


def _is_trial_package(package: SubscriptionPackage) -> bool:
    return _effective_package_type(package) == "trial"


def _serialize_order(order: PaymentOrder) -> dict:
    extra_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
    return {
        "orderNo": order.order_no,
        "status": order.status,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "amount": float(order.amount or 0),
        "payChannel": order.pay_channel,
        "thirdPartyOrderNo": order.third_party_order_no or "",
        "paidAt": order.paid_at.isoformat() if order.paid_at else "",
        "createdAt": order.created_at.isoformat() if order.created_at else "",
        "refundInfo": extra_payload.get("refund", {}),
    }


def _serialize_payment_response(order: PaymentOrder, package: SubscriptionPackage, pay_payload: dict | None = None) -> dict:
    return {
        **_serialize_order(order),
        "packageName": package.package_name,
        "payParams": pay_payload or {},
    }


def _assert_admin(current_user: AuthUser) -> None:
    if not current_user.isAdmin and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _minutes_to_hours(minutes: int) -> int:
    return max((int(minutes or 0) + 59) // 60, 0)


def _get_subscription_for_order(db: Session, order: PaymentOrder) -> UserSubscription | None:
    return db.query(UserSubscription).filter(
        UserSubscription.source_order_no == order.order_no,
        UserSubscription.username == order.username,
    ).first()


def _amount_to_cents(value) -> int:
    return int(round(float(value or 0) * 100))


def _normalize_idempotency_key(value: str | None) -> str:
    return str(value or "").strip()[:128]


def _get_order_extra(order: PaymentOrder) -> dict:
    return dict(order.extra_payload) if isinstance(order.extra_payload, dict) else {}


def _find_idempotent_order(db: Session, username: str, package_code: str, pay_channel: str, idempotency_key: str) -> PaymentOrder | None:
    if not idempotency_key:
        return None
    candidates = db.query(PaymentOrder).filter(
        PaymentOrder.username == username,
        PaymentOrder.package_code == package_code,
        PaymentOrder.pay_channel == pay_channel,
        PaymentOrder.status.in_([PENDING_STATUS, PAID_STATUS]),
    ).order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).limit(30).all()
    for order in candidates:
        if _get_order_extra(order).get("idempotencyKey") == idempotency_key:
            return order
    return None


def _store_pay_payload(order: PaymentOrder, pay_payload: dict) -> None:
    extra_payload = _get_order_extra(order)
    extra_payload["payParams"] = pay_payload
    order.extra_payload = extra_payload


def _get_cached_pay_payload(order: PaymentOrder) -> dict:
    pay_payload = _get_order_extra(order).get("payParams")
    return pay_payload if isinstance(pay_payload, dict) else {}


def _build_refund_balance(order: PaymentOrder, subscription: UserSubscription | None) -> dict:
    total_minutes = int(subscription.total_minutes or 0) if subscription else 0
    used_minutes = int(subscription.used_minutes or 0) if subscription else 0
    refundable_minutes = max(total_minutes - used_minutes, 0)
    total_hours = _minutes_to_hours(total_minutes)
    used_hours = _minutes_to_hours(used_minutes)
    refundable_hours = _minutes_to_hours(refundable_minutes)
    hourly_amount = round(float(order.amount or 0) / total_hours, 2) if total_hours > 0 else 0
    refundable_amount = round(hourly_amount * refundable_hours, 2)
    refund_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
    return {
        **_serialize_order(order),
        "username": order.username,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "totalMinutes": total_minutes,
        "usedMinutes": used_minutes,
        "refundableMinutes": refundable_minutes,
        "totalHours": total_hours,
        "usedHours": used_hours,
        "refundableHours": refundable_hours,
        "hourlyAmount": hourly_amount,
        "refundableAmount": refundable_amount,
        "refundStatus": order.status,
        "refundInfo": refund_payload.get("refund", {}),
    }


def create_payment_order(db: Session, current_user: AuthUser, data: PaymentOrderCreateRequest) -> dict:
    _get_user(db, current_user)
    package = _get_package_or_404(db, data.packageCode)
    if data.payChannel != "wechat":
        raise HTTPException(status_code=400, detail="当前仅支持微信支付")
    idempotency_key = _normalize_idempotency_key(data.idempotencyKey)
    existing_order = _find_idempotent_order(db, current_user.username, package.package_code, data.payChannel, idempotency_key)
    if existing_order:
        logger.info(
            "Payment idempotent order reused",
            extra={
                "event": "payment.order.idempotent_reused",
                "user_id": current_user.username,
                "order_no": existing_order.order_no,
                "package_code": package.package_code,
                "pay_channel": data.payChannel,
                "status": existing_order.status,
            },
        )
        pay_payload = _get_cached_pay_payload(existing_order)
        if not pay_payload and existing_order.status == PENDING_STATUS:
            pay_payload = wechat_pay_service.get_pay_payload(existing_order, package, data)
            _store_pay_payload(existing_order, pay_payload)
            db.commit()
        return _serialize_payment_response(existing_order, package, pay_payload)

    order = PaymentOrder(
        order_no=f"PAY{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}",
        username=current_user.username,
        package_code=package.package_code,
        package_type=_effective_package_type(package),
        amount=Decimal(str(package.price or 0)),
        pay_channel=data.payChannel,
        status=PENDING_STATUS,
        extra_payload={
            "packageName": package.package_name,
            "scene": data.scene,
            "appId": data.appId or "",
            "openId": data.openId or "",
            "clientIp": data.clientIp or "",
            "idempotencyKey": idempotency_key,
        },
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    logger.info(
        "Payment order created",
        extra={
            "event": "payment.order.created",
            "user_id": current_user.username,
            "order_no": order.order_no,
            "package_code": package.package_code,
            "package_type": order.package_type,
            "amount": float(order.amount or 0),
            "pay_channel": data.payChannel,
            "scene": data.scene,
        },
    )
    pay_payload = wechat_pay_service.get_pay_payload(order, package, data)
    _store_pay_payload(order, pay_payload)
    db.commit()
    db.refresh(order)
    return _serialize_payment_response(order, package, pay_payload)


def list_payment_orders(db: Session, current_user: AuthUser) -> dict:
    _get_user(db, current_user)
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.username == current_user.username,
    ).order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    logger.info(
        "Payment orders listed",
        extra={"event": "payment.order.listed", "user_id": current_user.username, "total": len(orders)},
    )
    return {"list": [_serialize_order(order) for order in orders], "total": len(orders)}


def get_payment_order(db: Session, current_user: AuthUser, order_no: str) -> dict:
    order = db.query(PaymentOrder).filter(
        PaymentOrder.order_no == order_no,
        PaymentOrder.username == current_user.username,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")

    if order.status == PENDING_STATUS:
        transaction = wechat_pay_service.query_order(order)
        if transaction:
            _apply_transaction_to_order(db, order, package, transaction)
            db.commit()
            db.refresh(order)
            logger.info(
                "Payment order synced from provider",
                extra={
                    "event": "payment.order.synced",
                    "user_id": current_user.username,
                    "order_no": order.order_no,
                    "status": order.status,
                    "transaction_id": order.third_party_order_no or "",
                },
            )

    pay_payload = _get_cached_pay_payload(order) or {
        "mode": "query",
        "scene": _get_order_extra(order).get("scene", "mini_program"),
        "message": "订单查询接口不重复生成支付签名，如需重新拉起支付，请重新创建订单。",
    }
    return _serialize_payment_response(order, package, pay_payload)


def get_refund_balance_stats(db: Session, current_user: AuthUser, data: PaymentRefundStatsRequest) -> dict:
    _assert_admin(current_user)
    query = db.query(PaymentOrder).filter(PaymentOrder.status.in_([PAID_STATUS, REFUND_STATUS, REFUND_PENDING_STATUS]))
    if data.username:
        query = query.filter(PaymentOrder.username == data.username)
    if data.orderNo:
        query = query.filter(PaymentOrder.order_no == data.orderNo)
    orders = query.order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    items = [_build_refund_balance(order, _get_subscription_for_order(db, order)) for order in orders]
    logger.info(
        "Refund stats queried",
        extra={
            "event": "payment.refund.stats",
            "operator": current_user.username,
            "target_username": data.username or "",
            "order_no": data.orderNo or "",
            "total": len(items),
        },
    )
    return {
        "list": items,
        "total": len(items),
        "summary": {
            "totalPaidAmount": round(sum(item["amount"] for item in items), 2),
            "totalHours": sum(item["totalHours"] for item in items),
            "usedHours": sum(item["usedHours"] for item in items),
            "refundableHours": sum(item["refundableHours"] for item in items),
            "refundableAmount": round(sum(item["refundableAmount"] for item in items), 2),
        },
    }


def apply_refund_by_hours(db: Session, current_user: AuthUser, data: PaymentRefundApplyRequest) -> dict:
    _assert_admin(current_user)
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == data.orderNo).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in [PAID_STATUS, REFUND_STATUS, REFUND_PENDING_STATUS]:
        raise HTTPException(status_code=400, detail="仅支持已支付订单统计退款")

    subscription = _get_subscription_for_order(db, order)
    balance = _build_refund_balance(order, subscription)
    refunded_hours = balance["refundableHours"] if data.refundedHours is None else min(int(data.refundedHours), balance["refundableHours"])
    refund_amount = round(balance["hourlyAmount"] * refunded_hours, 2)
    if refund_amount <= 0:
        raise HTTPException(status_code=400, detail="当前订单没有可退余额")
    refund_payload = dict(order.extra_payload) if isinstance(order.extra_payload, dict) else {}
    existing_refund = refund_payload.get("refund", {}) if isinstance(refund_payload.get("refund"), dict) else {}
    out_refund_no = existing_refund.get("outRefundNo") or f"RF{order.order_no}"
    refund_result = wechat_pay_service.request_refund(
        order,
        amount_total=_amount_to_cents(order.amount),
        amount_refund=int(round(refund_amount * 100)),
        reason=data.refundReason or data.refundRemark or "用户申请退款",
        out_refund_no=out_refund_no,
    )
    refund_payload["refund"] = {
        "refundedHours": refunded_hours,
        "refundAmount": refund_amount,
        "remark": data.refundRemark or "",
        "refundedAt": datetime.now(timezone.utc).isoformat(),
        "operator": current_user.username,
        "outRefundNo": refund_result.get("outRefundNo") or out_refund_no,
        "refundId": refund_result.get("refundId") or "",
        "wechatStatus": refund_result.get("status") or "",
        "wechatMode": refund_result.get("mode") or "",
        "wechatRaw": refund_result.get("raw") or {},
    }
    order.extra_payload = refund_payload
    order.status = REFUND_STATUS if refund_result.get("status") == "SUCCESS" else REFUND_PENDING_STATUS
    if subscription and order.status == REFUND_STATUS:
        subscription.status = REFUND_STATUS
        subscription.total_minutes = min(int(subscription.used_minutes or 0), int(subscription.total_minutes or 0))
        user = db.query(User).filter(User.username == order.username).first()
        if user:
            _sync_user_preferences_subscription(user, _get_package_or_404(db, order.package_code), subscription)
    db.commit()
    db.refresh(order)
    logger.info(
        "Payment refund applied",
        extra={
            "event": "payment.refund.applied",
            "operator": current_user.username,
            "user_id": order.username,
            "order_no": order.order_no,
            "refunded_hours": refunded_hours,
            "refund_amount": refund_amount,
            "refund_status": order.status,
            "wechat_mode": refund_result.get("mode") or "",
        },
    )
    return {"success": True, "refund": _build_refund_balance(order, subscription)}


def _sync_user_preferences_subscription(user: User, package: SubscriptionPackage, subscription: UserSubscription):
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    remaining_minutes = max(int(subscription.total_minutes or 0) - int(subscription.used_minutes or 0), 0)
    remaining_daily_minutes = (
        max(int(subscription.daily_limit_minutes or 0) - int(subscription.daily_used_minutes or 0), 0)
        if int(subscription.daily_limit_minutes or 0) > 0
        else remaining_minutes
    )
    can_use = subscription.status == "active" and remaining_minutes > 0 and (
        int(subscription.daily_limit_minutes or 0) <= 0 or remaining_daily_minutes > 0
    )
    prefs["subscription"] = {
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "hasActivePlan": can_use,
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": int(subscription.total_minutes or 0),
        "usedMinutes": int(subscription.used_minutes or 0),
        "dailyLimitMinutes": int(subscription.daily_limit_minutes or 0),
        "dailyUsedMinutes": int(subscription.daily_used_minutes or 0),
        "remainingMinutes": remaining_minutes,
        "remainingDailyMinutes": remaining_daily_minutes,
        "expiresAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "packageCode": package.package_code,
        "canUse": can_use,
        "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
    }
    prefs["billing"] = {
        "planType": subscription.plan_type if can_use else "trial",
        "remainingSeconds": remaining_minutes * 60 if can_use and subscription.plan_type == "hourly" else 0,
        "monthlyExpireAt": int(subscription.end_at.timestamp() * 1000) if can_use and subscription.plan_type == "monthly" and subscription.end_at else 0,
        "activatedAt": int(subscription.start_at.timestamp() * 1000) if subscription.start_at else 0,
        "orderHistory": [],
    }
    user.preferences = prefs


def _parse_paid_at(raw: str | None) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _assert_callback_amount(order: PaymentOrder, amount_total: int | None) -> None:
    if amount_total is None:
        raise HTTPException(status_code=400, detail="微信支付回调缺少金额")
    expected_total = int(round(float(order.amount or 0) * 100))
    if expected_total != int(amount_total):
        raise HTTPException(status_code=400, detail="回调金额与订单金额不一致")


def _ensure_subscription_for_paid_order(db: Session, order: PaymentOrder, package: SubscriptionPackage, paid_at: datetime) -> UserSubscription:
    existing = db.query(UserSubscription).filter(
        UserSubscription.source_order_no == order.order_no,
        UserSubscription.username == order.username,
    ).first()
    end_at = paid_at + timedelta(days=int(package.duration_days or 0)) if int(package.duration_days or 0) > 0 else None
    if existing:
        existing.status = "active" if order.status == PAID_STATUS else order.status
        existing.plan_name = package.package_name
        existing.plan_type = _effective_package_type(package)
        existing.total_minutes = int(package.total_minutes or 0)
        existing.daily_limit_minutes = int(package.daily_limit_minutes or 0)
        existing.end_at = end_at
        return existing
    subscription = UserSubscription(
        username=order.username,
        package_code=package.package_code,
        plan_type=_effective_package_type(package),
        plan_name=package.package_name,
        status="active" if order.status == PAID_STATUS else order.status,
        is_trial=_is_trial_package(package),
        trial_completed=False,
        total_minutes=int(package.total_minutes or 0),
        used_minutes=0,
        daily_limit_minutes=int(package.daily_limit_minutes or 0),
        daily_used_minutes=0,
        last_reset_date=paid_at.date() if paid_at else None,
        start_at=paid_at,
        end_at=end_at,
        source_order_no=order.order_no,
        extra_payload={"payChannel": order.pay_channel},
    )
    db.add(subscription)
    return subscription


def _apply_transaction_to_order(db: Session, order: PaymentOrder, package: SubscriptionPackage, parsed: dict) -> UserSubscription | None:
    parsed_status = parsed.get("status") or PENDING_STATUS
    order.status = parsed_status if parsed_status in {PAID_STATUS, "closed", "payerror", "revoked"} else PENDING_STATUS
    order.third_party_order_no = parsed.get("transactionId") or order.third_party_order_no
    if order.status != PAID_STATUS:
        return None

    paid_at = _parse_paid_at(parsed.get("paidAt"))
    order.paid_at = paid_at
    subscription = _ensure_subscription_for_paid_order(db, order, package, paid_at)
    user = db.query(User).filter(User.username == order.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="订单关联用户不存在")
    _sync_user_preferences_subscription(user, package, subscription)
    return subscription


def handle_payment_callback(db: Session, data: PaymentCallbackRequest, headers: dict | None = None, raw_body: bytes | None = None) -> dict:
    parsed = wechat_pay_service.parse_callback(data, headers, raw_body)
    if parsed.get("mode") != "wechat" or not parsed.get("verified") or parsed.get("verifyPending"):
        raise HTTPException(status_code=401, detail="微信支付回调未通过真实验签，不能开通权益")
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == parsed["orderNo"]).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    package = _get_package_or_404(db, order.package_code)
    user = db.query(User).filter(User.username == order.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="订单关联用户不存在")

    _assert_callback_amount(order, parsed.get("amountTotal"))

    if order.status == PAID_STATUS:
        subscription = _ensure_subscription_for_paid_order(db, order, package, order.paid_at or _parse_paid_at(parsed.get("paidAt")))
        _sync_user_preferences_subscription(user, package, subscription)
        db.commit()
        logger.info(
            "Payment callback ignored idempotently",
            extra={
                "event": "payment.callback.idempotent",
                "user_id": order.username,
                "order_no": order.order_no,
                "callback_mode": parsed["mode"],
                "verified": parsed.get("verified", False),
            },
        )
        return {
            "success": True,
            "idempotent": True,
            "message": "订单已支付，重复回调已忽略",
            "callbackMode": parsed["mode"],
            "verifyPending": parsed.get("verifyPending", False),
            "order": _serialize_order(order),
        }

    order.callback_payload = {
        "mode": parsed["mode"],
        "verified": parsed.get("verified", False),
        "verifyPending": parsed.get("verifyPending", False),
        "headers": parsed.get("headers", {}),
        "payload": parsed.get("rawPayload", {}),
    }

    subscription = _apply_transaction_to_order(db, order, package, parsed)
    shipping = {}
    if subscription:
        try:
            shipping = wechat_pay_service.upload_shipping_info(parsed, order, package)
        except Exception as exc:
            shipping = {"skipped": False, "success": False, "error": str(exc)}
        if shipping:
            subscription_payload = dict(subscription.extra_payload) if isinstance(subscription.extra_payload, dict) else {}
            subscription_payload["shipping"] = shipping
            subscription.extra_payload = subscription_payload
    db.commit()
    db.refresh(order)
    logger.info(
        "Payment callback handled",
        extra={
            "event": "payment.callback.handled",
            "user_id": order.username,
            "order_no": order.order_no,
            "status": order.status,
            "callback_mode": parsed["mode"],
            "verified": parsed.get("verified", False),
            "transaction_id": order.third_party_order_no or "",
            "shipping_success": shipping.get("success") if isinstance(shipping, dict) else None,
        },
    )
    return {
        "success": True,
        "idempotent": False,
        "callbackMode": parsed["mode"],
        "verified": parsed.get("verified", False),
        "verifyPending": parsed.get("verifyPending", False),
        "order": _serialize_order(order),
        "subscription": {
            "username": subscription.username,
            "packageCode": subscription.package_code,
            "planType": subscription.plan_type,
            "planName": subscription.plan_name,
            "status": subscription.status,
            "totalMinutes": subscription.total_minutes,
            "dailyLimitMinutes": subscription.daily_limit_minutes,
            "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
            "endAt": subscription.end_at.isoformat() if subscription.end_at else "",
        } if subscription else {},
        "shipping": shipping,
    }
