from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import (
    AuthUser,
    CompensateRequest,
    PaymentCallbackRequest,
    PaymentOrderCreateRequest,
    PaymentVirtualConfirmRequest,
    RefundApplyRequest,
    RefundBalanceStatsRequest,
)
from app.services.wechat_pay_service import wechat_pay_service
from app.services.user_service import get_user_or_404

def _get_package_or_404(db: Session, package_code: str) -> SubscriptionPackage:
    package = db.query(SubscriptionPackage).filter(
        SubscriptionPackage.package_code == package_code,
        SubscriptionPackage.is_active.is_(True),
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="套餐不存在或不可用")
    return package


def _serialize_order(order: PaymentOrder) -> dict:
    callback_payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    return {
        "orderNo": order.order_no,
        "status": order.status,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "amount": float(order.amount or 0),
        "payChannel": order.pay_channel,
        "thirdPartyOrderNo": order.third_party_order_no or "",
        "verified": callback_payload.get("verified") is True,
        "verifyPending": callback_payload.get("verifyPending") is True,
        "verifyError": callback_payload.get("verifyError") or "",
        "paidAt": order.paid_at.isoformat() if order.paid_at else "",
        "createdAt": order.created_at.isoformat() if order.created_at else "",
    }


def _assert_admin(current_user: AuthUser) -> None:
    if not getattr(current_user, "isAdmin", False):
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _serialize_payment_response(order: PaymentOrder, package: SubscriptionPackage, pay_payload: dict | None = None) -> dict:
    return {
        **_serialize_order(order),
        "packageName": package.package_name,
        "payParams": pay_payload or {},
    }


def _sync_order_amount_to_virtual_goods_price(order: PaymentOrder, pay_payload: dict | None) -> None:
    meta = pay_payload.get("virtualPayMeta") if isinstance(pay_payload, dict) else {}
    goods_price = meta.get("goodsPrice") if isinstance(meta, dict) else None
    if goods_price in (None, ""):
        return
    try:
        order.amount = Decimal(int(goods_price)) / Decimal("100")
    except (TypeError, ValueError):
        return


def create_payment_order(db: Session, current_user: AuthUser, data: PaymentOrderCreateRequest) -> dict:
    get_user_or_404(db, current_user.username)
    package = _get_package_or_404(db, data.packageCode)
    order = PaymentOrder(
        order_no=f"PAY{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}",
        username=current_user.username,
        package_code=package.package_code,
        package_type=package.package_type,
        amount=Decimal(str(package.price or 0)),
        pay_channel=data.payChannel,
        status="pending",
        extra_payload={
            "packageName": package.package_name,
            "scene": data.scene,
            "openId": data.openId or "",
            "clientIp": data.clientIp or "",
            "idempotencyKey": data.idempotencyKey or "",
        },
    )
    db.add(order)
    db.flush()
    try:
        pay_payload = wechat_pay_service.get_pay_payload(order, package, data)
        _sync_order_amount_to_virtual_goods_price(order, pay_payload)
    except Exception:
        db.rollback()
        raise
    db.commit()
    db.refresh(order)
    return _serialize_payment_response(order, package, pay_payload)


def list_payment_orders(db: Session, current_user: AuthUser) -> dict:
    get_user_or_404(db, current_user.username)
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.username == current_user.username,
    ).order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    return {"list": [_serialize_order(order) for order in orders], "total": len(orders)}


def _hours_from_minutes(minutes: int | float | None) -> float:
    return round(max(float(minutes or 0), 0) / 60, 2)


def _money(value) -> float:
    return round(float(value or 0), 2)


def _refund_info(order: PaymentOrder) -> dict:
    payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    return payload.get("refund") if isinstance(payload.get("refund"), dict) else {}


def _serialize_refund_row(order: PaymentOrder, subscription: UserSubscription | None) -> dict:
    total_minutes = int(subscription.total_minutes or 0) if subscription else 0
    used_minutes = int(subscription.used_minutes or 0) if subscription else 0
    refundable_minutes = 0 if order.status == "refunded" else max(total_minutes - used_minutes, 0)
    amount = Decimal(str(order.amount or 0))
    refundable_amount = Decimal("0")
    if total_minutes > 0 and refundable_minutes > 0:
        refundable_amount = amount * Decimal(refundable_minutes) / Decimal(total_minutes)
    elif order.status == "paid" and total_minutes <= 0:
        refundable_amount = amount
    return {
        "orderNo": order.order_no,
        "username": order.username,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "amount": _money(order.amount),
        "status": order.status,
        "totalHours": _hours_from_minutes(total_minutes),
        "usedHours": _hours_from_minutes(used_minutes),
        "refundableHours": _hours_from_minutes(refundable_minutes),
        "refundableAmount": _money(refundable_amount),
        "paidAt": order.paid_at.isoformat() if order.paid_at else "",
        "createdAt": order.created_at.isoformat() if order.created_at else "",
        "refundInfo": _refund_info(order),
    }


def _subscription_for_order(db: Session, order: PaymentOrder) -> UserSubscription | None:
    return db.query(UserSubscription).filter(
        UserSubscription.username == order.username,
        UserSubscription.source_order_no == order.order_no,
    ).first()


def get_refund_balance_stats(db: Session, current_user: AuthUser, data: RefundBalanceStatsRequest) -> dict:
    _assert_admin(current_user)
    query = db.query(PaymentOrder).filter(PaymentOrder.status.in_(["paid", "refunded"]))
    if data.username:
        query = query.filter(PaymentOrder.username == data.username)
    if data.orderNo:
        query = query.filter(PaymentOrder.order_no == data.orderNo)
    orders = query.order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    rows = [_serialize_refund_row(order, _subscription_for_order(db, order)) for order in orders]
    summary = {
        "totalPaidAmount": _money(sum(row["amount"] for row in rows)),
        "totalHours": round(sum(row["totalHours"] for row in rows), 2),
        "usedHours": round(sum(row["usedHours"] for row in rows), 2),
        "refundableHours": round(sum(row["refundableHours"] for row in rows), 2),
        "refundableAmount": _money(sum(row["refundableAmount"] for row in rows)),
    }
    return {"list": rows, "total": len(rows), "summary": summary}


def apply_refund(db: Session, current_user: AuthUser, data: RefundApplyRequest) -> dict:
    _assert_admin(current_user)
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == data.orderNo).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "refunded":
        raise HTTPException(status_code=400, detail="订单已退款")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="仅已支付订单可退款")

    subscription = _subscription_for_order(db, order)
    row = _serialize_refund_row(order, subscription)
    requested_hours = data.refundedHours if data.refundedHours is not None else row["refundableHours"]
    refunded_hours = max(float(requested_hours or 0), 0)
    if refunded_hours <= 0:
        raise HTTPException(status_code=400, detail="退款小时数必须大于 0")
    if row["refundableHours"] and refunded_hours > row["refundableHours"]:
        raise HTTPException(status_code=400, detail="退款小时数超过可退额度")

    # Query WeChat for current order state including left_fee
    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")
    try:
        query_result = wechat_pay_service.query_virtual_order(order, package)
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"查询微信订单状态失败: {exc.detail}")

    left_fee = wechat_pay_service._extract_virtual_left_fee(query_result.get("raw") or {})
    if left_fee <= 0:
        raise HTTPException(status_code=400, detail="微信侧该订单无可退余额")

    total_hours = row["totalHours"] or refunded_hours
    refund_ratio = refunded_hours / total_hours if total_hours > 0 else 1.0
    refund_fee = int(left_fee * refund_ratio)
    if refund_fee <= 0:
        raise HTTPException(status_code=400, detail="退款金额为0，无需退款")
    refund_fee = min(refund_fee, left_fee)

    # Generate refund_order_id
    refund_order_id = f"RFND{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

    # Call WeChat refund API
    try:
        refund_result = wechat_pay_service.refund_virtual_order(
            order=order,
            refund_order_id=refund_order_id,
            left_fee=left_fee,
            refund_fee=refund_fee,
            refund_reason=data.refundReason or "3",
            req_from="1",
        )
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"微信退款发起失败: {exc.detail}")

    refunded_amount = Decimal(str(order.amount or 0)) * Decimal(str(refunded_hours)) / Decimal(str(total_hours))
    refund_payload = {
        "refundedHours": round(refunded_hours, 2),
        "refundedAmount": _money(refunded_amount),
        "refundFee": refund_fee,
        "leftFee": left_fee,
        "refundReason": data.refundReason or "",
        "refundRemark": data.refundRemark or "",
        "refundedBy": current_user.username,
        "refundedAt": datetime.now(timezone.utc).isoformat(),
        "refundOrderId": refund_order_id,
        "refundWxOrderId": refund_result.get("refundWxOrderId") or "",
        "mode": "wechat_virtual_refund",
        "wechatRaw": refund_result.get("raw") or {},
    }

    callback_payload = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
    callback_payload["refund"] = refund_payload
    order.callback_payload = callback_payload
    order.status = "refunded"

    if subscription:
        subscription.status = "refunded"
        subscription.used_minutes = int(subscription.total_minutes or 0)
        subscription.daily_used_minutes = int(subscription.daily_limit_minutes or subscription.daily_used_minutes or 0)
        extra = dict(subscription.extra_payload) if isinstance(subscription.extra_payload, dict) else {}
        extra["refund"] = refund_payload
        subscription.extra_payload = extra
        user = db.query(User).filter(User.username == order.username).first()
        if user and package:
            _sync_user_preferences_subscription(user, package, subscription)

    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "message": "退款已提交微信处理，请稍后在微信支付后台确认退款完成。",
        "order": _serialize_refund_row(order, subscription),
        "refund": refund_result,
    }


def compensate_subscription(db: Session, current_user: AuthUser, data: CompensateRequest) -> dict:
    _assert_admin(current_user)
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    subscription = db.query(UserSubscription).filter(
        UserSubscription.username == data.username,
        UserSubscription.status == "active",
    ).order_by(UserSubscription.created_at.desc()).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="该用户没有活跃订阅")

    additional = int(data.additionalMinutes)
    subscription.total_minutes = int(subscription.total_minutes or 0) + additional

    compensation = {
        "additionalMinutes": additional,
        "newTotalMinutes": int(subscription.total_minutes),
        "reason": data.reason or "",
        "remark": data.remark or "",
        "operator": current_user.username,
        "operatedAt": datetime.now(timezone.utc).isoformat(),
    }
    extra = dict(subscription.extra_payload) if isinstance(subscription.extra_payload, dict) else {}
    compensations = list(extra.get("compensations") or [])
    compensations.append(compensation)
    extra["compensations"] = compensations
    subscription.extra_payload = extra

    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == subscription.package_code).first()
    if package:
        _sync_user_preferences_subscription(user, package, subscription)

    db.commit()
    db.refresh(subscription)
    return {
        "success": True,
        "message": f"已为用户 {data.username} 追加 {additional} 分钟时长",
        "subscription": {
            "username": subscription.username,
            "packageCode": subscription.package_code,
            "planType": subscription.plan_type,
            "planName": subscription.plan_name,
            "status": subscription.status,
            "totalMinutes": subscription.total_minutes,
            "usedMinutes": subscription.used_minutes,
            "dailyLimitMinutes": subscription.daily_limit_minutes,
            "dailyUsedMinutes": subscription.daily_used_minutes,
        },
        "compensation": compensation,
    }


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
    pay_payload = {
        "mode": "query",
        "scene": (order.extra_payload or {}).get("scene", "mini_program") if isinstance(order.extra_payload, dict) else "mini_program",
        "message": "订单查询接口不重复生成支付签名，如需重新拉起支付，请重新创建订单或补充预下单刷新接口。",
    }
    return _serialize_payment_response(order, package, pay_payload)


def verify_virtual_payment_order(db: Session, current_user: AuthUser, order_no: str) -> dict:
    order = db.query(PaymentOrder).filter(
        PaymentOrder.order_no == order_no,
        PaymentOrder.username == current_user.username,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")
    query_result = _verify_order_with_wechat(order, package, raise_on_error=True)
    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "order": _serialize_order(order),
        "verification": query_result,
    }


def _sync_user_preferences_subscription(user: User, package: SubscriptionPackage, subscription: UserSubscription):
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    prefs["subscription"] = {
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": int(subscription.total_minutes or 0),
        "usedMinutes": int(subscription.used_minutes or 0),
        "dailyLimitMinutes": int(subscription.daily_limit_minutes or 0),
        "dailyUsedMinutes": int(subscription.daily_used_minutes or 0),
        "expiresAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "packageCode": package.package_code,
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
        return
    expected_total = int(round(float(order.amount or 0) * 100))
    if expected_total != int(amount_total):
        raise HTTPException(status_code=400, detail="回调金额与订单金额不一致")


def _extract_virtual_transaction_id(data: PaymentVirtualConfirmRequest) -> str:
    if data.thirdPartyOrderNo:
        return str(data.thirdPartyOrderNo)
    raw = data.rawResult if isinstance(data.rawResult, dict) else {}
    candidates = [
        raw.get("transactionId"),
        raw.get("transaction_id"),
        raw.get("orderId"),
        raw.get("order_id"),
        raw.get("paymentOrderId"),
        raw.get("payment_order_id"),
        raw.get("tradeNo"),
        raw.get("trade_no"),
    ]
    pay_info = raw.get("WeChatPayInfo") or raw.get("wechatPayInfo") or raw.get("wechat_pay_info")
    if isinstance(pay_info, dict):
        candidates.extend([
            pay_info.get("TransactionId"),
            pay_info.get("transactionId"),
            pay_info.get("transaction_id"),
        ])
    for value in candidates:
        if value not in (None, ""):
            return str(value)
    return ""


def _verify_order_with_wechat(order: PaymentOrder, package: SubscriptionPackage, raise_on_error: bool = False) -> dict:
    callback_payload = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
    try:
        query_result = wechat_pay_service.query_virtual_order(order, package)
    except HTTPException as exc:
        callback_payload["verified"] = False
        callback_payload["verifyPending"] = True
        callback_payload["verifyError"] = str(exc.detail)
        callback_payload["verifiedAt"] = datetime.now(timezone.utc).isoformat()
        order.callback_payload = callback_payload
        if raise_on_error:
            raise
        return {"verified": False, "verifyPending": True, "verifyError": str(exc.detail)}

    callback_payload["verified"] = bool(query_result.get("verified"))
    callback_payload["verifyPending"] = not bool(query_result.get("verified"))
    callback_payload["verifyError"] = ""
    callback_payload["verifiedAt"] = datetime.now(timezone.utc).isoformat()
    callback_payload["queryResult"] = query_result.get("raw") or {}
    callback_payload["queryRequest"] = query_result.get("request") or {}
    transaction_id = query_result.get("transactionId") or ""
    if transaction_id:
        order.third_party_order_no = transaction_id
    paid_at = _parse_paid_at(query_result.get("paidAt")) if query_result.get("paidAt") else order.paid_at
    if paid_at:
        order.paid_at = paid_at
    order.callback_payload = callback_payload
    if raise_on_error and not query_result.get("verified"):
        raise HTTPException(status_code=409, detail="微信虚拟支付查单未确认支付成功")
    return query_result


def _ensure_subscription_for_paid_order(db: Session, order: PaymentOrder, package: SubscriptionPackage, paid_at: datetime) -> UserSubscription:
    existing = db.query(UserSubscription).filter(
        UserSubscription.source_order_no == order.order_no,
        UserSubscription.username == order.username,
    ).first()
    end_at = paid_at + timedelta(days=int(package.duration_days or 0)) if int(package.duration_days or 0) > 0 else None
    if existing:
        existing.status = "active" if order.status == "paid" else order.status
        existing.plan_name = package.package_name
        existing.plan_type = package.package_type
        existing.total_minutes = int(package.total_minutes or 0)
        existing.daily_limit_minutes = int(package.daily_limit_minutes or 0)
        existing.end_at = end_at
        return existing
    subscription = UserSubscription(
        username=order.username,
        package_code=package.package_code,
        plan_type=package.package_type,
        plan_name=package.package_name,
        status="active" if order.status == "paid" else order.status,
        is_trial=(package.package_type == "trial"),
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


def confirm_virtual_payment_order(db: Session, current_user: AuthUser, order_no: str, data: PaymentVirtualConfirmRequest) -> dict:
    user = get_user_or_404(db, current_user.username)
    order = db.query(PaymentOrder).filter(
        PaymentOrder.order_no == order_no,
        PaymentOrder.username == current_user.username,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if data.scene != "mini_program_virtual":
        raise HTTPException(status_code=400, detail="订单确认场景不匹配")
    if data.payResult != "success":
        raise HTTPException(status_code=400, detail="小程序虚拟支付未成功，不能确认订单")

    package = _get_package_or_404(db, order.package_code)
    paid_at = _parse_paid_at(data.paidAt)
    if order.status == "paid":
        subscription = _ensure_subscription_for_paid_order(db, order, package, order.paid_at or paid_at)
        _sync_user_preferences_subscription(user, package, subscription)
        db.commit()
        return {
            "success": True,
            "idempotent": True,
            "message": "订单已支付，重复确认已忽略",
            "order": _serialize_order(order),
        }

    order.status = "paid"
    order.third_party_order_no = _extract_virtual_transaction_id(data) or order.third_party_order_no or ""
    order.paid_at = paid_at
    order.callback_payload = {
        "mode": "wechat_virtual_client_confirm",
        "verified": False,
        "verifyPending": True,
        "payResult": data.payResult,
        "rawResult": data.rawResult or {},
    }
    _verify_order_with_wechat(order, package, raise_on_error=False)
    subscription = _ensure_subscription_for_paid_order(db, order, package, paid_at)
    _sync_user_preferences_subscription(user, package, subscription)
    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "idempotent": False,
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
        },
    }


def handle_payment_callback(db: Session, data: PaymentCallbackRequest, headers: dict | None = None) -> dict:
    parsed = wechat_pay_service.parse_callback(data, headers)
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == parsed["orderNo"]).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    package = _get_package_or_404(db, order.package_code)
    user = db.query(User).filter(User.username == order.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="订单关联用户不存在")

    _assert_callback_amount(order, parsed.get("amountTotal"))
    paid_at = _parse_paid_at(parsed.get("paidAt"))

    if order.status == "paid":
        subscription = _ensure_subscription_for_paid_order(db, order, package, order.paid_at or paid_at)
        _sync_user_preferences_subscription(user, package, subscription)
        db.commit()
        return {
            "success": True,
            "idempotent": True,
            "message": "订单已支付，重复回调已忽略",
            "callbackMode": parsed["mode"],
            "verifyPending": parsed.get("verifyPending", False),
            "order": _serialize_order(order),
        }

    order.status = parsed.get("status") or "paid"
    order.third_party_order_no = parsed.get("transactionId") or order.third_party_order_no
    order.paid_at = paid_at
    order.callback_payload = {
        "mode": parsed["mode"],
        "verified": parsed.get("verified", False),
        "verifyPending": parsed.get("verifyPending", False),
        "headers": parsed.get("headers", {}),
        "payload": parsed.get("rawPayload", {}),
        "realCallbackTodo": parsed.get("realCallbackTodo", {}),
    }

    subscription = _ensure_subscription_for_paid_order(db, order, package, paid_at)
    _sync_user_preferences_subscription(user, package, subscription)
    db.commit()
    db.refresh(order)
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
        },
    }
