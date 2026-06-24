"""
账号服务层，统一处理 PC 登录注册、微信小程序登录/绑定、账号补全、密码重置和 token 响应组装。

PC 和小程序共享同一个用户表，但授权来源不同：PC 主要走用户名密码，小程序走 code2session/openId，审核要求用户先浏览后主动登录。
因此登录入口不能散落在页面或路由里各自实现，否则会出现 token 结构、管理员标识、注册时间和设备记录不一致。
这里只负责身份和账号资料，不负责权益发放；试用、套餐和人工补偿必须走订阅/支付/后台权益服务。

@param: 服务函数接收数据库 Session、登录表单、微信 code 或密码重置请求。
@return: 返回统一认证响应、账号资料或密码重置状态，供路由直接序列化。
@raises HTTPException: 用户不存在、密码错误、微信 code 无效、用户名冲突或重置码失效时抛出明确 HTTP 错误。
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
    WechatMiniProgramInviteBindRequest,
    WechatMiniProgramLoginRequest,
)
from app.services.invite_service import (
    INVITE_SESSION_TTL_SECONDS,
    bind_registration_invite,
    bind_wechat_account_setup_invite,
    bind_wechat_first_session_invite,
    create_first_session_token,
    record_user_daily_activity,
    resolve_active_invite_code,
    user_has_invite_attribution,
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
    record_user_daily_activity(db, user, now)
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
    使用账号密码登录并返回端侧通用认证结果。

    账号登录和微信登录最终都返回 _auth_response，这样 PC、小程序和管理员入口能拿到同样的 token、
    管理员标记、权益快照和账号绑定状态。密码错误统一走 401，不泄露用户是否存在。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @param password: 用户提交的凭据明文；只在校验/哈希边界短暂使用，避免持久化原文。
    @return: 登录响应，包含 access_token、user、permissions、billing 和微信账号补全提示。
    @raises HTTPException: 用户不存在或密码不匹配时抛出 401。
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
    创建普通账号。

    注册时只写必要账号资料和协议版本，不自动授予试用或付费权益；权益发放由 trial/subscription 链路处理，
    避免账号创建和支付/试用状态纠缠在一起。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 注册请求，包含用户名、密码、可选姓名/邮箱和协议版本。
    @return: 创建成功提示；注册后仍需要走登录接口获取 token。
    @raises HTTPException: 用户名已存在时抛出 400，数据库写入失败时抛出 500。
    """
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    resolve_active_invite_code(db, data.inviteCode)
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
        db.flush()
        bind_registration_invite(db, user, data.inviteCode, "register")
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
    使用小程序 code 登录或自动创建微信临时账号。

    微信 openId 是小程序支付和订单核验的重要身份字段；这里会把 openId 写入 preferences，而不是单独建
    微信用户表，是为了兼容现有以 username 串联的历史记录、权益和订单。新微信用户会生成 `wx_` 前缀账号，
    后续可通过 setup_wechat_miniprogram_account 设置 PC 可登录账号。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 小程序登录请求，包含 wx.login 返回的 code 和可选协议版本。
    @return: 登录响应，并附带 created、requiresPcAccountSetup 和微信绑定状态。
    @raises HTTPException: 微信 code2session 失败或返回 openId 异常时抛出 502。
    """
    session_info = _code_to_session(data.code)
    openid = session_info["openid"]
    resolve_active_invite_code(db, data.inviteCode)
    user = _find_user_by_wechat_openid(db, openid)
    created = False
    invite_session_token = ""
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
            bind_registration_invite(db, user, data.inviteCode, "wechat_first_login")
            if not user_has_invite_attribution(user):
                invite_session_token = create_first_session_token(user)
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
        "inviteSessionToken": invite_session_token,
        "inviteSessionExpiresIn": INVITE_SESSION_TTL_SECONDS if invite_session_token else 0,
    })


def bind_wechat_miniprogram(db: Session, current_user, data: WechatMiniProgramBindRequest) -> dict:
    """
    把当前已登录账号绑定到小程序 openId。

    绑定前会检查 openId 是否已被其他账号占用，避免一个微信身份对应多份权益或订单。绑定信息写入
    preferences，是为了延续当前用户表结构，同时满足虚拟支付核单需要 openId 的约束。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 小程序绑定请求，包含 wx.login 返回的 code。
    @return: 绑定成功提示和 wechatMiniBound=true。
    @raises HTTPException: 当前账号不存在时抛出 404，openId 已绑定其他账号时抛出 409。
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
    给微信自动账号补全 PC 可登录的用户名和密码。

    小程序审核要求先浏览后登录，微信临时账号能让用户快速进入；但 PC 端仍需要明确用户名密码。这里通过
    改名而不是新建账号，保留原微信账号下已经产生的试用、订单、历史记录和 openId 绑定。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: PC 账号补全请求，包含目标用户名和新密码。
    @return: 新的登录响应，包含 requiresPcAccountSetup=false。
    @raises HTTPException: 用户不存在、用户名长度不合法或用户名已被占用时抛出对应错误。
    """
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.inviteCode:
        resolve_active_invite_code(db, data.inviteCode)
    if not user.username.startswith(WECHAT_ACCOUNT_PREFIX):
        if data.inviteCode:
            bind_wechat_account_setup_invite(db, user, data.inviteCode, data.inviteSessionToken)
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
    if data.inviteCode:
        bind_wechat_account_setup_invite(db, user, data.inviteCode, data.inviteSessionToken)
    _mark_login_success(db, user)
    return _auth_response(user, {"message": "PC 登录账号已设置", "requiresPcAccountSetup": False})


def bind_wechat_miniprogram_invite(db: Session, current_user, data: WechatMiniProgramInviteBindRequest) -> dict:
    """
    微信首登首次会话内独立绑定邀请码。

    用户跳过 PC 账号补全但已经输入邀请码时，前端可调用本接口在 15 分钟内完成来源归因。

    @param db: 调用方传入的数据库会话。
    @param current_user: 当前已登录的微信临时账号。
    @param data: 邀请码和首次会话凭证。
    @return: 绑定结果。
    @raises HTTPException: 用户不存在、邀请码无效或会话凭证失效时抛出。
    """
    return bind_wechat_first_session_invite(db, current_user, data)


def request_password_reset(db: Session, data: PasswordResetRequest) -> dict:
    """
    生成密码重置验证码并暂存在用户 preferences。

    目前没有真正接入短信/邮件通道，所以返回 debugCode 作为管理员协助找回密码的临时妥协；验证码仍按
    哈希保存并设置过期时间，避免明文长期留在数据库里。接入通知渠道后应移除对外 debugCode。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 密码重置申请，包含用户名和可选联系信息。
    @return: 生成结果、有效期和当前临时 debugCode。
    @raises HTTPException: 用户不存在时抛出 404。
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
    校验密码重置验证码并标记已验证。

    分成“验证”和“确认重置”两步，是为了让前端能先给用户明确反馈；真正改密仍在 confirm_password_reset，
    避免验证码通过后还没提交新密码时就改变登录凭据。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 验证请求，包含用户名和验证码。
    @return: 验证通过提示。
    @raises HTTPException: 用户不存在、未申请验证码、验证码过期或验证码错误时抛出。
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
    使用有效验证码完成密码重置。

    修改密码后会删除 passwordReset 临时状态，避免同一个验证码重复使用。这里不自动登录用户，是为了让
    端侧重新走登录链路，拿到新的 token 和最新权限快照。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 重置确认请求，包含用户名、验证码和新密码。
    @return: 密码已重置提示。
    @raises HTTPException: 用户不存在、验证码失效或验证码错误时抛出。
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
