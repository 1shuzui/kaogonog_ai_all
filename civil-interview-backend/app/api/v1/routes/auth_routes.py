from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RegisterRequest,
    WechatMiniProgramAccountRequest,
    WechatMiniProgramBindRequest,
    WechatMiniProgramLoginRequest,
)
from app.services.auth_service import (
    bind_wechat_miniprogram,
    confirm_password_reset,
    login_user,
    login_wechat_miniprogram,
    register_user,
    request_password_reset,
    setup_wechat_miniprogram_account,
    verify_password_reset,
)

router = APIRouter(tags=["auth"])


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login_user(db, form_data.username, form_data.password)


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, data)


@router.post("/auth/wechat/miniprogram")
def wechat_miniprogram_login(data: WechatMiniProgramLoginRequest, db: Session = Depends(get_db)):
    return login_wechat_miniprogram(db, data)


@router.post("/auth/wechat/miniprogram/bind")
def wechat_miniprogram_bind(
    data: WechatMiniProgramBindRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return bind_wechat_miniprogram(db, current_user, data)


@router.post("/auth/wechat/miniprogram/account")
def wechat_miniprogram_account(
    data: WechatMiniProgramAccountRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return setup_wechat_miniprogram_account(db, current_user, data)


@router.get("/auth/wechat/web/url")
def wechat_web_login_url():
    return {"enabled": False, "url": "", "message": "PC 微信扫码登录暂未开通，请使用账号密码登录。"}


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    return request_password_reset(db, data)


@router.post("/password-reset/verify")
def password_reset_verify(data: PasswordResetVerifyRequest, db: Session = Depends(get_db)):
    return verify_password_reset(db, data)


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    return confirm_password_reset(db, data)
