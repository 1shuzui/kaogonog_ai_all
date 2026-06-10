"""
后端身份安全边界模块。

这里集中处理密码哈希与校验、JWT 令牌签发、FastAPI 当前用户解析。登录、改密、找回密码和管理员接口都依赖同一套身份判断，不能在路由层各写一份，否则 bcrypt/passlib 兼容策略、token 过期语义和管理员权限口径会分裂。当前还会节流更新 last_active_at，用于活跃用户统计；这个写入失败时只回滚本次触达，不阻断登录后的业务。

@param: 模块本身无入参；业务输入来自登录表单、Bearer token、数据库会话和调用方传入的密码字段。
@return: 导出密码工具函数、JWT 工具函数和 get_current_user 依赖，供路由层复用同一身份快照。
@raises ImportError: 缺少加密、JWT、数据库或配置依赖时会在导入阶段失败。
@raises HTTPException: token 无效、用户不存在或凭据过期时由 get_current_user 抛出 401。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.access import build_access_context
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import AuthUser, TokenData

# Prefer PBKDF2 for new hashes so registration/password change stays stable even
# when the runtime bcrypt binding and passlib version are mismatched.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ACTIVE_TOUCH_INTERVAL = timedelta(minutes=10)


def verify_password(plain: str, hashed: str) -> bool:
    """
    校验用户提交的明文密码是否匹配数据库里的哈希。

    旧账号可能仍是 bcrypt，新注册和改密优先使用 PBKDF2；这里同时兼容两种格式，是为了避免运行时
    bcrypt 绑定和 passlib 版本不一致时影响登录。异常统一返回 False，调用方不应该从错误类型推断账号状态。

    @param plain: 用户提交的明文密码；只在本函数内短暂使用。
    @param hashed: 数据库存储的密码哈希；支持 bcrypt 与 passlib 当前配置格式。
    @return: True 表示密码匹配，False 表示不匹配、缺失或哈希不可验证。
    @raises: 不主动向上抛校验异常；哈希格式错误会被吞掉并按失败处理。
    """
    if not plain or not hashed:
        return False
    if hashed.startswith(("$2a$", "$2b$", "$2x$", "$2y$")):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    为新密码生成持久化哈希。

    注册、改密、微信账号自动创建和密码重置都走这里，目的是让新写入的哈希算法保持一致；不要在
    业务服务里直接调用 bcrypt，否则后续升级哈希策略时会漏掉入口。

    @param password: 用户提交的凭据明文；只在校验/哈希边界短暂使用，避免持久化原文。
    @return: 可写入 users.hashed_password 的安全哈希字符串。
    @raises Exception: passlib 加密上下文异常会向上抛出，调用方应回滚本次用户写入。
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    根据登录用户信息签发 JWT 访问令牌。

    token 只承载最小身份声明和过期时间，权限、权益和管理员身份仍在 get_current_user 里查库生成，
    避免用户权限变化后旧 token 长时间携带过期权限快照。

    @param data: JWT payload 基础字段，通常至少包含 sub=username。
    @param expires_delta: 自定义过期时长；为空时使用全局 access_token_expire_minutes。
    @return: 可放入 Authorization Bearer 的 JWT 字符串。
    @raises Exception: secret、算法或 payload 不可编码时由 PyJWT 向上抛出。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def _mark_user_active_if_due(db: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    last_active = user.last_active_at
    if isinstance(last_active, datetime):
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        if now - last_active < ACTIVE_TOUCH_INTERVAL:
            return
    user.last_active_at = now
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    """
    FastAPI 依赖：从 Bearer token 解析当前用户并生成统一权限快照。

    这里故意每次查库，而不是完全相信 token，是为了让管理员标记、订阅权益、账号禁用和活跃时间统计
    能即时反映到各接口。last_active_at 采用十分钟节流写入，避免高频请求把 MySQL 写放大。

    @param token: Authorization Bearer 中的 JWT 令牌。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: AuthUser 快照，包含账号资料、角色、管理员标记、权限列表和权益摘要。
    @raises HTTPException: token 过期、签名无效、缺少 sub 或用户不存在时抛出 401。
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if not username:
            raise exc
    except (ExpiredSignatureError, InvalidTokenError):
        raise exc
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise exc
    _mark_user_active_if_due(db, user)
    access_context = build_access_context(user)
    return AuthUser(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        role=access_context["role"],
        isAdmin=access_context["isAdmin"],
        permissions=access_context["permissions"],
        billing=access_context["billing"],
    )
