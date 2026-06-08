"""
这个文件处理密码哈希、JWT 和当前用户解析；登录入口再多，也应该共用这一套可信身份边界。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    verify_password 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    安全模块是认证和密码哈希的共同边界，集中封装能减少登录入口扩散后的安全差异。

    @param plain: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param hashed: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
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
    get_password_hash 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    安全模块是认证和密码哈希的共同边界，集中封装能减少登录入口扩散后的安全差异。

    @param password: 用户提交的凭据明文；只在校验/哈希边界短暂使用，避免持久化原文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    create_access_token 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    安全模块是认证和密码哈希的共同边界，集中封装能减少登录入口扩散后的安全差异。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param expires_delta: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
    get_current_user 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    安全模块是认证和密码哈希的共同边界，集中封装能减少登录入口扩散后的安全差异。

    @param token: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException, exc: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
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
