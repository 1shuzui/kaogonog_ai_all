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
    return get_history_trend(db, current_user.username, days=days)


@router.get("/stats")
def history_stats(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_history_stats(db, current_user.username)


@router.get("/{exam_id}")
def history_detail(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_history_detail(db, exam_id)
