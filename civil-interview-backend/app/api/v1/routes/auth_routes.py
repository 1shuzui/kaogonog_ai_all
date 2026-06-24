"""
账号认证路由，承接 PC 登录注册、小程序 code 登录/绑定、账号补全、网页登录地址和密码重置接口。

本文件只处理 HTTP 边界：解析表单或 JSON、注入当前用户和数据库会话、把请求转交给 `auth_service.py`。
登录体验的业务约束在这里也要保持清楚：小程序可以先浏览，只有用户主动触发试用、练习、支付或个人数据时才进入登录流程；
管理员身份来自 token 中解析出的后端可信用户，不由前端按钮显示与否决定。

@param: FastAPI 根据路由声明注入请求体、表单、当前用户和数据库 Session。
@return: 返回 token、账号资料、微信绑定结果或密码重置状态。
@raises HTTPException: 参数校验、鉴权失败或服务层业务错误会按 FastAPI 语义返回给前端。
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
    WechatMiniProgramInviteBindRequest,
    WechatMiniProgramLoginRequest,
)
from app.services.auth_service import (
    bind_wechat_miniprogram,
    bind_wechat_miniprogram_invite,
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
    账号密码登录路由。

    这个接口保持 OAuth2PasswordRequestForm，是为了兼容 FastAPI 标准登录表单和现有 PC 请求层；真正的密码校验、登录成功时间和权限快照由 auth_service 处理。

    @param form_data: OAuth2 表单，包含 username 和 password。
    @param db: 请求级数据库会话。
    @return: access_token、用户资料、管理员标记、权限和权益摘要。
    @raises HTTPException: 凭据错误时由服务层抛出 401。
    """
    return login_user(db, form_data.username, form_data.password)


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    普通账号注册路由。

    路由层只负责把 Pydantic 请求交给服务层，避免把用户名唯一性、协议版本和密码哈希规则写在 HTTP 适配层。

    @param data: 注册请求体。
    @param db: 请求级数据库会话。
    @return: 创建成功提示。
    @raises HTTPException: 用户名重复或数据库写入失败时由服务层抛出。
    """
    return register_user(db, data)


@router.post("/auth/wechat/miniprogram")
def wechat_miniprogram_login(data: WechatMiniProgramLoginRequest, db: Session = Depends(get_db)):
    """
    小程序微信登录路由。

    这是微信审核“用户主动登录”之后的入口；openId 获取、临时账号创建和 PC 账号补全提示都在服务层完成。

    @param data: 小程序登录请求，包含 wx.login code 和可选协议版本。
    @param db: 请求级数据库会话。
    @return: 登录响应及微信账号绑定/补全状态。
    @raises HTTPException: 微信 code2session 失败或数据库状态异常时由服务层抛出。
    """
    return login_wechat_miniprogram(db, data)


@router.post("/auth/wechat/miniprogram/bind")
def wechat_miniprogram_bind(
    data: WechatMiniProgramBindRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    已登录账号绑定小程序微信身份的路由。

    绑定动作必须要求当前用户已登录，避免匿名 openId 被错误写到其他账号；重复绑定冲突由服务层判断。

    @param data: 微信绑定请求，包含 wx.login code。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 绑定成功状态。
    @raises HTTPException: 未登录、用户不存在或 openId 已绑定其他账号时抛出。
    """
    return bind_wechat_miniprogram(db, current_user, data)


@router.post("/auth/wechat/miniprogram/account")
def wechat_miniprogram_account(
    data: WechatMiniProgramAccountRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    微信临时账号补全 PC 登录账号的路由。

    小程序可先生成 wx_ 临时账号，但 PC 端需要可记忆用户名和密码；本路由只做 HTTP 适配，改名保留历史数据的逻辑放在服务层。

    @param data: 用户名和新密码。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 更新后的登录响应。
    @raises HTTPException: 用户名不可用或当前账号不存在时抛出。
    """
    return setup_wechat_miniprogram_account(db, current_user, data)


@router.post("/auth/wechat/miniprogram/invite")
def wechat_miniprogram_invite_bind(
    data: WechatMiniProgramInviteBindRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    微信首登首次会话内的邀请码独立绑定路由。

    用户如果跳过 PC 账号补全，但在首次会话里仍输入了邀请码，可以通过这个接口把来源先保存下来。
    """
    return bind_wechat_miniprogram_invite(db, current_user, data)


@router.get("/auth/wechat/web/url")
def wechat_web_login_url():
    """
    返回 PC 微信登录占位状态。

    当前尚未接入 PC 微信扫码登录，所以明确返回 disabled，避免前端误展示不可用入口。

    @param: 无；该接口只读取当前服务能力配置。
    @return: enabled=false 和不可用说明。
    @raises: 不主动抛业务异常。
    """
    return {"enabled": False, "url": "", "message": "PC 微信扫码登录暂未开通，请使用账号密码登录。"}


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    申请密码重置验证码的路由。

    通知通道尚未完善，服务层会返回临时 debugCode 供管理员协助；路由层不记录验证码，避免日志和响应处理分叉。

    @param data: 密码重置申请。
    @param db: 请求级数据库会话。
    @return: 验证码申请结果和有效期。
    @raises HTTPException: 用户不存在时由服务层抛出。
    """
    return request_password_reset(db, data)


@router.post("/password-reset/verify")
def password_reset_verify(data: PasswordResetVerifyRequest, db: Session = Depends(get_db)):
    """
    验证密码重置验证码的路由。

    验证和最终改密分成两步，是为了让前端能先提示验证码是否有效，同时保持密码真正修改在 confirm 阶段完成。

    @param data: 用户名和验证码。
    @param db: 请求级数据库会话。
    @return: 验证通过提示。
    @raises HTTPException: 验证码缺失、过期或错误时由服务层抛出。
    """
    return verify_password_reset(db, data)


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """
    确认重置密码的路由。

    服务层会重新校验验证码并清除临时状态，路由层不自动登录用户，避免旧 token 与新密码状态混用。

    @param data: 用户名、验证码和新密码。
    @param db: 请求级数据库会话。
    @return: 密码已重置提示。
    @raises HTTPException: 用户不存在或验证码无效时由服务层抛出。
    """
    return confirm_password_reset(db, data)
