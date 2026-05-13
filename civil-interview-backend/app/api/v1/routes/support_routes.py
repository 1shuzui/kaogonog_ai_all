from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest
from app.services.support_service import delete_feedback, list_feedback, submit_feedback, update_feedback

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/feedback")
def feedback_list(
    current: int = 1,
    pageSize: int = 20,
    type: str = "",
    status: str = "",
    province: str = "",
    keyword: str = "",
    scope: str = "mine",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_feedback(
        db,
        current_user,
        current=current,
        page_size=pageSize,
        feedback_type=type,
        status=status,
        province=province,
        keyword=keyword,
        scope=scope,
    )


@router.post("/feedback")
def feedback_submit(
    data: SupportFeedbackCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return submit_feedback(db, current_user, data)


@router.patch("/feedback/{feedback_id}")
def feedback_update(
    feedback_id: int,
    data: SupportFeedbackUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_feedback(db, feedback_id, current_user, data)


@router.delete("/feedback/{feedback_id}")
def feedback_delete(
    feedback_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_feedback(db, feedback_id, current_user)
