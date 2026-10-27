"""Personal analysis endpoints, separate from legacy editorial focus content."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.access import ensure_paid_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.schemas.targeted_performance import PerformanceRequest, PerformanceAnswersRequest, TargetedPracticeRequest
from app.services.targeted_performance_service import performance, performance_answers
from app.services.targeted_practice_service import select_practice

router = APIRouter(tags=["targeted_performance"])


def access(current_user: AuthUser = Depends(get_current_user)):
    ensure_paid_access(current_user, detail="定向备面需付费开通后使用")
    return current_user


@router.post("/targeted/performance")
def overview(data: PerformanceRequest, user: AuthUser = Depends(access), db: Session = Depends(get_db)):
    return performance(db, user.username, data)


@router.post("/targeted/performance/answers")
def answers(data: PerformanceAnswersRequest, user: AuthUser = Depends(access), db: Session = Depends(get_db)):
    return performance_answers(db, user.username, data)


@router.post("/targeted/practice-selections")
def selections(data: TargetedPracticeRequest, user: AuthUser = Depends(access), db: Session = Depends(get_db)):
    return select_practice(db, user.username, data)
