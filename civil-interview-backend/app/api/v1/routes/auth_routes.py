from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RegisterRequest,
)
from app.services.auth_service import (
    login_user,
    register_user,
    request_password_reset,
    reset_password_with_code,
    verify_password_reset_code,
)

router = APIRouter(tags=["auth"])


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login_user(db, form_data.username, form_data.password)


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, data)


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    return request_password_reset(db, data.username, data.contact or "")


@router.post("/password-reset/verify")
def password_reset_verify(data: PasswordResetVerifyRequest):
    return verify_password_reset_code(data.username, data.code)


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    return reset_password_with_code(db, data.username, data.code, data.new_password)
