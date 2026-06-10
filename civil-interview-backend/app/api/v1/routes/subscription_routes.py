"""
权益路由，提供用户套餐余额、访问校验、权益切换，以及管理员人工补发/扣减/流水查询接口。

普通用户接口只返回“我还能不能用、剩余多少、当前消耗哪份权益”；后台接口必须经过管理员鉴权，
并把每次人工调整写入审计流水。这里刻意把人工权益管理挂在 subscription 下，是因为它影响可用时长，
但它不能创建支付订单，也不能伪造历史用量。

@param: FastAPI 注入查询参数、补发/扣减请求、当前用户和数据库 Session。
@return: 返回用户权益状态、访问校验结果、切换结果、管理员用户权益详情或调整流水。
@raises HTTPException: 未登录、非管理员、权益不存在、余额不足、参数越界或原因类型无效时返回 HTTP 错误。
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
    读取当前用户权益状态的路由。

    所有端侧余额展示都应走这个接口，避免 PC、小程序和管理员调整后看到不同的剩余时长。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 当前权益快照和全部权益列表。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return get_subscription_status(db, current_user)


@router.get("/check-access")
def subscription_check_access(mode: str = "practice", current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    检查当前用户是否能进入某类训练的路由。

    前端可用于提前提示，但不能替代服务端扣量校验；真正消耗权益仍在 usage_report。

    @param mode: 训练场景标识，用于响应回显。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: allowed、reason 和权益快照。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return check_subscription_access(db, current_user, mode)


@router.post("/switch")
def subscription_switch(data: SubscriptionSwitchRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    切换当前消耗权益的路由。

    用户可能有多条可用权益，切换行为必须在后端确认归属和可用性，避免端侧传入他人权益 ID。

    @param payload: 包含 subscriptionId 的请求体。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 切换后的权益快照。
    @raises HTTPException: 权益不存在或不可用时抛出。
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
    管理员用户搜索路由。

    权益管理只允许按条件分页查询，避免后台页面一次性拉全量用户表。

    @param username: 用户名模糊筛选。
    @param page: 页码。
    @param pageSize: 每页数量。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 用户分页列表。
    @raises HTTPException: 非管理员访问时抛出 403。
    """
    return list_admin_users(db, current_user, username=username, page=page, page_size=pageSize)


@router.get("/admin/users/{username}/entitlements")
def subscription_admin_user_entitlements(
    username: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员查看单个用户权益详情的路由。

    页面需要同时核对用户资料、订单摘要、权益列表和最近调整记录，所以由服务层统一拼装，避免前端多接口竞态。

    @param username: 被查看用户的用户名。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 用户权益详情。
    @raises HTTPException: 非管理员或用户不存在时抛出。
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
    管理员人工补发权益的路由。

    人工权益不创建支付订单，必须走独立审计流水，避免和微信虚拟支付到账记录混在一起。

    @param username: 被补发用户。
    @param body: 补发分钟数、每日限额、有效期、原因和备注。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 补发后的用户权益详情和调整流水。
    @raises HTTPException: 非管理员、参数越界或用户不存在时抛出。
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
    管理员扣减指定权益的路由。

    后台扣减通过增加 used_minutes 完成，不改历史 usage_records；这样用户真实答题记录和客服调整记录保持两套审计口径。

    @param username: 被扣减用户。
    @param body: subscriptionId、扣减分钟数、原因和备注。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 扣减后的用户权益详情和调整流水。
    @raises HTTPException: 非管理员、权益不存在或扣减超过剩余时长时抛出。
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
    管理员权益调整流水查询路由。

    撤错通过新增反向调整完成，所以流水查询是追责和客服复盘的主要入口，不能给普通用户开放。

    @param username: 目标用户筛选。
    @param actionType: 调整类型筛选。
    @param operator: 操作者筛选。
    @param startAt: 开始时间。
    @param endAt: 结束时间。
    @param page: 页码。
    @param pageSize: 每页数量。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 调整流水分页列表。
    @raises HTTPException: 非管理员访问时抛出 403。
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
