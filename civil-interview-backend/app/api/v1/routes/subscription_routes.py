"""
这个路由文件提供权益状态、套餐切换和访问校验接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, EntitlementDeductRequest, EntitlementGrantRequest, SubscriptionSwitchRequest
from app.services.entitlement_admin_service import (
    deduct_user_entitlement,
    get_admin_user_entitlements,
    grant_user_entitlement,
    list_admin_users,
    list_entitlement_adjustments,
)
from app.services.subscription_service import check_subscription_access, get_subscription_status, switch_subscription

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/me")
def subscription_me(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    subscription_me 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_subscription_status(db, current_user)


@router.get("/check-access")
def subscription_check_access(mode: str = "practice", current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    subscription_check_access 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param mode: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return check_subscription_access(db, current_user, mode)


@router.post("/switch")
def subscription_switch(data: SubscriptionSwitchRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    subscription_switch 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return switch_subscription(db, current_user, data.subscriptionId)


@router.get("/admin/users")
def subscription_admin_users(
    username: str = "",
    page: int = 1,
    pageSize: int = 20,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    subscription_admin_users 为管理员权益页提供用户搜索入口，避免前端直接拉取全量用户表。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param username: 搜索关键字；主口径是用户名，兼容昵称和邮箱模糊搜索。
    @param page: 页码，从 1 开始。
    @param pageSize: 每页条数，服务层会限制最大值。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return list_admin_users(db, current_user, username=username, page=page, page_size=pageSize)


@router.get("/admin/users/{username}/entitlements")
def subscription_admin_user_entitlements(
    username: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    subscription_admin_user_entitlements 返回管理员核查单个用户时需要的权益、订单摘要和最近调整记录。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param username: 目标用户账号。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_admin_user_entitlements(db, current_user, username)


@router.post("/admin/users/{username}/grant")
def subscription_admin_grant_entitlement(
    username: str,
    data: EntitlementGrantRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    subscription_admin_grant_entitlement 创建人工补发权益，和微信支付订单保持分离。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param username: 目标用户账号。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return grant_user_entitlement(db, current_user, username, data)


@router.post("/admin/users/{username}/deduct")
def subscription_admin_deduct_entitlement(
    username: str,
    data: EntitlementDeductRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    subscription_admin_deduct_entitlement 扣减指定权益的剩余时长，不改历史用量流水。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param username: 目标用户账号。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return deduct_user_entitlement(db, current_user, username, data)


@router.get("/admin/adjustments")
def subscription_admin_adjustments(
    username: str = "",
    actionType: str = "",
    operator: str = "",
    startAt: str = "",
    endAt: str = "",
    page: int = 1,
    pageSize: int = 20,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    subscription_admin_adjustments 提供全局人工权益调整流水查询。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param username: 目标用户筛选。
    @param actionType: 调整类型筛选。
    @param operator: 操作者筛选。
    @param startAt: 开始时间筛选。
    @param endAt: 结束时间筛选。
    @param page: 页码，从 1 开始。
    @param pageSize: 每页条数，服务层会限制最大值。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return list_entitlement_adjustments(
        db,
        current_user,
        username=username,
        action_type=actionType,
        operator=operator,
        start_at=startAt,
        end_at=endAt,
        page=page,
        page_size=pageSize,
    )
