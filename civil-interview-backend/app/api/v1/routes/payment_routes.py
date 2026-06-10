"""
支付路由，暴露套餐订单、微信小程序虚拟支付确认、订单查询、退款申请和管理员退款管理接口。

所有付费训练权益都必须通过微信官方小程序虚拟支付确认，不在路由层提供普通支付兜底。支付接口只处理真实购买和退款；
人工补发、测试账号赠送、客服扣减走订阅管理员接口，避免审核和财务口径混在一张订单表里。

@param: FastAPI 注入支付请求、退款请求、当前用户和数据库 Session。
@return: 返回套餐列表、订单信息、虚拟支付参数、支付确认结果、退款统计或退款处理结果。
@raises HTTPException: 未登录、非管理员、套餐不存在、订单状态不合法、微信支付查询失败或退款越界时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    PaymentOrderCreateRequest,
    PaymentVirtualConfirmRequest,
    RefundApplyRequest,
    RefundBalanceStatsRequest,
)
from app.services.payment_service import (
    apply_refund,
    confirm_virtual_payment_order,
    create_payment_order,
    get_payment_order,
    get_refund_balance_stats,
    list_payment_orders,
    verify_virtual_payment_order,
)

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/orders")
def payment_create_order(data: PaymentOrderCreateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    创建支付订单的 HTTP 路由。

    所有付费虚拟训练权益都应从这里进入微信小程序虚拟支付链路，路由层只做鉴权和请求转发。

    @param data: 下单请求体。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 本地订单和虚拟支付拉起参数。
    @raises HTTPException: 未登录、套餐无效或支付配置异常时抛出。
    """
    return create_payment_order(db, current_user, data)


@router.get("/orders/me")
def payment_list_orders(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    当前用户订单中心列表路由。

    普通用户只能看自己的订单，管理员退款核查走独立后台接口。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 用户订单列表。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return list_payment_orders(db, current_user)


@router.get("/orders/{order_no}")
def payment_get_order(order_no: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取当前用户单个订单的路由。

    该接口只用于订单详情展示，不重新生成支付签名，避免刷新详情页造成支付参数混乱。

    @param orderNo: 本地订单号。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 订单详情和只读查询提示。
    @raises HTTPException: 订单不存在或无权访问时抛出。
    """
    return get_payment_order(db, current_user, order_no)


@router.post("/orders/{order_no}/virtual/verify")
def payment_verify_virtual_order(order_no: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户主动补核微信虚拟支付订单的路由。

    当小程序支付完成但本地状态未及时刷新时，端侧可以调用这里让服务端向微信查单。

    @param orderNo: 本地订单号。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 核验后的订单和微信查询结果。
    @raises HTTPException: 订单不存在、缺少 openId 或微信查单失败时抛出。
    """
    return verify_virtual_payment_order(db, current_user, order_no)


@router.post("/admin/refund-stats")
def payment_refund_stats(data: RefundBalanceStatsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    管理员退款余额统计路由。

    该接口给退款后台做决策辅助，不代表已经发起退款；真正退款必须调用 apply_refund。

    @param data: 查询条件。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 可退款订单和汇总数据。
    @raises HTTPException: 非管理员访问时抛出 403。
    """
    return get_refund_balance_stats(db, current_user, data)


@router.post("/admin/refund")
def payment_apply_refund(data: RefundApplyRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    管理员发起微信虚拟支付退款的路由。

    退款动作会影响订单和权益状态，必须经过管理员鉴权，并由服务层完成微信查单、退款和本地审计写入。

    @param data: 退款申请。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 退款提交结果。
    @raises HTTPException: 非管理员、订单不可退或微信退款失败时抛出。
    """
    return apply_refund(db, current_user, data)


@router.post("/orders/{order_no}/virtual/confirm")
def payment_virtual_confirm(order_no: str, data: PaymentVirtualConfirmRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    小程序支付成功后的确认路由。

    该路由用于把微信虚拟支付结果同步为本地 paid 订单和用户权益；普通支付或失败支付不能走这里。

    @param orderNo: 本地订单号。
    @param data: 小程序支付结果。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 支付确认结果和最新权益。
    @raises HTTPException: 场景不匹配、支付未成功或订单核验失败时抛出。
    """
    return confirm_virtual_payment_order(db, current_user, order_no, data)
