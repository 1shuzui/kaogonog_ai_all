"""
客服反馈路由，承接用户提交题目纠错、支付问题、体验建议、附件上传和管理员处理反馈状态。

反馈链路是用户与管理员之间的轻量工单系统：普通用户只能提交和查看自己的反馈，管理员可以筛选、备注、更新状态和删除。
这里不直接修题库、不直接退款、不直接改权益；它只留下可追溯线索，再由题库、支付或权益后台完成实际处理。

@param: FastAPI 注入反馈请求、附件文件、筛选参数、当前用户和数据库 Session。
@return: 返回反馈列表、创建结果、附件信息、状态更新结果或删除结果。
@raises HTTPException: 未登录、非管理员、反馈不存在、附件不合法或用户无权访问时返回 HTTP 错误。
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
    查询反馈列表。

    普通用户默认只看自己的反馈，管理员才能通过 `scope` 和筛选条件查看全量工单。
    这条边界放在服务层执行，路由层保留兼容参数，避免 PC 管理台和小程序反馈页分页口径不同。

    @param current: 当前页码。
    @param page: 兼容旧前端的页码别名，优先级高于 current。
    @param pageSize: 每页条数。
    @param feedback_type: 反馈类型筛选。
    @param status: 处理状态筛选。
    @param province: 地区筛选，只作为反馈上下文。
    @param keyword: 标题、正文或用户名搜索词。
    @param scope: `mine` 或管理员全量范围。
    @param current_user: 鉴权层解析出的用户身份。
    @param db: 当前请求复用的数据库会话。
    @return: 分页反馈列表。
    @raises HTTPException: 未登录、越权查看或查询失败时抛出。
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
    创建用户反馈。

    反馈只记录问题线索，不在提交时直接改题库、退款或调权益；这样可以让管理员先核对证据，
    再通过对应后台入口做可审计处理。

    @param data: 反馈标题、类型、正文和关联上下文。
    @param current_user: 鉴权层解析出的用户身份。
    @param db: 当前请求复用的数据库会话。
    @return: 新建反馈详情。
    @raises HTTPException: 未登录、内容不合法或保存失败时抛出。
    """
    return create_support_feedback(db, current_user, data)


@router.post("/feedback/attachments")
async def support_feedback_upload_attachment(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    上传反馈附件并返回可挂到反馈正文的文件信息。

    附件保存与反馈创建分离，是为了兼容小程序先传图、再提交表单的交互；服务层仍会限制大小和文件类型。

    @param file: 用户上传的截图或佐证附件。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 附件访问路径、文件名和元信息。
    @raises HTTPException: 未登录、附件类型不支持或保存失败时抛出。
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
    更新反馈处理状态或管理员备注。

    反馈状态是客服工作台的轻量工单流转，不代表关联问题已经自动修复；实际退款、权益调整和题库修正
    仍要在对应模块留下独立审计记录。

    @param feedback_id: 反馈记录 ID。
    @param data: 状态、备注或处理结果更新请求。
    @param current_user: 鉴权层解析出的用户身份。
    @param db: 当前请求复用的数据库会话。
    @return: 更新后的反馈详情。
    @raises HTTPException: 反馈不存在、无权处理或状态不合法时抛出。
    """
    return update_support_feedback(db, current_user, feedback_id, data)


@router.delete("/feedback/{feedback_id}")
def support_feedback_delete(
    feedback_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除反馈记录。

    删除入口只面向管理员清理误提交或测试数据；真实售后处理不应依赖删除反馈来“撤销”，
    需要在退款或权益流水里另留记录。

    @param feedback_id: 反馈记录 ID。
    @param current_user: 鉴权层解析出的用户身份。
    @param db: 当前请求复用的数据库会话。
    @return: 删除结果。
    @raises HTTPException: 非管理员、反馈不存在或删除失败时抛出。
    """
    return delete_support_feedback(db, current_user, feedback_id)
