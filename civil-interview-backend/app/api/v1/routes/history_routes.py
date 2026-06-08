"""
这个路由文件提供历史记录、成绩趋势和复盘详情接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    history_list 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @param current: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param pageSize: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param startDate: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param endDate: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
    history_trend 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param days: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_history_trend(db, current_user.username, days=days)


@router.get("/stats")
def history_stats(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    history_stats 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_history_stats(db, current_user.username)


@router.get("/{exam_id}")
def history_detail(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    history_detail 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_history_detail(db, exam_id)
