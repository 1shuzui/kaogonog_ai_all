"""
支付与到账服务层，负责套餐订单、微信小程序虚拟支付确认、退款申请和支付成功后的权益生成。

微信审核要求虚拟训练权益必须走官方小程序虚拟支付能力，因此这里不保留普通微信支付分支，也不让人工补偿伪装成支付订单。
订单表只记录真实购买和退款状态；支付成功后再创建或更新 `UserSubscription`，并同步用户偏好里的权益快照。
退款扣减、客服补偿和测试账号赠送属于管理员人工权益调整，应走 `entitlement_admin_service.py` 留审计流水。

@param: 服务函数接收数据库 Session、当前用户、套餐编码、支付确认参数、退款申请或后台退款操作请求。
@return: 返回订单详情、支付参数、退款统计、退款结果或最新权益摘要。
@raises HTTPException: 套餐不存在、订单状态不合法、微信查询失败、退款越界或用户无权限时抛出 HTTP 错误。
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import (
    AuthUser,
    PaymentOrderCreateRequest,
    PaymentVirtualConfirmRequest,
    RefundApplyRequest,
    RefundBalanceStatsRequest,
)
from app.services.wechat_pay_service import wechat_pay_service
from app.services.invite_service import record_payment_event_for_order, update_payment_event_refund
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
    """
    创建本地支付订单并生成微信小程序虚拟支付 payload。

    虚拟训练权益属于微信审核认定的虚拟商品，所以这里不允许普通支付兜底。订单先落本地 pending，再调用微信虚拟支付服务生成拉起参数；如果微信参数生成失败会回滚本地订单，避免出现无法支付的悬空单。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户，订单归属和 openId 都以它为准。
    @param data: 下单请求，包含套餐、支付渠道、场景、openId 和幂等键。
    @return: 本地订单摘要、套餐信息和小程序拉起虚拟支付所需 payload。
    @raises HTTPException: 用户/套餐不存在、支付渠道不符合虚拟支付或微信配置不可用时抛出。
    """
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
    """
    列出当前用户自己的支付订单。

    订单中心只展示本人订单，管理员核查退款走单独后台接口；这样普通用户无法通过订单号枚举别人的支付记录。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @return: 按创建时间倒序排列的订单列表和总数。
    @raises HTTPException: 用户不存在时由 get_user_or_404 抛出。
    """
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
    """
    管理员查询可退款余额统计。

    退款前需要同时看本地订单、关联权益、已用时长和微信侧可退余额。这个接口只做本地可退额度预估，真正退款仍必须走微信虚拟支付退款接口。

    @param db: 请求级数据库会话。
    @param current_user: 当前管理员用户。
    @param data: 用户名或订单号筛选条件。
    @return: 可退款订单列表和汇总金额/小时数。
    @raises HTTPException: 非管理员访问时抛出 403。
    """
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
    """
    管理员发起微信虚拟支付退款。

    退款不能只把本地订单改成 refunded，必须先查微信订单、计算可退 left_fee，再调用微信退款接口。成功后才同步本地订单、权益状态和退款 payload，保证客服后台与微信交易订单可对账。

    @param db: 请求级数据库会话。
    @param current_user: 当前管理员用户。
    @param data: 退款申请，包含订单号、退款小时数、原因和备注。
    @return: 退款提交结果、更新后的订单退款行和微信响应。
    @raises HTTPException: 非管理员、订单不可退、微信查单失败或微信退款失败时抛出。
    """
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
        if exc.status_code < 500:
            raise
        raise HTTPException(status_code=502, detail=f"查询微信订单状态失败: {exc.detail}")

    left_fee = wechat_pay_service._extract_virtual_left_fee(query_result.get("raw") or {})
    if left_fee <= 0:
        raise HTTPException(status_code=400, detail="微信侧该订单无可退余额")

    total_hours = row["totalHours"] or refunded_hours
    refund_ratio = refunded_hours / total_hours if total_hours > 0 else 1.0
    refund_fee = int(left_fee * refund_ratio)
    if refund_fee <= 0 and left_fee > 0 and refund_ratio > 0:
        refund_fee = 1
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
        if exc.status_code < 500:
            raise
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

    update_payment_event_refund(db, order, refunded_amount)
    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "message": "退款已提交微信官方小程序虚拟支付接口处理，请稍后在虚拟支付交易订单中确认退款完成。",
        "order": _serialize_refund_row(order, subscription),
        "refund": refund_result,
    }


def get_payment_order(db: Session, current_user: AuthUser, order_no: str) -> dict:
    """
    读取当前用户自己的单个订单。

    查询订单不会重新生成支付签名，避免用户刷新订单页时重复制造支付参数；需要重新支付时应回套餐中心重新下单。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @param order_no: 本地订单号。
    @return: 订单摘要和只读查询提示 payload。
    @raises HTTPException: 订单不存在或套餐配置不存在时抛出。
    """
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
        "message": "订单查询接口不重复生成虚拟支付签名，如需重新拉起支付，请在微信小程序套餐中心重新发起官方小程序虚拟支付。",
    }
    return _serialize_payment_response(order, package, pay_payload)


def _serialize_payment_verification(query_result: dict | None, order: PaymentOrder) -> dict:
    """只向端侧返回核验摘要，不暴露微信原始响应、openid 或签名请求参数。"""
    source = query_result if isinstance(query_result, dict) else {}
    callback_payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    amount_total = source.get("amountTotal")
    try:
        amount_total = int(amount_total) if amount_total not in (None, "") else None
    except (TypeError, ValueError):
        amount_total = None
    return {
        "verified": source.get("verified") is True or callback_payload.get("verified") is True,
        "orderStatus": source.get("orderStatus"),
        "amountTotal": amount_total,
        "transactionId": str(source.get("transactionId") or order.third_party_order_no or ""),
        "paidAt": str(source.get("paidAt") or (order.paid_at.isoformat() if order.paid_at else "")),
    }


def verify_virtual_payment_order(db: Session, current_user: AuthUser, order_no: str) -> dict:
    """
    主动向微信核验当前用户订单是否已支付。

    小程序支付完成后的回调/确认可能受网络影响，用户端可以调用这里补核单。核验成功会更新本地订单状态，但仍以后端创建权益为准。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @param order_no: 本地订单号。
    @return: 本地订单摘要和微信核验结果。
    @raises HTTPException: 订单/套餐不存在、微信查单失败或微信返回未支付时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    order = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.order_no == order_no,
            PaymentOrder.username == current_user.username,
        )
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in {"pending", "paid"}:
        raise HTTPException(status_code=409, detail="当前订单状态不能核验到账")
    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")
    callback_payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    idempotent = order.status == "paid" and callback_payload.get("verified") is True
    query_result = callback_payload.get("verification") if idempotent else _verify_order_with_wechat(
        order,
        package,
        raise_on_error=True,
    )
    try:
        subscription = _finalize_verified_order(db, user, order, package)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="订单核验成功，但权益入账失败，请稍后重试") from None
    _sync_wechat_delivery_after_commit(db, order)
    db.refresh(order)
    return {
        "success": True,
        "idempotent": idempotent,
        "order": _serialize_order(order),
        "verification": _serialize_payment_verification(query_result, order),
        "subscription": _serialize_subscription(subscription),
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
    try:
        query_result = wechat_pay_service.query_virtual_order(order, package)
    except HTTPException as exc:
        if raise_on_error:
            raise
        return {"verified": False, "verifyPending": True, "verifyError": str(exc.detail)}

    if not query_result.get("verified"):
        if raise_on_error:
            raise HTTPException(status_code=409, detail="微信虚拟支付查单未确认支付成功")
        return {**query_result, "verified": False, "verifyPending": True, "verifyError": "微信未确认支付成功"}

    extra_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
    expected_amount = extra_payload.get("virtualGoodsPrice")
    if expected_amount in (None, ""):
        expected_amount = Decimal(str(order.amount or 0)) * Decimal("100")
    try:
        expected_amount = int(expected_amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=500, detail="本地订单金额配置无效，已停止发放权益") from None

    authoritative_order_id = str(query_result.get("orderId") or "").strip()
    if authoritative_order_id and authoritative_order_id != order.order_no:
        if raise_on_error:
            raise HTTPException(status_code=409, detail="微信订单号与本地订单不一致，已停止发放权益")
        return {**query_result, "verified": False, "verifyPending": True, "verifyError": "订单号不一致"}

    order_type = query_result.get("orderType")
    try:
        invalid_order_type = order_type not in (None, "") and int(order_type) != 0
    except (TypeError, ValueError):
        invalid_order_type = True
    if invalid_order_type:
        if raise_on_error:
            raise HTTPException(status_code=409, detail="微信返回的不是支付订单，已停止发放权益")
        return {**query_result, "verified": False, "verifyPending": True, "verifyError": "订单类型不一致"}

    reported_amount = query_result.get("amountTotal")
    try:
        amount_mismatch = reported_amount in (None, "") or int(reported_amount) != expected_amount
    except (TypeError, ValueError):
        amount_mismatch = True
    if amount_mismatch:
        if raise_on_error:
            raise HTTPException(status_code=409, detail="微信订单金额与本地订单不一致，已停止发放权益")
        return {**query_result, "verified": False, "verifyPending": True, "verifyError": "订单金额不一致"}

    callback_payload = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
    callback_payload["mode"] = "wechat_virtual_server_verify"
    callback_payload["verified"] = True
    callback_payload["verifyPending"] = False
    callback_payload["verifyError"] = ""
    callback_payload["verifiedAt"] = datetime.now(timezone.utc).isoformat()
    callback_payload["queryResult"] = query_result.get("raw") or {}
    request_payload = query_result.get("request") if isinstance(query_result.get("request"), dict) else {}
    callback_payload["queryRequest"] = {
        key: request_payload[key]
        for key in ("order_id", "wx_order_id", "env", "product_id")
        if request_payload.get(key) not in (None, "")
    }
    callback_payload["verification"] = _serialize_payment_verification(query_result, order)
    transaction_id = query_result.get("transactionId") or ""
    if transaction_id:
        order.third_party_order_no = transaction_id
    paid_at = _parse_paid_at(query_result.get("paidAt")) if query_result.get("paidAt") else order.paid_at
    if paid_at:
        order.paid_at = paid_at
    order.callback_payload = callback_payload
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


def _serialize_subscription(subscription: UserSubscription) -> dict:
    return {
        "username": subscription.username,
        "packageCode": subscription.package_code,
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": subscription.total_minutes,
        "dailyLimitMinutes": subscription.daily_limit_minutes,
        "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
        "endAt": subscription.end_at.isoformat() if subscription.end_at else "",
    }


def _finalize_verified_order(
    db: Session,
    user: User,
    order: PaymentOrder,
    package: SubscriptionPackage,
) -> UserSubscription:
    callback_payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    if callback_payload.get("verified") is not True:
        raise HTTPException(status_code=409, detail="微信尚未确认支付成功，不能发放权益")
    order.status = "paid"
    order.paid_at = order.paid_at or datetime.now(timezone.utc)
    subscription = _ensure_subscription_for_paid_order(db, order, package, order.paid_at)
    _sync_user_preferences_subscription(user, package, subscription)
    record_payment_event_for_order(db, order)
    return subscription


def _sync_wechat_delivery_after_commit(db: Session, order: PaymentOrder) -> dict:
    """
    本地权益提交成功后同步微信发货状态；外部通知失败不回滚用户已经到账的权益。

    微信 XPay 状态 2 表示已支付待发货，需要调用 notify_provide_goods；状态 3/4 已进入或完成发货，
    只补记本地状态。失败状态写回订单供后续 confirm/verify 幂等重试，不把微信原始响应暴露给端侧。
    """
    callback_payload = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
    verification = callback_payload.get("verification") if isinstance(callback_payload.get("verification"), dict) else {}
    raw_status = verification.get("orderStatus")
    try:
        order_status = int(raw_status) if raw_status not in (None, "") else None
    except (TypeError, ValueError):
        order_status = None

    current_delivery = callback_payload.get("delivery") if isinstance(callback_payload.get("delivery"), dict) else {}
    if current_delivery.get("status") == "confirmed":
        return {"status": "confirmed", "idempotent": True}
    if order_status not in {2, 3, 4}:
        return {"status": "not_applicable", "idempotent": True}

    now_iso = datetime.now(timezone.utc).isoformat()
    if order_status in {3, 4}:
        callback_payload["delivery"] = {
            "status": "confirmed",
            "source": "wechat_query",
            "confirmedAt": now_iso,
            "error": "",
        }
        order.callback_payload = callback_payload
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        return {"status": "confirmed", "idempotent": True}

    try:
        wechat_pay_service.notify_provide_goods(order)
    except Exception as exc:
        detail = getattr(exc, "detail", None) if isinstance(exc, HTTPException) else None
        detail = detail or "微信发货通知暂时失败"
        callback_payload["delivery"] = {
            "status": "pending",
            "source": "notify_provide_goods",
            "attemptedAt": now_iso,
            "error": str(detail)[:240],
        }
        order.callback_payload = callback_payload
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        return {"status": "pending", "idempotent": False}

    callback_payload["delivery"] = {
        "status": "confirmed",
        "source": "notify_provide_goods",
        "attemptedAt": now_iso,
        "confirmedAt": datetime.now(timezone.utc).isoformat(),
        "error": "",
    }
    order.callback_payload = callback_payload
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return {"status": "confirmed_unrecorded", "idempotent": False}
    return {"status": "confirmed", "idempotent": False}


def confirm_virtual_payment_order(db: Session, current_user: AuthUser, order_no: str, data: PaymentVirtualConfirmRequest) -> dict:
    """
    确认小程序虚拟支付成功并发放权益。

    端侧的 payResult 只用于决定是否立即发起查单，不能作为到账依据。服务端持锁查询微信订单，
    核对支付状态和金额后，才在同一事务里标记 paid、创建权益并刷新用户 preferences；重复确认保持幂等。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @param order_no: 本地订单号。
    @param data: 小程序支付完成后上报的场景、结果和 paidAt。
    @return: 确认结果、订单摘要和最新权益状态。
    @raises HTTPException: 场景不匹配、支付未成功、订单不存在或核验失败时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    order = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.order_no == order_no,
            PaymentOrder.username == current_user.username,
        )
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if data.scene != "mini_program_virtual":
        raise HTTPException(status_code=400, detail="订单确认场景不匹配")
    if data.payResult != "success":
        raise HTTPException(status_code=400, detail="小程序虚拟支付未成功，不能确认订单")
    if order.status not in {"pending", "paid"}:
        raise HTTPException(status_code=409, detail="当前订单状态不能确认到账")

    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")
    callback_payload = order.callback_payload if isinstance(order.callback_payload, dict) else {}
    already_verified = order.status == "paid" and callback_payload.get("verified") is True
    if already_verified:
        try:
            subscription = _finalize_verified_order(db, user, order, package)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(status_code=500, detail="订单已支付，但权益恢复失败，请稍后重试") from None
        _sync_wechat_delivery_after_commit(db, order)
        return {
            "success": True,
            "idempotent": True,
            "message": "订单已支付，重复确认已忽略",
            "order": _serialize_order(order),
            "subscription": _serialize_subscription(subscription),
        }

    _verify_order_with_wechat(order, package, raise_on_error=True)
    verified_payload = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
    verified_payload["clientConfirmation"] = {
        "payResult": data.payResult,
        "reportedTransactionId": str(data.thirdPartyOrderNo or _extract_virtual_transaction_id(data))[:128],
        "reportedPaidAt": str(data.paidAt or "")[:64],
    }
    order.callback_payload = verified_payload
    try:
        subscription = _finalize_verified_order(db, user, order, package)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="支付已核验，但权益入账失败，请稍后重试") from None
    _sync_wechat_delivery_after_commit(db, order)
    db.refresh(order)
    return {
        "success": True,
        "idempotent": False,
        "order": _serialize_order(order),
        "subscription": _serialize_subscription(subscription),
    }
