"""
客服反馈服务层，负责保存用户反馈、附件、管理员备注、处理状态和删除操作。

反馈可能来自题目纠错、支付失败、ASR 转写问题、页面体验或其他售后线索。这里的职责是留痕和分派，
不直接改题库、不直接退款、不直接调整权益；管理员需要根据反馈跳转到题库、支付或权益后台完成后续动作。
附件保存在后端 uploads/support 下，限制文件类型和大小是为了避免把反馈入口变成任意文件存储。

@param: 服务函数接收数据库 Session、当前用户、反馈创建/更新请求、附件文件或筛选条件。
@return: 返回反馈列表、反馈详情、创建结果、附件信息、状态更新结果或删除结果。
@raises HTTPException: 非管理员、反馈不存在、附件过大/类型不支持或用户无权访问时抛出 HTTP 错误。
"""
from datetime import datetime, timezone
from pathlib import Path
import mimetypes
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import SupportFeedback
from app.schemas.common import AuthUser, SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "support-feedback"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

EMPTY_FILTER_VALUES = {"", "undefined", "null", "none", "全部类型", "全部状态", "全部省份"}
VALID_FEEDBACK_STATUSES = {"pending", "handled"}
ALLOWED_ATTACHMENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_ATTACHMENT_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENTS_PER_FEEDBACK = 8


def _clean_text(value) -> str:
    return str(value or "").strip()


def _clean_filter(value) -> str:
    normalized = _clean_text(value)
    return "" if normalized.lower() in EMPTY_FILTER_VALUES else normalized


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _sanitize_upload_name(raw_name: str) -> str:
    safe_name = "".join(ch for ch in str(raw_name or "") if ch.isalnum() or ch in {"-", "_", "."})
    return safe_name or "feedback.png"


def _normalize_attachment(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    url = _clean_text(item.get("url"))
    if not url:
        return None
    size = item.get("size", 0)
    try:
        size = max(0, int(size or 0))
    except (TypeError, ValueError):
        size = 0
    return {
        "storageKey": _clean_text(item.get("storageKey") or item.get("storage_key") or item.get("key")),
        "filename": _clean_text(item.get("filename") or item.get("name")),
        "url": url,
        "size": size,
        "mimeType": _clean_text(item.get("mimeType") or item.get("mime_type") or item.get("type")),
        "uploadedAt": _clean_text(item.get("uploadedAt") or item.get("uploaded_at")),
    }


def _normalize_attachments(items) -> list[dict]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items[:MAX_ATTACHMENTS_PER_FEEDBACK]:
        attachment = _normalize_attachment(item)
        if attachment:
            normalized.append(attachment)
    return normalized


def _serialize_feedback(record: SupportFeedback) -> dict:
    return {
        "id": record.id,
        "username": record.username,
        "type": record.feedback_type or "其他建议",
        "questionId": record.question_id or "",
        "summary": record.summary or "",
        "contact": record.contact or "",
        "routePath": record.route_path or "",
        "province": record.province or "",
        "status": record.status or "pending",
        "adminNote": record.admin_note or "",
        "handledBy": record.handled_by or "",
        "handledAt": _iso(record.handled_at),
        "attachments": record.attachments if isinstance(record.attachments, list) else [],
        "createdAt": _iso(record.created_at),
        "updatedAt": _iso(record.updated_at),
    }


def _base_visible_query(db: Session, current_user: AuthUser, scope: str):
    query = db.query(SupportFeedback)
    if getattr(current_user, "isAdmin", False) and _clean_filter(scope) == "all":
        return query
    return query.filter(SupportFeedback.username == current_user.username)


def _apply_feedback_filters(query, *, feedback_type: str = "", status: str = "", province: str = "", keyword: str = ""):
    feedback_type = _clean_filter(feedback_type)
    status = _clean_filter(status)
    province = _clean_filter(province)
    keyword = _clean_filter(keyword)

    if feedback_type:
        query = query.filter(SupportFeedback.feedback_type == feedback_type)
    if status in VALID_FEEDBACK_STATUSES:
        query = query.filter(SupportFeedback.status == status)
    if province:
        query = query.filter(SupportFeedback.province == province)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                SupportFeedback.summary.ilike(pattern),
                SupportFeedback.question_id.ilike(pattern),
                SupportFeedback.contact.ilike(pattern),
                SupportFeedback.route_path.ilike(pattern),
                SupportFeedback.username.ilike(pattern),
            )
        )
    return query


def _build_summary(db: Session, current_user: AuthUser, filtered_query, *, feedback_type: str, status: str, province: str, keyword: str) -> dict:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    mine_query = db.query(SupportFeedback).filter(SupportFeedback.username == current_user.username)
    mine_query = _apply_feedback_filters(
        mine_query,
        feedback_type=feedback_type,
        status=status,
        province=province,
        keyword=keyword,
    )
    return {
        "total": filtered_query.count(),
        "pending": filtered_query.filter(SupportFeedback.status == "pending").count(),
        "handled": filtered_query.filter(SupportFeedback.status == "handled").count(),
        "today": filtered_query.filter(SupportFeedback.created_at >= today_start).count(),
        "mine": mine_query.count(),
    }


def list_support_feedback(
    db: Session,
    current_user: AuthUser,
    *,
    current: int = 1,
    page_size: int = 10,
    feedback_type: str = "",
    status: str = "",
    province: str = "",
    keyword: str = "",
    scope: str = "mine",
) -> dict:
    """
    按权限和筛选条件列出反馈，普通用户只看自己的，管理员看全站待处理问题。

    反馈列表在服务端收口，是为了避免端侧漏筛导致用户看到别人的联系方式或截图。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param current: 当前页码。
    @param page_size: 每页条数。
    @param feedback_type: 反馈类型筛选。
    @param status: 处理状态筛选。
    @param province: 反馈关联地区筛选。
    @param keyword: 标题、正文、题号或用户名搜索词。
    @param scope: 普通用户通常为 `mine`，管理员可请求全量范围。
    @return: 分页反馈列表和当前筛选下的统计摘要。
    @raises HTTPException: 非管理员请求全量范围时由可见性查询抛出越权错误。
    """
    current = max(1, int(current or 1))
    page_size = min(max(1, int(page_size or 10)), 200)
    query = _base_visible_query(db, current_user, scope)
    query = _apply_feedback_filters(
        query,
        feedback_type=feedback_type,
        status=status,
        province=province,
        keyword=keyword,
    )
    total = query.count()
    records = (
        query.order_by(SupportFeedback.created_at.desc(), SupportFeedback.id.desc())
        .offset((current - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "list": [_serialize_feedback(record) for record in records],
        "total": total,
        "current": current,
        "pageSize": page_size,
        "summary": _build_summary(
            db,
            current_user,
            query,
            feedback_type=feedback_type,
            status=status,
            province=province,
            keyword=keyword,
        ),
    }


def create_support_feedback(db: Session, current_user: AuthUser, data: SupportFeedbackCreateRequest) -> dict:
    """
    创建用户反馈记录，保留题目、页面路径和联系方式，方便管理员按场景回查。

    描述不能为空，是为了避免后台出现无法处理的空工单。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param data: 反馈创建请求。
    @return: 新建反馈详情。
    @raises HTTPException: 反馈描述为空或保存失败时抛出。
    """
    summary = _clean_text(data.summary)
    if not summary:
        raise HTTPException(status_code=400, detail="请填写反馈描述")
    record = SupportFeedback(
        username=current_user.username,
        feedback_type=_clean_filter(data.type) or "其他建议",
        question_id=_clean_text(data.questionId),
        summary=summary,
        contact=_clean_text(data.contact),
        route_path=_clean_text(data.routePath),
        province=_clean_filter(data.province),
        status="pending",
        attachments=_normalize_attachments(data.attachments),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_feedback(record)


def update_support_feedback(db: Session, current_user: AuthUser, feedback_id: int, data: SupportFeedbackUpdateRequest) -> dict:
    """
    让管理员更新反馈状态和处理备注，形成可追踪的客服闭环。

    普通用户不能改状态，否则待处理数量和处理人记录会失真。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param feedback_id: 反馈记录 ID。
    @param data: 状态和管理员备注更新请求。
    @return: 更新后的反馈详情。
    @raises HTTPException: 非管理员、反馈不存在或状态值无效时抛出。
    """
    if not getattr(current_user, "isAdmin", False):
        raise HTTPException(status_code=403, detail="仅管理员可处理客服反馈")
    record = db.query(SupportFeedback).filter(SupportFeedback.id == feedback_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")

    status = _clean_filter(data.status)
    if status:
        if status not in VALID_FEEDBACK_STATUSES:
            raise HTTPException(status_code=400, detail="反馈状态无效")
        record.status = status
        if status == "handled":
            record.handled_at = record.handled_at or _now()
            record.handled_by = current_user.username
        else:
            record.handled_at = None
            record.handled_by = ""
    if data.adminNote is not None:
        record.admin_note = _clean_text(data.adminNote)
    record.updated_at = _now()
    db.commit()
    db.refresh(record)
    return _serialize_feedback(record)


def delete_support_feedback(db: Session, current_user: AuthUser, feedback_id: int) -> dict:
    """
    删除误提交或无效反馈，只允许管理员操作。

    删除动作不开放给普通用户，是为了保留问题追踪和审核排查记录。

    @param db: 当前请求复用的数据库会话。
    @param current_user: 鉴权层解析出的用户身份。
    @param feedback_id: 反馈记录 ID。
    @return: 删除成功标记。
    @raises HTTPException: 非管理员或反馈不存在时抛出。
    """
    if not getattr(current_user, "isAdmin", False):
        raise HTTPException(status_code=403, detail="仅管理员可删除客服反馈")
    record = db.query(SupportFeedback).filter(SupportFeedback.id == feedback_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    db.delete(record)
    db.commit()
    return {"success": True, "id": feedback_id}


async def save_support_feedback_attachment(file: UploadFile) -> dict:
    """
    保存反馈截图并限制大小和类型，防止客服入口变成任意文件上传通道。

    上传结果只返回相对路径和文件信息，便于前端绑定到后续反馈表单。

    @param file: 用户上传的反馈截图。
    @return: 附件相对路径、原始文件名、大小和类型。
    @raises HTTPException: 文件为空、超过大小限制、类型不支持或写入失败时抛出。
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="反馈截图不能为空")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="单张反馈图片不能超过 5MB")

    original_name = _sanitize_upload_name(file.filename or "feedback.png")
    suffix = Path(original_name).suffix.lower()
    content_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    if content_type not in ALLOWED_ATTACHMENT_TYPES and suffix not in ALLOWED_ATTACHMENT_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG、WEBP、GIF 图片")
    if suffix not in ALLOWED_ATTACHMENT_SUFFIXES:
        suffix = mimetypes.guess_extension(content_type) or ".png"

    now = _now()
    stored_name = f"feedback_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{suffix}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(content)

    return {
        "storageKey": f"support-feedback/{stored_name}",
        "filename": original_name,
        "url": f"/uploads/support-feedback/{stored_name}",
        "size": len(content),
        "mimeType": content_type,
        "uploadedAt": now.isoformat(),
    }
