"""
历史记录路由，向 PC 和小程序提供成绩列表、趋势图数据、统计卡片和单场复盘详情。

路由层只做当前用户鉴权、分页/ID 参数接收和服务层转发；历史数据必须来自已完成考试的保存结果，
不能在这里重新评分或重新推导能力维度，否则结果页和历史页会出现分数不一致。

@param: FastAPI 注入当前用户、数据库 Session、分页参数或考试 ID。
@return: 返回历史列表、趋势数据、统计摘要或复盘详情。
@raises HTTPException: 未登录、记录不存在或用户无权查看时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.history_service import get_history_list, get_history_detail, get_history_stats, get_history_trend

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def history_list(
    province: str = "",
    current: int = 1,
    pageSize: int = 10,
    startDate: str = "",
    endDate: str = "",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    分页读取当前用户练习历史。

    历史列表是个人复盘入口，只返回当前用户记录；筛选条件在服务层归一化，避免端侧传入不一致日期格式。

    @param current: 页码。
    @param pageSize: 每页数量。
    @param province: 省份筛选。
    @param startDate: 开始日期。
    @param endDate: 结束日期。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 历史记录分页列表。
    @raises HTTPException: 未登录或筛选参数非法时抛出。
    """
    return get_history_list(
        db,
        current_user.username,
        current=current,
        page_size=pageSize,
        province=province,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/trend")
def history_trend(days: int = 30, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取成绩趋势数据。

    趋势图只基于当前用户历史记录计算，避免把全局样本误当成个人能力变化。

    @param days: 统计最近多少天。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 日期维度的练习次数和平均分趋势。
    @raises HTTPException: 未登录时抛出。
    """
    return get_history_trend(db, current_user.username, days=days)


@router.get("/stats")
def history_stats(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取当前用户历史统计摘要。

    首页和个人中心使用这个接口展示练习次数、平均分和薄弱项，不直接遍历历史列表，减少端侧重复计算。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 历史统计摘要。
    @raises HTTPException: 未登录时抛出。
    """
    return get_history_stats(db, current_user.username)


@router.get("/{exam_id}")
def history_detail(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取单条历史记录详情。

    详情回看可能包含题干、答案、评分和文字稿，必须在服务层确认记录归属，避免通过 ID 枚举他人记录。

    @param record_id: 历史记录 ID。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 历史记录详情。
    @raises HTTPException: 记录不存在或无权访问时抛出。
    """
    return get_history_detail(db, exam_id, current_user.username)
