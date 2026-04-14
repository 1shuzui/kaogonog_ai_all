from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, UserProfileUpdate, UserPasswordUpdate
from app.services.user_service import get_user_info, update_user_profile, change_password, update_preferences, get_provinces

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/info")
def user_info(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_info(db, current_user)


@router.get("/me")
def user_me(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_info(db, current_user)


@router.put("/profile")
def update_profile(data: UserProfileUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_user_profile(db, current_user, data)


@router.put("/password")
def update_password(data: UserPasswordUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return change_password(db, current_user, data)


@router.put("/preferences")
def update_prefs(data: dict, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_preferences(db, current_user, data)


@router.get("/provinces")
def provinces():
    return get_provinces()
