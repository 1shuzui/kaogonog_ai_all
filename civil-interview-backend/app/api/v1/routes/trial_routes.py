from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.trial_service import complete_trial, get_trial_question, get_trial_status

router = APIRouter(prefix="/trial", tags=["trial"])


@router.get("/status")
def trial_status(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_trial_status(db, current_user)


@router.get("/question")
def trial_question(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_trial_question(db, current_user)


@router.post("/complete")
def trial_complete(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return complete_trial(db, current_user)
