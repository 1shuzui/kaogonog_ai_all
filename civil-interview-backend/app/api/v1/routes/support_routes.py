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
    return create_support_feedback(db, current_user, data)


@router.post("/feedback/attachments")
async def support_feedback_upload_attachment(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
):
    return await save_support_feedback_attachment(file)


@router.patch("/feedback/{feedback_id}")
def support_feedback_update(
    feedback_id: int,
    data: SupportFeedbackUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_support_feedback(db, current_user, feedback_id, data)


@router.delete("/feedback/{feedback_id}")
def support_feedback_delete(
    feedback_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_support_feedback(db, current_user, feedback_id)
