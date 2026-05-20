from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.subscription_service import check_subscription_access, get_subscription_status

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/me")
def subscription_me(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_subscription_status(db, current_user)


@router.get("/check-access")
def subscription_check_access(mode: str = "practice", current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return check_subscription_access(db, current_user, mode)
