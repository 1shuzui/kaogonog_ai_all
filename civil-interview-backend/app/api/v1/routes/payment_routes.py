import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, PaymentCallbackRequest, PaymentOrderCreateRequest, PaymentRefundApplyRequest, PaymentRefundStatsRequest
from app.services.payment_service import (
    apply_refund_by_hours,
    create_payment_order,
    get_payment_order,
    get_refund_balance_stats,
    handle_payment_callback,
    list_payment_orders,
)

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/orders")
def payment_create_order(data: PaymentOrderCreateRequest, request: Request, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    check_rate_limit(request, "payment:create", limit=12, window_seconds=600, identity=current_user.username)
    return create_payment_order(db, current_user, data)


@router.get("/orders/me")
def payment_list_orders(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_payment_orders(db, current_user)


@router.get("/orders/{order_no}")
def payment_get_order(order_no: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_payment_order(db, current_user, order_no)


@router.post("/admin/refund-stats")
def payment_refund_stats(data: PaymentRefundStatsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_refund_balance_stats(db, current_user, data)


@router.post("/admin/refund")
def payment_apply_refund(data: PaymentRefundApplyRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return apply_refund_by_hours(db, current_user, data)


@router.post("/callback/wechat")
async def payment_wechat_callback(request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "payment:wechat_callback", limit=120, window_seconds=60)
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="微信支付回调请求体不是合法 JSON") from exc
    data = PaymentCallbackRequest.model_validate(payload)
    return handle_payment_callback(db, data, dict(request.headers), raw_body)
