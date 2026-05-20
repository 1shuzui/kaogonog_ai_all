"""User service: profile, password, preferences, provinces"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.access import build_access_context, normalize_billing_state
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

VALID_PROVINCES = {item["code"] for item in PROVINCES}
LATEST_TERMS_VERSION = "v1.0"

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
    raw_preferences = prefs if isinstance(prefs, dict) else {}
    merged = DEFAULT_PREFERENCES.copy()
    merged.update(
        {
            key: value
            for key, value in raw_preferences.items()
            if key in DEFAULT_PREFERENCES and value is not None
        }
    )
    merged["billing"] = normalize_billing_state(raw_preferences.get("billing"))
    return merged


def get_user_info(db: Session, current_user: AuthUser) -> dict:
    user = _get_user_or_404(db, current_user.username)
    normalized_preferences = _normalize_preferences(user.preferences)
    access_context = build_access_context(user)
    terms = get_terms_status(db, user.username)
    return {
        "id": user.username,
        "name": user.full_name or user.username,
        "avatar": user.avatar or "",
        "province": user.province or "national",
        "email": user.email or "",
        "preferences": {
            key: normalized_preferences[key]
            for key in DEFAULT_PREFERENCES
        },
        "terms": terms,
        **access_context,
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
        if data.province not in VALID_PROVINCES:
            raise HTTPException(status_code=400, detail="无效的省份代码")
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
    user.preferences = _normalize_preferences({**current, **incoming})
    db.commit()
    return {"success": True, "message": "偏好设置已更新"}


def get_provinces() -> list:
    return PROVINCES


def update_user_province(db: Session, username: str, province: str) -> dict:
    if province not in VALID_PROVINCES:
        raise HTTPException(status_code=400, detail="无效的省份代码")
    user = _get_user_or_404(db, username)
    user.province = province
    db.commit()
    return {"success": True, "province": province, "message": "省份已更新"}


def get_terms_status(db: Session, username: str) -> dict:
    user = _get_user_or_404(db, username)
    agreed_version = user.agreed_terms_version or ""
    return {
        "hasAgreed": agreed_version == LATEST_TERMS_VERSION,
        "agreedVersion": agreed_version,
        "latestVersion": LATEST_TERMS_VERSION,
        "agreedAt": user.agreed_terms_at.isoformat() if user.agreed_terms_at else "",
        "needsUpdate": agreed_version != LATEST_TERMS_VERSION,
    }


def record_terms_agreement(db: Session, username: str, version: str) -> dict:
    version = str(version or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="协议版本不能为空")
    user = _get_user_or_404(db, username)
    user.agreed_terms_version = version
    user.agreed_terms_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "success": True,
        "version": user.agreed_terms_version,
        "agreedAt": user.agreed_terms_at.isoformat(),
    }


def check_device_risk(db: Session, username: str, device_id: str) -> dict:
    device_id = str(device_id or "").strip()
    if not device_id:
        return {
            "riskLevel": "unknown",
            "isNewDevice": False,
            "deviceCount": 0,
            "warning": "未提供设备标识，无法完成设备风险检测",
        }

    user = _get_user_or_404(db, username)
    history = user.login_device_history if isinstance(user.login_device_history, list) else []
    existing_ids = {
        str(item.get("deviceId"))
        for item in history
        if isinstance(item, dict) and item.get("deviceId")
    }
    is_new_device = device_id not in existing_ids

    if is_new_device:
        history.append({
            "deviceId": device_id,
            "firstSeenAt": datetime.now(timezone.utc).isoformat(),
        })
        history = history[-10:]
        user.login_device_history = history
        user.last_login_device = device_id
        db.commit()
        existing_ids.add(device_id)

    device_count = len(existing_ids)
    if device_count >= 5:
        risk_level = "high"
        warning = "检测到账号在多个设备上使用，请确认是否为本人操作。"
    elif device_count >= 3:
        risk_level = "medium"
        warning = "检测到账号存在多设备使用情况，请注意账号安全。"
    elif is_new_device:
        risk_level = "low"
        warning = "检测到新设备登录，请确认是否为本人操作。"
    else:
        risk_level = "safe"
        warning = ""

    return {
        "riskLevel": risk_level,
        "isNewDevice": is_new_device,
        "deviceCount": device_count,
        "warning": warning,
    }
