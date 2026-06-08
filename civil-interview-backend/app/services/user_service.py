"""
这个文件处理用户资料、省份偏好、练习偏好和活跃时间；这些信息会影响首页默认筛选和后台统计，所以统一从这里读写。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
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
    {"code": "shanghai", "name": "上海"},
    {"code": "guangdong", "name": "广东"},
    {"code": "zhejiang", "name": "浙江"},
    {"code": "sichuan", "name": "四川"},
    {"code": "jiangsu", "name": "江苏"},
    {"code": "anhui", "name": "安徽"},
    {"code": "henan", "name": "河南"},
    {"code": "shandong", "name": "山东"},
    {"code": "hubei", "name": "湖北"},
    {"code": "hunan", "name": "湖南"},
    {"code": "hebei", "name": "河北"},
    {"code": "fujian", "name": "福建"},
    {"code": "liaoning", "name": "辽宁"},
    {"code": "shanxi", "name": "陕西"},
]

VALID_PROVINCES = {item["code"] for item in PROVINCES}
LATEST_TERMS_VERSION = "v1.0"

DEFAULT_PREFERENCES = {
    "defaultPrepTime": 90,
    "defaultAnswerTime": 180,
    "enableVideo": True,
    "enableAudio": True,
    "preferredQuestionDimensions": [],
    "practicePreferenceConfirmed": False,
    "examCategory": "",
}
VALID_PREFERRED_QUESTION_DIMENSIONS = {
    "analysis",
    "practical",
    "emergency",
    "logic",
    "expression",
    "legal",
}


def get_user_or_404(db: Session, username: str) -> User:
    """
    get_user_or_404 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
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
    raw_dimensions = merged.get("preferredQuestionDimensions")
    if isinstance(raw_dimensions, str):
        raw_dimensions = [item.strip() for item in raw_dimensions.split(",")]
    if not isinstance(raw_dimensions, list):
        raw_dimensions = []
    seen_dimensions = set()
    merged["preferredQuestionDimensions"] = [
        item
        for item in (str(value).strip() for value in raw_dimensions)
        if item in VALID_PREFERRED_QUESTION_DIMENSIONS
        and not (item in seen_dimensions or seen_dimensions.add(item))
    ]
    merged["practicePreferenceConfirmed"] = bool(merged.get("practicePreferenceConfirmed"))
    merged["examCategory"] = str(merged.get("examCategory") or "").strip()
    merged["enableAudio"] = merged.get("enableAudio") is not False and merged.get("enableVideo") is not False
    merged["enableVideo"] = bool(merged.get("enableVideo"))
    merged["billing"] = normalize_billing_state(raw_preferences.get("billing"))
    return merged


def get_user_info(db: Session, current_user: AuthUser) -> dict:
    """
    get_user_info 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, current_user.username)
    normalized_preferences = _normalize_preferences(user.preferences)
    raw_preferences = user.preferences if isinstance(user.preferences, dict) else {}
    wechat_mini = raw_preferences.get("wechatMiniProgram") if isinstance(raw_preferences.get("wechatMiniProgram"), dict) else {}
    generated_wechat_username = user.username.startswith("wxmp_")
    access_context = build_access_context(user)
    terms = get_terms_status(db, user.username)
    return {
        "id": user.username,
        "name": user.full_name or user.username,
        "avatar": user.avatar or "",
        "province": user.province or "national",
        "email": user.email or "",
        "registeredAt": user.registered_at.isoformat() if user.registered_at else "",
        "createdAt": user.created_at.isoformat() if user.created_at else "",
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else "",
        "lastActiveAt": user.last_active_at.isoformat() if user.last_active_at else "",
        "preferences": {
            key: normalized_preferences[key]
            for key in DEFAULT_PREFERENCES
        },
        "terms": terms,
        "accountBindings": {
            "wechatMiniBound": bool(wechat_mini.get("openId")),
            "wechatUnionBound": bool(wechat_mini.get("unionId")),
            "wechatWebBound": False,
        },
        "accountLogin": {
            "requiresPcAccountSetup": generated_wechat_username,
            "pcLoginUsername": "" if generated_wechat_username else user.username,
            "wechatGeneratedUsername": user.username if generated_wechat_username else "",
        },
        **access_context,
    }


def update_user_profile(db: Session, current_user: AuthUser, data: UserProfileUpdate) -> dict:
    """
    update_user_profile 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = get_user_or_404(db, current_user.username)
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
    """
    change_password 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "密码修改成功"}


def update_preferences(db: Session, current_user: AuthUser, prefs: dict) -> dict:
    """
    update_preferences 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param prefs: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, current_user.username)
    current = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    incoming = dict(prefs) if isinstance(prefs, dict) else {}
    user.preferences = _normalize_preferences({**current, **incoming})
    db.commit()
    return {"success": True, "message": "偏好设置已更新"}


def get_provinces() -> list:
    """
    get_provinces 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return PROVINCES


def update_user_province(db: Session, username: str, province: str) -> dict:
    """
    update_user_province 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @param province: 地区筛选值；只表示地域，不替代考试体系或岗位方向。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    if province not in VALID_PROVINCES:
        raise HTTPException(status_code=400, detail="无效的省份代码")
    user = get_user_or_404(db, username)
    user.province = province
    db.commit()
    return {"success": True, "province": province, "message": "省份已更新"}


def get_terms_status(db: Session, username: str) -> dict:
    """
    get_terms_status 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, username)
    agreed_version = user.agreed_terms_version or ""
    return {
        "hasAgreed": agreed_version == LATEST_TERMS_VERSION,
        "agreedVersion": agreed_version,
        "latestVersion": LATEST_TERMS_VERSION,
        "agreedAt": user.agreed_terms_at.isoformat() if user.agreed_terms_at else "",
        "needsUpdate": agreed_version != LATEST_TERMS_VERSION,
    }


def record_terms_agreement(db: Session, username: str, version: str) -> dict:
    """
    record_terms_agreement 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @param version: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
    version = str(version or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="协议版本不能为空")
    user = get_user_or_404(db, username)
    user.agreed_terms_version = version
    user.agreed_terms_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "success": True,
        "version": user.agreed_terms_version,
        "agreedAt": user.agreed_terms_at.isoformat(),
    }


def check_device_risk(db: Session, username: str, device_id: str) -> dict:
    """
    check_device_risk 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @param device_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    device_id = str(device_id or "").strip()
    if not device_id:
        return {
            "riskLevel": "unknown",
            "isNewDevice": False,
            "deviceCount": 0,
            "warning": "未提供设备标识，无法完成设备风险检测",
        }

    user = get_user_or_404(db, username)
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
