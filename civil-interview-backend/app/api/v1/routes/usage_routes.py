"""
用量路由，接收前端上报的练习/考试用时，并交给服务层完成分钟折算和权益扣减。

端侧时间只是一项输入，不能直接决定最终扣量；服务端会校验考试归属、权益状态和每日限额。
这里不处理管理员人工扣减，也不写支付订单，避免用量记录和售后调整混在一起。

@param: FastAPI 注入用量上报请求、当前用户和数据库 Session。
@return: 返回扣量后的权益状态和用量记录摘要。
@raises HTTPException: 未登录、考试不属于当前用户、权益不足或上报参数不合法时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, UsageReportRequest
from app.services.usage_service import report_usage

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/report")
def usage_report(data: UsageReportRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    上报答题消耗时长的路由。

    端侧只负责报告作答秒数，真正扣减分钟、每日限额和 usage_records 写入都在 usage_service，防止前端自行修改余额。

    @param data: 用量上报请求。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 扣减后的权益状态和用量记录。
    @raises HTTPException: 未登录、考试不属于当前用户或额度不足时抛出。
    """
    return report_usage(db, current_user, data)
