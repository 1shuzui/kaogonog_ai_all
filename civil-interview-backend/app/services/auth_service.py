"""
这个文件专门处理账号登录、注册、微信小程序登录和密码重置；把这些入口放在一起，是为了避免 PC、小程序和管理员端各写一套身份规则。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import HTTPException, status
import requests
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.entities import User
from app.schemas.common import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RegisterRequest,
    WechatMiniProgramAccountRequest,
    WechatMiniProgramBindRequest,
    WechatMiniProgramLoginRequest,
)

WECHAT_ACCOUNT_PREFIX = "wxmp_"
PASSWORD_RESET_TTL_SECONDS = 15 * 60


def _make_token(username: str) -> str:
    return create_access_token(
        {"sub": username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def _auth_response(user: User, extra: dict | None = None) -> dict:
    response = {
        "access_token": _make_token(user.username),
        "token_type": "bearer",
        "username": user.username,
    }
    if extra:
        response.update(extra)
    return response


def _mark_login_success(db: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    user.last_login_at = now
    user.last_active_at = now
    db.commit()
    db.refresh(user)


def _preferences(user: User) -> dict:
    return dict(user.preferences) if isinstance(user.preferences, dict) else {}


def _save_preferences(user: User, prefs: dict) -> None:
    user.preferences = prefs


def _stable_wechat_username(openid: str) -> str:
    digest = hashlib.sha256(openid.encode("utf-8")).hexdigest()[:20]
    return f"{WECHAT_ACCOUNT_PREFIX}{digest}"


def _code_to_session(code: str) -> dict:
    code = str(code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="微信 code 不能为空")
    if not settings.wechat_pay_appid or not settings.wechat_miniprogram_app_secret:
        raise HTTPException(status_code=503, detail="微信小程序登录未配置")

    response = requests.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params={
            "appid": settings.wechat_pay_appid,
            "secret": settings.wechat_miniprogram_app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=settings.wechat_pay_request_timeout,
    )
    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="微信登录服务响应异常") from None
    if payload.get("errcode"):
        raise HTTPException(status_code=400, detail=payload.get("errmsg") or "微信登录失败")
    if not payload.get("openid"):
        raise HTTPException(status_code=400, detail="微信登录未返回 openid")
    return payload


def _find_user_by_wechat_openid(db: Session, openid: str) -> User | None:
    marker = f'"openId": "{openid}"'
    compact_marker = f'"openId":"{openid}"'
    candidates = db.query(User).filter(User.preferences.isnot(None)).all()
    for user in candidates:
        prefs = _preferences(user)
        mini = prefs.get("wechatMiniProgram") if isinstance(prefs.get("wechatMiniProgram"), dict) else {}
        if mini.get("openId") == openid:
            return user
        # Some DB dialects return JSON text through SQLAlchemy; keep a fallback
        # scan for older rows without relying on dialect-specific JSON operators.
        raw = str(user.preferences)
        if marker in raw or compact_marker in raw:
            return user
    return None


def _mark_wechat_binding(user: User, session_info: dict) -> None:
    prefs = _preferences(user)
    prefs["wechatMiniProgram"] = {
        "openId": session_info.get("openid", ""),
        "unionId": session_info.get("unionid", ""),
        "sessionKey": session_info.get("session_key", ""),
        "boundAt": datetime.now(timezone.utc).isoformat(),
    }
    _save_preferences(user, prefs)


def _account_login_payload(user: User) -> dict:
    generated = user.username.startswith(WECHAT_ACCOUNT_PREFIX)
    prefs = _preferences(user)
    mini = prefs.get("wechatMiniProgram") if isinstance(prefs.get("wechatMiniProgram"), dict) else {}
    return {
        "requiresPcAccountSetup": generated,
        "pcLoginUsername": "" if generated else user.username,
        "wechatGeneratedUsername": user.username if generated else "",
        "wechatMiniBound": bool(mini.get("openId")),
    }


def login_user(db: Session, username: str, password: str) -> dict:
    """
    login_user 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @param password: 用户提交的凭据明文；只在校验/哈希边界短暂使用，避免持久化原文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _mark_login_success(db, user)
    return _auth_response(user)


def register_user(db: Session, data: RegisterRequest) -> dict:
    """
    register_user 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException, IntegrityError, SQLAlchemyError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name or data.username,
        email=data.email or "",
    )
    if data.agreedTermsVersion:
        user.agreed_terms_version = data.agreedTermsVersion
        user.agreed_terms_at = datetime.now(timezone.utc)
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already registered") from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试") from None
    return {"success": True, "message": "User created successfully"}


def login_wechat_miniprogram(db: Session, data: WechatMiniProgramLoginRequest) -> dict:
    """
    login_wechat_miniprogram 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    session_info = _code_to_session(data.code)
    openid = session_info["openid"]
    user = _find_user_by_wechat_openid(db, openid)
    created = False
    if not user:
        username = _stable_wechat_username(openid)
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                hashed_password=get_password_hash(secrets.token_urlsafe(24)),
                full_name="微信用户",
                email="",
            )
            db.add(user)
            db.flush()
            created = True
    _mark_wechat_binding(user, session_info)
    if data.agreedTermsVersion:
        user.agreed_terms_version = data.agreedTermsVersion
        user.agreed_terms_at = datetime.now(timezone.utc)
    _mark_login_success(db, user)
    account_login = _account_login_payload(user)
    return _auth_response(user, {
        "created": created,
        "requiresPcAccountSetup": account_login["requiresPcAccountSetup"],
        "accountBindings": {
            "wechatMiniBound": account_login["wechatMiniBound"],
            "wechatUnionBound": False,
            "wechatWebBound": False,
        },
        "accountLogin": account_login,
    })


def bind_wechat_miniprogram(db: Session, current_user, data: WechatMiniProgramBindRequest) -> dict:
    """
    bind_wechat_miniprogram 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    session_info = _code_to_session(data.code)
    existing = _find_user_by_wechat_openid(db, session_info["openid"])
    if existing and existing.username != user.username:
        raise HTTPException(status_code=409, detail="该微信已绑定其他账号")
    _mark_wechat_binding(user, session_info)
    db.commit()
    return {"success": True, "message": "微信已绑定", "wechatMiniBound": True}


def setup_wechat_miniprogram_account(db: Session, current_user, data: WechatMiniProgramAccountRequest) -> dict:
    """
    setup_wechat_miniprogram_account 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.username.startswith(WECHAT_ACCOUNT_PREFIX):
        _mark_login_success(db, user)
        return _auth_response(user, {"message": "当前账号已可用于 PC 登录", "requiresPcAccountSetup": False})

    target_username = str(data.username or "").strip()
    if len(target_username) < 3 or len(target_username) > 32:
        raise HTTPException(status_code=400, detail="账号需为 3-32 位")
    if db.query(User).filter(User.username == target_username).first():
        raise HTTPException(status_code=400, detail="用户名已被占用")

    user.username = target_username
    user.hashed_password = get_password_hash(data.password)
    if not user.full_name or user.full_name == "微信用户":
        user.full_name = target_username
    _mark_login_success(db, user)
    return _auth_response(user, {"message": "PC 登录账号已设置", "requiresPcAccountSetup": False})


def request_password_reset(db: Session, data: PasswordResetRequest) -> dict:
    """
    request_password_reset 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    code = f"{secrets.randbelow(1_000_000):06d}"
    prefs = _preferences(user)
    prefs["passwordReset"] = {
        "codeHash": get_password_hash(code),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(seconds=PASSWORD_RESET_TTL_SECONDS)).isoformat(),
        "contact": data.contact or "",
        "verified": False,
        "requestedAt": datetime.now(timezone.utc).isoformat(),
    }
    _save_preferences(user, prefs)
    db.commit()
    return {
        "success": True,
        "message": "验证码已生成，请联系管理员获取或查看已接入的通知渠道。",
        "debugCode": code,
        "expiresIn": PASSWORD_RESET_TTL_SECONDS,
    }


def _load_valid_password_reset(user: User, code: str) -> dict:
    prefs = _preferences(user)
    reset = prefs.get("passwordReset") if isinstance(prefs.get("passwordReset"), dict) else {}
    if not reset.get("codeHash"):
        raise HTTPException(status_code=400, detail="请先获取验证码")
    expires_at_raw = reset.get("expiresAt") or ""
    try:
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="验证码已失效") from None
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="验证码已过期")
    if not verify_password(code, reset["codeHash"]):
        raise HTTPException(status_code=400, detail="验证码错误")
    return reset


def verify_password_reset(db: Session, data: PasswordResetVerifyRequest) -> dict:
    """
    verify_password_reset 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    reset = _load_valid_password_reset(user, data.code)
    prefs = _preferences(user)
    reset["verified"] = True
    reset["verifiedAt"] = datetime.now(timezone.utc).isoformat()
    prefs["passwordReset"] = reset
    _save_preferences(user, prefs)
    db.commit()
    return {"success": True, "message": "验证码验证通过"}


def confirm_password_reset(db: Session, data: PasswordResetConfirmRequest) -> dict:
    """
    confirm_password_reset 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    认证服务连接账号、微信身份和审核运营体验，集中处理是为了避免多端登录规则分叉。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    _load_valid_password_reset(user, data.code)
    user.hashed_password = get_password_hash(data.newPassword)
    prefs = _preferences(user)
    prefs.pop("passwordReset", None)
    _save_preferences(user, prefs)
    db.commit()
    return {"success": True, "message": "密码已重置"}
