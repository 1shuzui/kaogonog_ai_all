"""User service: profile, password, preferences, provinces"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_password, get_password_hash
from app.models.entities import User
from app.schemas.common import AuthUser, UserProfileUpdate, UserPasswordUpdate

PROVINCES = [
    {"code": "national", "name": "国家公务员考试"},
    {"code": "beijing", "name": "北京"},
    {"code": "guangdong", "name": "广东"},
    {"code": "zhejiang", "name": "浙江"},
    {"code": "sichuan", "name": "四川"},
    {"code": "jiangsu", "name": "江苏"},
    {"code": "henan", "name": "河南"},
    {"code": "shandong", "name": "山东"},
    {"code": "hubei", "name": "湖北"},
    {"code": "hunan", "name": "湖南"},
    {"code": "liaoning", "name": "辽宁"},
    {"code": "shanxi", "name": "陕西"},
]

DEFAULT_PREFERENCES = {
    "defaultPrepTime": 90,
    "defaultAnswerTime": 180,
    "enableVideo": True,
}


def _get_user_or_404(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user


def _normalize_preferences(prefs: dict | None) -> dict:
    merged = DEFAULT_PREFERENCES.copy()
    if isinstance(prefs, dict):
        merged.update({key: value for key, value in prefs.items() if value is not None})
    return merged


def get_user_info(db: Session, current_user: AuthUser) -> dict:
    user = _get_user_or_404(db, current_user.username)
    return {
        "id": user.username,
        "name": user.full_name or user.username,
        "avatar": user.avatar or "",
        "province": user.province or "national",
        "email": user.email or "",
        "preferences": _normalize_preferences(user.preferences),
    }


def update_user_profile(db: Session, current_user: AuthUser, data: UserProfileUpdate) -> dict:
    user = _get_user_or_404(db, current_user.username)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.avatar is not None:
        user.avatar = data.avatar
    if data.province is not None:
        user.province = data.province
    db.commit()
    return {"success": True, "message": "信息已更新"}


def change_password(db: Session, current_user: AuthUser, data: UserPasswordUpdate) -> dict:
    user = _get_user_or_404(db, current_user.username)
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "密码修改成功"}


def update_preferences(db: Session, current_user: AuthUser, prefs: dict) -> dict:
    user = _get_user_or_404(db, current_user.username)
    current = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    incoming = dict(prefs) if isinstance(prefs, dict) else {}
    current.update(incoming)
    user.preferences = _normalize_preferences(current)
    db.commit()
    return {"success": True, "message": "偏好设置已更新"}


def get_provinces() -> list:
    return PROVINCES
