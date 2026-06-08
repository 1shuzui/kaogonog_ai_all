"""
这个路由文件提供账号登录、注册、微信绑定和密码重置接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
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
    """
    login_for_access_token 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param form_data: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return login_user(db, form_data.username, form_data.password)


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    register 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return register_user(db, data)


@router.post("/auth/wechat/miniprogram")
def wechat_miniprogram_login(data: WechatMiniProgramLoginRequest, db: Session = Depends(get_db)):
    """
    wechat_miniprogram_login 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return login_wechat_miniprogram(db, data)


@router.post("/auth/wechat/miniprogram/bind")
def wechat_miniprogram_bind(
    data: WechatMiniProgramBindRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    wechat_miniprogram_bind 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return bind_wechat_miniprogram(db, current_user, data)


@router.post("/auth/wechat/miniprogram/account")
def wechat_miniprogram_account(
    data: WechatMiniProgramAccountRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    wechat_miniprogram_account 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return setup_wechat_miniprogram_account(db, current_user, data)


@router.get("/auth/wechat/web/url")
def wechat_web_login_url():
    """
    wechat_web_login_url 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return {"enabled": False, "url": "", "message": "PC 微信扫码登录暂未开通，请使用账号密码登录。"}


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    password_reset_request 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return request_password_reset(db, data)


@router.post("/password-reset/verify")
def password_reset_verify(data: PasswordResetVerifyRequest, db: Session = Depends(get_db)):
    """
    password_reset_verify 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return verify_password_reset(db, data)


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """
    password_reset_confirm 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return confirm_password_reset(db, data)
