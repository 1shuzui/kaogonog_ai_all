"""Auth service: login and register"""
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import random
import secrets
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.data.legal_documents import LATEST_TERMS_VERSION
from app.models.entities import User
from app.schemas.common import RegisterRequest, WechatMiniLoginRequest
from app.services.wechat_pay_service import wechat_pay_service

logger = logging.getLogger(__name__)
_reset_codes: dict[str, dict[str, object]] = {}
RESERVED_USERNAMES = {"admin", "administrator", "root", "superadmin"}


def user_role(user: User | None) -> str:
    role = str(getattr(user, "role", "") or "").strip().lower()
    return role or "user"


def _is_reserved_username(username: str) -> bool:
    return str(username or "").strip().lower() in RESERVED_USERNAMES


def _is_strong_admin_password(password: str) -> bool:
    value = str(password or "")
    if len(value) < 10:
        return False
    return (
        any(ch.islower() for ch in value)
        and any(ch.isupper() for ch in value)
        and any(ch.isdigit() for ch in value)
        and any(not ch.isalnum() for ch in value)
    )


def _ensure_admin_password_strength(user: User, password: str) -> None:
    if user_role(user) != "admin":
        return
    if _is_strong_admin_password(password):
        return
    raise HTTPException(status_code=403, detail="管理员账号必须使用至少 10 位且包含大小写字母、数字和符号的强密码")


def _issue_token_for_user(user: User) -> dict:
    token = create_access_token(
        {"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": token, "token_type": "bearer"}


def login_user(db: Session, username: str, password: str) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(
            "Login failed",
            extra={"event": "auth.login.failed", "username": username, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _ensure_admin_password_strength(user, password)
    logger.info(
        "Login succeeded",
        extra={"event": "auth.login.succeeded", "username": user.username, "role": user_role(user)},
    )
    return _issue_token_for_user(user)


def register_user(db: Session, data: RegisterRequest) -> dict:
    if _is_reserved_username(data.username):
        raise HTTPException(status_code=400, detail="该用户名为系统保留账号，不能注册")

    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        logger.warning(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "duplicate_username"},
        )
        raise HTTPException(status_code=400, detail="Username already registered")

    agreed_terms_version = str(data.agreed_terms_version or "").strip()
    if agreed_terms_version != LATEST_TERMS_VERSION:
        raise HTTPException(status_code=400, detail="注册前请先阅读并同意最新版用户协议与隐私协议")

    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name or data.username,
        email=data.email or "",
        role="user",
        agreed_terms_version=LATEST_TERMS_VERSION,
        agreed_terms_at=datetime.now(timezone.utc),
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "integrity_error"},
        )
        raise HTTPException(status_code=400, detail="Username already registered") from None
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "database_error"},
        )
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试") from None
    logger.info(
        "Register succeeded",
        extra={"event": "auth.register.succeeded", "username": user.username},
    )
    return {"success": True, "message": "User created successfully"}


def _wechat_username(openid: str) -> str:
    digest = hashlib.sha256(openid.encode("utf-8")).hexdigest()[:16]
    return f"wx_{digest}"


def _unique_wechat_username(db: Session, openid: str) -> str:
    base = _wechat_username(openid)
    candidate = base
    for _ in range(10):
        if not db.query(User).filter(User.username == candidate).first():
            return candidate
        candidate = f"{base}_{secrets.token_hex(2)}"
    raise HTTPException(status_code=500, detail="微信账号初始化失败，请稍后重试")


def login_or_register_miniprogram_wechat(db: Session, data: WechatMiniLoginRequest) -> dict:
    session = wechat_pay_service.exchange_code_for_session(data.code)
    openid = str(session.get("openid") or "").strip()
    unionid = str(session.get("unionid") or "").strip()
    if not openid:
        raise HTTPException(status_code=502, detail="微信登录响应缺少 openid")

    user = db.query(User).filter(User.wechat_mini_openid == openid).first()
    if not user and unionid:
        user = db.query(User).filter(User.wechat_unionid == unionid, User.wechat_unionid != "").first()
    is_new_user = False

    if user:
        if user_role(user) == "admin":
            raise HTTPException(status_code=403, detail="管理员账号不支持微信快捷登录")
        if not user.wechat_mini_openid:
            user.wechat_mini_openid = openid
        if unionid and not user.wechat_unionid:
            user.wechat_unionid = unionid
        db.commit()
    else:
        agreed_terms_version = str(data.agreed_terms_version or "").strip()
        if agreed_terms_version != LATEST_TERMS_VERSION:
            raise HTTPException(status_code=400, detail="登录前请先阅读并同意最新版用户协议与隐私协议")
        user = User(
            username=_unique_wechat_username(db, openid),
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name="微信用户",
            role="user",
            wechat_mini_openid=openid,
            wechat_unionid=unionid or None,
            agreed_terms_version=LATEST_TERMS_VERSION,
            agreed_terms_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        is_new_user = True

    db.refresh(user)
    logger.info(
        "Wechat mini login succeeded",
        extra={"event": "auth.wechat_mini.succeeded", "username": user.username, "is_new_user": is_new_user},
    )
    return {**_issue_token_for_user(user), "username": user.username, "isNewUser": is_new_user}


def get_wechat_web_login_config() -> dict:
    configured = all((settings.wechat_web_appid, settings.wechat_web_app_secret, settings.wechat_web_redirect_uri))
    if not configured:
        return {
            "configured": False,
            "loginUrl": "",
            "message": "PC 微信扫码登录未启用：缺少微信开放平台网站应用 AppID/AppSecret/授权回调域名。",
            "requiredEnv": ["WECHAT_WEB_APPID", "WECHAT_WEB_APP_SECRET", "WECHAT_WEB_REDIRECT_URI"],
        }
    params = urlencode(
        {
            "appid": settings.wechat_web_appid,
            "redirect_uri": settings.wechat_web_redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": secrets.token_urlsafe(18),
        }
    )
    return {
        "configured": True,
        "loginUrl": f"https://open.weixin.qq.com/connect/qrconnect?{params}#wechat_redirect",
        "message": "PC 微信扫码登录已配置。",
    }


def _reset_key(username: str) -> str:
    return str(username or "").strip().lower()


def _reset_contact_matches(user: User, contact: str = "") -> bool:
    normalized = str(contact or "").strip().lower()
    if not normalized:
        return True
    email = str(user.email or "").strip().lower()
    return bool(email and normalized == email)


def _find_reset_user(db: Session, username: str, contact: str = "") -> User:
    normalized_username = str(username or "").strip()
    if not normalized_username:
        raise HTTPException(status_code=400, detail="请输入用户名")

    user = db.query(User).filter(User.username == normalized_username).first()
    if not user or not _reset_contact_matches(user, contact):
        logger.warning(
            "Password reset lookup failed",
            extra={"event": "auth.password_reset.lookup_failed", "username": normalized_username},
        )
        raise HTTPException(status_code=404, detail="未找到匹配账号，请核对用户名或联系管理员")
    return user


def _sms_ready() -> bool:
    return all((
        settings.sms_provider,
        settings.sms_access_key_id,
        settings.sms_access_key_secret,
        settings.sms_sign_name,
        settings.sms_template_code,
    ))


def _store_reset_code(username: str, code: str) -> datetime:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_code_ttl_minutes)
    _reset_codes[_reset_key(username)] = {
        "code": code,
        "expires_at": expires_at,
        "verified": False,
    }
    return expires_at


def request_password_reset(db: Session, username: str, contact: str = "") -> dict:
    user = _find_reset_user(db, username, contact)
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    expires_at = _store_reset_code(user.username, code)

    sms_ready = _sms_ready()
    logger.info(
        "Password reset code generated",
        extra={
            "event": "auth.password_reset.requested",
            "username": user.username,
            "expires_at": expires_at.isoformat(),
            "sms_ready": sms_ready,
        },
    )

    response = {
        "success": True,
        "message": "验证码已生成。当前未接入短信服务时，请联系管理员获取验证码。",
        "expiresAt": expires_at.isoformat(),
        "smsReady": sms_ready,
        "smsRequirements": {
            "provider": "短信服务商账号，例如阿里云/腾讯云短信",
            "requiredEnv": [
                "SMS_PROVIDER",
                "SMS_ACCESS_KEY_ID",
                "SMS_ACCESS_KEY_SECRET",
                "SMS_SIGN_NAME",
                "SMS_TEMPLATE_CODE",
            ],
            "notes": "还需要已审核短信签名、验证码模板、费用余额和服务商要求的主体资质。",
        },
    }
    if settings.password_reset_code_debug_response:
        response["debugCode"] = code
    return response


def verify_password_reset_code(username: str, code: str) -> dict:
    record = _reset_codes.get(_reset_key(username))
    now = datetime.now(timezone.utc)
    if not record or record.get("expires_at") <= now or record.get("code") != str(code or "").strip():
        raise HTTPException(status_code=400, detail="验证码无效或已过期")
    record["verified"] = True
    return {"success": True, "message": "验证通过"}


def reset_password_with_code(db: Session, username: str, code: str, new_password: str) -> dict:
    verify_password_reset_code(username, code)
    user = _find_reset_user(db, username)
    _ensure_admin_password_strength(user, new_password)
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    _reset_codes.pop(_reset_key(username), None)
    logger.info(
        "Password reset completed",
        extra={"event": "auth.password_reset.completed", "username": user.username},
    )
    return {"success": True, "message": "密码已重置，请使用新密码登录"}
