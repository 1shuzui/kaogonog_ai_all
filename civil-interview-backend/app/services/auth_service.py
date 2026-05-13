"""Auth service: login and register"""
from datetime import datetime, timedelta, timezone
import logging
import random

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.data.legal_documents import LATEST_TERMS_VERSION
from app.models.entities import User
from app.schemas.common import RegisterRequest

logger = logging.getLogger(__name__)
_reset_codes: dict[str, dict[str, object]] = {}


def user_role(user: User | None) -> str:
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role:
        return role
    if str(getattr(user, "username", "") or "").strip().lower() == "admin":
        return "admin"
    return "user"


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
    token = create_access_token(
        {"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info(
        "Login succeeded",
        extra={"event": "auth.login.succeeded", "username": user.username, "role": user_role(user)},
    )
    return {"access_token": token, "token_type": "bearer"}


def register_user(db: Session, data: RegisterRequest) -> dict:
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
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    _reset_codes.pop(_reset_key(username), None)
    logger.info(
        "Password reset completed",
        extra={"event": "auth.password_reset.completed", "username": user.username},
    )
    return {"success": True, "message": "密码已重置，请使用新密码登录"}
