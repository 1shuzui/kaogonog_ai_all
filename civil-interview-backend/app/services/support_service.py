"""Support feedback service."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access
from app.schemas.common import AuthUser, SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest
from app.models.entities import FeedbackTicket

VALID_FEEDBACK_STATUSES = {"pending", "handled"}


def _serialize_feedback(ticket: FeedbackTicket) -> dict:
    return {
        "id": ticket.id,
        "type": ticket.feedback_type,
        "questionId": ticket.question_id or "",
        "summary": ticket.summary or "",
        "contact": ticket.contact or "",
        "routePath": ticket.route_path or "",
        "province": ticket.province or "",
        "username": ticket.username or "",
        "status": ticket.status or "pending",
        "adminNote": ticket.admin_note or "",
        "handledBy": ticket.handled_by or "",
        "createdAt": ticket.created_at.isoformat() if ticket.created_at else "",
        "updatedAt": ticket.updated_at.isoformat() if ticket.updated_at else "",
        "handledAt": ticket.handled_at.isoformat() if ticket.handled_at else "",
    }


def _get_ticket_or_404(db: Session, feedback_id: int) -> FeedbackTicket:
    ticket = db.query(FeedbackTicket).filter(FeedbackTicket.id == feedback_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    return ticket


def _apply_filters(query, feedback_type: str = "", status: str = "", province: str = "", keyword: str = ""):
    normalized_type = str(feedback_type or "").strip()
    normalized_status = str(status or "").strip()
    normalized_province = str(province or "").strip()
    normalized_keyword = str(keyword or "").strip()

    if normalized_type:
        query = query.filter(FeedbackTicket.feedback_type == normalized_type)
    if normalized_status:
        query = query.filter(FeedbackTicket.status == normalized_status)
    if normalized_province:
        query = query.filter(FeedbackTicket.province == normalized_province)
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                FeedbackTicket.question_id.like(pattern),
                FeedbackTicket.summary.like(pattern),
                FeedbackTicket.contact.like(pattern),
                FeedbackTicket.username.like(pattern),
                FeedbackTicket.route_path.like(pattern),
            )
        )
    return query


def submit_feedback(db: Session, current_user: AuthUser, data: SupportFeedbackCreateRequest) -> dict:
    summary = str(data.summary or "").strip()
    if not summary:
        raise HTTPException(status_code=400, detail="反馈内容不能为空")

    ticket = FeedbackTicket(
        username=current_user.username,
        feedback_type=str(data.type or "").strip() or "其他建议",
        question_id=str(data.questionId or "").strip(),
        summary=summary,
        contact=str(data.contact or "").strip(),
        route_path=str(data.routePath or "").strip(),
        province=str(data.province or "").strip(),
        status="pending",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"success": True, "record": _serialize_feedback(ticket)}


def list_feedback(
    db: Session,
    current_user: AuthUser,
    *,
    current: int = 1,
    page_size: int = 20,
    feedback_type: str = "",
    status: str = "",
    province: str = "",
    keyword: str = "",
    scope: str = "mine",
) -> dict:
    current = max(1, int(current or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    normalized_scope = str(scope or "mine").strip().lower()

    base_query = db.query(FeedbackTicket)
    if not current_user.isAdmin or normalized_scope != "all":
        base_query = base_query.filter(FeedbackTicket.username == current_user.username)

    filtered_query = _apply_filters(
        base_query,
        feedback_type=feedback_type,
        status=status,
        province=province,
        keyword=keyword,
    )

    total = filtered_query.count()
    records = (
        filtered_query
        .order_by(FeedbackTicket.created_at.desc(), FeedbackTicket.id.desc())
        .offset((current - 1) * page_size)
        .limit(page_size)
        .all()
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    visible_query = base_query
    mine_query = db.query(FeedbackTicket).filter(FeedbackTicket.username == current_user.username)
    summary = {
        "total": visible_query.count(),
        "pending": visible_query.filter(FeedbackTicket.status != "handled").count(),
        "handled": visible_query.filter(FeedbackTicket.status == "handled").count(),
        "today": visible_query.filter(FeedbackTicket.created_at >= today_start).count(),
        "mine": mine_query.count(),
    }

    return {
        "list": [_serialize_feedback(item) for item in records],
        "total": total,
        "current": current,
        "pageSize": page_size,
        "summary": summary,
    }


def update_feedback(db: Session, feedback_id: int, current_user: AuthUser, data: SupportFeedbackUpdateRequest) -> dict:
    ensure_admin_access(current_user)
    ticket = _get_ticket_or_404(db, feedback_id)

    status = str(data.status or ticket.status or "pending").strip().lower()
    if status not in VALID_FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail="无效的反馈状态")

    ticket.status = status
    ticket.admin_note = str(data.adminNote or ticket.admin_note or "").strip()
    if status == "handled":
        ticket.handled_at = datetime.now(timezone.utc)
        ticket.handled_by = current_user.username
    else:
        ticket.handled_at = None
        ticket.handled_by = ""
    db.commit()
    db.refresh(ticket)
    return {"success": True, "record": _serialize_feedback(ticket)}


def delete_feedback(db: Session, feedback_id: int, current_user: AuthUser) -> dict:
    ensure_admin_access(current_user)
    ticket = _get_ticket_or_404(db, feedback_id)
    db.delete(ticket)
    db.commit()
    return {"success": True}
