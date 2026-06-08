"""
这个路由文件提供用户反馈和管理员处理接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest
from app.services.support_service import (
    create_support_feedback,
    delete_support_feedback,
    list_support_feedback,
    save_support_feedback_attachment,
    update_support_feedback,
)

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/feedback")
def support_feedback_list(
    current: int = 1,
    page: int | None = None,
    pageSize: int = 10,
    feedback_type: str = Query("", alias="type"),
    status: str = "",
    province: str = "",
    keyword: str = "",
    scope: str = "mine",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    support_feedback_list 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param current: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param page: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param pageSize: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param feedback_type: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param status: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @param keyword: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param scope: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return list_support_feedback(
        db,
        current_user,
        current=page or current,
        page_size=pageSize,
        feedback_type=feedback_type,
        status=status,
        province=province,
        keyword=keyword,
        scope=scope,
    )


@router.post("/feedback")
def support_feedback_create(
    data: SupportFeedbackCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    support_feedback_create 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return create_support_feedback(db, current_user, data)


@router.post("/feedback/attachments")
async def support_feedback_upload_attachment(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    support_feedback_upload_attachment 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param file: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return await save_support_feedback_attachment(file)


@router.patch("/feedback/{feedback_id}")
def support_feedback_update(
    feedback_id: int,
    data: SupportFeedbackUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    support_feedback_update 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param feedback_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return update_support_feedback(db, current_user, feedback_id, data)


@router.delete("/feedback/{feedback_id}")
def support_feedback_delete(
    feedback_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    support_feedback_delete 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param feedback_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return delete_support_feedback(db, current_user, feedback_id)
