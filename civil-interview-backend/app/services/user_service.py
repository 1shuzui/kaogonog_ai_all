"""
用户资料服务层，统一读写个人信息、省份偏好、练习偏好、协议同意、登录设备风险和活跃时间。

首页默认筛选、定向备面默认值、后台用户搜索、活跃用户统计和权益快照都依赖用户表里的偏好字段。
这里不直接处理支付、试用或评分，只维护用户身份周边信息；涉及套餐余额的展示通过订阅服务同步到 preferences，
避免 PC 和小程序各自拼一份“我的权益”。

@param: 服务函数接收数据库 Session、当前用户、资料更新请求、密码更新请求、偏好更新请求或设备标识。
@return: 返回用户详情、更新后的资料、协议状态、设备风险提示或活跃状态。
@raises HTTPException: 用户不存在、旧密码错误、偏好格式不合法或设备风险校验失败时抛出 HTTP 错误。
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
    按用户名取得用户，并把“账号不存在”的接口语义统一成 404。

    很多业务表仍以 `username` 串联历史、权益、订单和反馈，不能让各个服务各自决定空用户如何处理。
    集中在这里抛错能避免某些接口返回空对象、某些接口返回 500，减少 PC 和小程序端的兼容分支。

    @param db: 当前请求或脚本复用的数据库会话。
    @param username: 用户名主键口径；与现有历史数据保持兼容。
    @return: 命中的用户 ORM 实例。
    @raises HTTPException: 用户不存在时返回 404。
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
    汇总“我的”页和登录态刷新所需的用户资料。

    这里故意把偏好、协议、微信绑定和权益入口状态一起返回，因为双端都会在启动后读取这份摘要。
    后端统一归一化旧偏好字段，可以让老账号、小程序游客转正账号和 PC 登录账号走同一份展示逻辑。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @return: 用户基础资料、偏好、协议状态、账号绑定状态和访问能力摘要。
    @raises HTTPException: 当前用户在数据库中不存在时抛出 404。
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
    更新用户可自行维护的公开资料和默认地区。

    省份字段只作为默认地区偏好保留，不再代表考试体系；因此仍要校验合法代码，避免旧页面把任意展示文案写进用户表。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param data: 用户资料更新请求，未传字段保持原值。
    @return: 更新成功提示。
    @raises HTTPException: 用户不存在或省份代码不在白名单内时抛出。
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
    在已登录状态下修改 PC 账号密码。

    微信小程序账号可能是系统生成的用户名，但只要绑定了 PC 登录能力，密码校验就必须在后端完成，
    否则前端无法可靠区分旧密码错误和账号异常。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param data: 旧密码和新密码请求体。
    @return: 修改成功提示。
    @raises HTTPException: 用户不存在或旧密码不匹配时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "密码修改成功"}


def update_preferences(db: Session, current_user: AuthUser, prefs: dict) -> dict:
    """
    合并并归一化用户练习偏好。

    偏好字段承载过多端历史版本，直接整体覆盖容易丢掉账单快照、微信绑定或新注册引导状态。
    因此这里采用“现有偏好 + 入参”的白名单合并，只让训练相关字段被用户端更新。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param prefs: 前端提交的偏好增量。
    @return: 更新成功提示。
    @raises HTTPException: 当前用户不存在时抛出 404。
    """
    user = get_user_or_404(db, current_user.username)
    current = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    incoming = dict(prefs) if isinstance(prefs, dict) else {}
    user.preferences = _normalize_preferences({**current, **incoming})
    db.commit()
    return {"success": True, "message": "偏好设置已更新"}


def get_provinces() -> list:
    """
    返回可选默认地区列表。

    这是用户偏好的地区白名单，不是题库考试体系分类树。保留“国家公务员考试”这个历史项是为了兼容旧用户默认值。

    @param: 无。
    @return: 省份代码和展示名列表。
    @raises: 不主动抛出业务异常。
    """
    return PROVINCES


def update_user_province(db: Session, username: str, province: str) -> dict:
    """
    更新指定用户的默认地区偏好。

    后台脚本和旧接口仍会按用户名直接更新地区，所以这里保留用户名参数；业务含义只限默认展示和筛选偏好，
    不应被导入脚本或题库分类拿来替代真实考试来源。

    @param db: 当前请求或脚本复用的数据库会话。
    @param username: 需要更新的用户名。
    @param province: 地区代码。
    @return: 更新后的地区代码和提示。
    @raises HTTPException: 用户不存在或地区代码无效时抛出。
    """
    if province not in VALID_PROVINCES:
        raise HTTPException(status_code=400, detail="无效的省份代码")
    user = get_user_or_404(db, username)
    user.province = province
    db.commit()
    return {"success": True, "province": province, "message": "省份已更新"}


def get_terms_status(db: Session, username: str) -> dict:
    """
    查询用户是否已同意当前版本协议。

    协议状态会影响登录后是否需要弹出确认，但不应该阻塞游客先浏览功能；后端只返回状态，
    由双端按审核要求决定何时展示提示。

    @param db: 当前请求复用的数据库会话。
    @param username: 需要查询的用户名。
    @return: 已同意版本、最新版本、同意时间和是否需要更新。
    @raises HTTPException: 用户不存在时抛出 404。
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
    记录用户主动确认的协议版本。

    只写入用户明确提交的版本号，不自动默认同意最新协议，避免登录流程、审核整改和隐私合规边界混在一起。

    @param db: 当前请求复用的数据库会话。
    @param username: 确认协议的用户名。
    @param version: 用户端展示并提交的协议版本。
    @return: 记录后的版本号和同意时间。
    @raises HTTPException: 版本号为空或用户不存在时抛出。
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
    维护轻量设备登录记录并给出风险提示。

    现阶段只做温和提醒，不做强封禁；这是为了兼顾考生换手机、微信开发工具调试和客服代查场景。
    历史只保留最近 10 个设备，避免把设备轨迹无限写入用户 JSON 字段。

    @param db: 当前请求复用的数据库会话。
    @param username: 需要检测的用户名。
    @param device_id: 端侧生成或微信环境提供的设备标识。
    @return: 风险等级、是否新设备、设备数量和用户可读提醒。
    @raises HTTPException: 用户不存在时抛出 404。
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
