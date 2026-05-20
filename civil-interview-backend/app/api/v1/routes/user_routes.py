from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    UserPasswordUpdate,
    UserPreferencesUpdate,
    UserProfileUpdate,
    UserProvinceUpdate,
    UserTermsAgreementRequest,
)
from app.services.user_service import (
    change_password,
    check_device_risk,
    get_provinces,
    get_terms_status,
    get_user_info,
    record_terms_agreement,
    update_preferences,
    update_user_profile,
    update_user_province,
)

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
def update_prefs(data: UserPreferencesUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_preferences(db, current_user, data.model_dump(exclude_none=True))


@router.get("/provinces")
def provinces():
    return get_provinces()


@router.put("/province")
def update_province(data: UserProvinceUpdate, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_user_province(db, current_user.username, data.province)


@router.get("/terms-status")
def terms_status(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_terms_status(db, current_user.username)


@router.post("/agree-terms")
def agree_terms(data: UserTermsAgreementRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return record_terms_agreement(db, current_user.username, data.version)


@router.get("/device-risk")
def device_risk(
    x_device_id: str = Header(default="", alias="X-Device-ID"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return check_device_risk(db, current_user.username, x_device_id)
