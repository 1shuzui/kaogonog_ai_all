"""
试用路由，提供试用状态、试用题领取和试用完成标记。

小程序首页可以未登录浏览，但试用接口必须登录，因为试用次数和完成状态要绑定用户账号。
这里不直接生成正式套餐，也不绕过用量上报；试用权益仍走订阅服务的同一套可用性判断。

@param: FastAPI 注入当前用户和数据库 Session。
@return: 返回试用资格、试用题或试用完成状态。
@raises HTTPException: 未登录、试用已用完、用户不存在或没有可用试用题时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.trial_service import complete_trial, get_trial_question, get_trial_status

router = APIRouter(prefix="/trial", tags=["trial"])


@router.get("/status")
def trial_status(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取当前用户试用状态。

    试用也依赖账号记录完成状态，所以未登录用户只能浏览功能，不能直接消耗试用题。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 是否可试用、是否已完成和试用题信息摘要。
    @raises HTTPException: 未登录或用户不存在时抛出。
    """
    return get_trial_status(db, current_user)


@router.get("/question")
def trial_question(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    领取试用题的路由。

    试用题必须和用户绑定，避免同一设备或清缓存重复领取；题目选择逻辑在 trial_service。

    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 试用题详情和试用状态。
    @raises HTTPException: 未登录、已完成试用或题目不可用时抛出。
    """
    return get_trial_question(db, current_user)


@router.post("/complete")
def trial_complete(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    标记试用完成的路由。

    完成状态写入用户权益/偏好，后续套餐中心和首页都以此判断是否还能试用。

    @param data: 试用完成请求。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 完成后的试用状态。
    @raises HTTPException: 未登录或试用记录不存在时抛出。
    """
    return complete_trial(db, current_user)
