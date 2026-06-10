"""
用户资料路由，提供个人资料、密码、省份偏好、练习偏好、协议同意和设备风险相关接口。

这些接口会影响首页默认筛选、定向备面默认值、活跃用户统计和账号安全提示。路由层不直接拼权益、
历史或支付数据，只把用户态请求交给 `user_service.py`，让用户表周边信息保持一个出口。

@param: FastAPI 注入当前用户、数据库 Session、请求体和可选设备头。
@return: 返回用户资料、更新结果、可选省份、协议状态或设备风险结果。
@raises HTTPException: 未登录、用户不存在、密码错误、参数不合法或设备风险异常时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    UserPasswordUpdate,
    UserPreferencesUpdate,
    UserProfileUpdate,
    UserTermsAgreementRequest,
)
from app.services.user_service import (
    change_password,
    check_device_risk,
    get_provinces,
    get_terms_status,
    get_user_info,
    record_terms_agreement,
    update_preferences,
    update_user_profile,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/info")
def user_info(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取当前用户资料和权限快照。

    个人中心、路由守卫和管理员入口都依赖这个接口；真正权限由后端生成，前端只负责展示。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 用户资料、偏好、管理员标记和权益摘要。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return get_user_info(db, current_user)



@router.put("/profile")
def update_profile(data: UserProfileUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    更新当前用户基础资料。

    这里只允许用户改自己的展示资料，不处理权益、订单或管理员标记，避免个人设置页越界。

    @param data: 资料更新请求。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 更新后的用户资料。
    @raises HTTPException: 未登录、用户不存在或字段非法时抛出。
    """
    return update_user_profile(db, current_user, data)


@router.put("/password")
def update_password(data: UserPasswordUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    当前用户修改密码。

    改密必须校验旧密码，并通过安全模块生成新哈希；路由层不接触哈希细节。

    @param data: 旧密码和新密码。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 修改成功提示。
    @raises HTTPException: 未登录、旧密码错误或用户不存在时抛出。
    """
    return change_password(db, current_user, data)


@router.put("/preferences")
def update_prefs(data: UserPreferencesUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    更新用户偏好设置。

    偏好可以保存省份、首页弹窗和端侧设置，但权益快照会由订阅服务同步，避免前端通过 preferences 伪造余额。

    @param data: 偏好更新请求。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 更新后的偏好和用户资料。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return update_preferences(db, current_user, data.model_dump(exclude_none=True))


@router.get("/provinces")
def provinces():
    """
    返回可选省份列表。

    省份用于用户偏好和筛选入口，不代表题库真实考试体系；题库分类仍以 examCategory/examSubcategory 为准。

    @param: 无。
    @return: 省份列表和默认值。
    @raises: 不主动抛业务异常。
    """
    return get_provinces()



@router.get("/terms-status")
def terms_status(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取当前用户协议同意状态。

    协议版本需要后端记录，避免端侧清缓存后无法证明用户是否已同意当前版本。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 当前协议版本、用户已同意版本和是否需要重新同意。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return get_terms_status(db, current_user.username)


@router.post("/agree-terms")
def agree_terms(data: UserTermsAgreementRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    记录当前用户同意协议。

    同意时间和版本写在用户表，用于后续审核、争议和版本升级判断。

    @param data: 协议版本。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 更新后的协议同意状态。
    @raises HTTPException: 未登录、用户不存在或版本非法时抛出。
    """
    return record_terms_agreement(db, current_user.username, data.version)


@router.get("/device-risk")
def device_risk(
    x_device_id: str = Header(default="", alias="X-Device-ID"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    设备风险提示路由。

    当前只返回轻量风险提示，不做强风控拦截；后续如果接入设备指纹，应保持这里是服务端可信判断。

    @param data: 设备和客户端环境信息。
    @param current_user: Bearer token 解析出的当前用户。
    @return: 风险等级和提示信息。
    @raises HTTPException: 未登录或参数异常时抛出。
    """
    return check_device_risk(db, current_user.username, x_device_id)
