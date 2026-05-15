from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.schemas.common import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RegisterRequest,
    WechatMiniLoginRequest,
)
from app.services.auth_service import (
    get_wechat_web_login_config,
    login_user,
    login_or_register_miniprogram_wechat,
    register_user,
    request_password_reset,
    reset_password_with_code,
    verify_password_reset_code,
)

router = APIRouter(tags=["auth"])


@router.post("/token")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:login", limit=10, window_seconds=300, identity=form_data.username)
    return login_user(db, form_data.username, form_data.password)


@router.post("/register")
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:register", limit=6, window_seconds=600, identity=data.username)
    return register_user(db, data)


@router.post("/auth/wechat/miniprogram")
def wechat_miniprogram_login(data: WechatMiniLoginRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:wechat_mini", limit=12, window_seconds=300)
    return login_or_register_miniprogram_wechat(db, data)


@router.post("/wechat/miniprogram", include_in_schema=False)
def wechat_miniprogram_login_legacy(data: WechatMiniLoginRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:wechat_mini", limit=12, window_seconds=300)
    return login_or_register_miniprogram_wechat(db, data)


@router.get("/auth/wechat/web/url")
def wechat_web_login_url():
    return get_wechat_web_login_config()


@router.get("/wechat/web/url", include_in_schema=False)
def wechat_web_login_url_legacy():
    return get_wechat_web_login_config()


@router.get("/auth/wechat/web/callback")
def wechat_web_login_callback():
    raise HTTPException(status_code=501, detail="PC 微信扫码登录回调尚未启用，需先配置微信开放平台网站应用资料")


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:password_reset", limit=5, window_seconds=600, identity=data.username)
    return request_password_reset(db, data.username, data.contact or "")


@router.post("/password-reset/verify")
def password_reset_verify(data: PasswordResetVerifyRequest, request: Request):
    check_rate_limit(request, "auth:password_reset_verify", limit=10, window_seconds=600, identity=data.username)
    return verify_password_reset_code(data.username, data.code)


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirmRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "auth:password_reset_confirm", limit=6, window_seconds=600, identity=data.username)
    return reset_password_with_code(db, data.username, data.code, data.new_password)
