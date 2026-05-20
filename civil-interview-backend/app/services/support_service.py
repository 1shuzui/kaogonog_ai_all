"""Support feedback service."""
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
    if not getattr(current_user, "isAdmin", False):
        raise HTTPException(status_code=403, detail="仅管理员可删除客服反馈")
    record = db.query(SupportFeedback).filter(SupportFeedback.id == feedback_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    db.delete(record)
    db.commit()
    return {"success": True, "id": feedback_id}


async def save_support_feedback_attachment(file: UploadFile) -> dict:
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
