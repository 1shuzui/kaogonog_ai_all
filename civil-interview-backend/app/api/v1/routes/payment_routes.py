from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, PaymentCallbackRequest, PaymentOrderCreateRequest
from app.services.payment_service import create_payment_order, get_payment_order, handle_payment_callback, list_payment_orders

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/orders")
def payment_create_order(data: PaymentOrderCreateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_payment_order(db, current_user, data)


@router.get("/orders/me")
def payment_list_orders(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_payment_orders(db, current_user)


@router.get("/orders/{order_no}")
def payment_get_order(order_no: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_payment_order(db, current_user, order_no)


@router.post("/callback/wechat")
def payment_wechat_callback(data: PaymentCallbackRequest, db: Session = Depends(get_db)):
    return handle_payment_callback(db, data)
