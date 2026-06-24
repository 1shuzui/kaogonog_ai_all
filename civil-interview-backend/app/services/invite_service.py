"""
邀请码与渠道归因服务层。

这里集中处理邀请码规范化、合作公司和邀请码 CRUD、注册/首登归因绑定、首次会话 token、日活快照与报表聚合。
历史报表只读事件快照，不回算用户当前归因；管理员纠错只更新当前归因和审计，不改历史注册、活跃和支付事件。

@param: 服务函数接收数据库 Session、用户、邀请码请求、管理员操作请求或报表查询条件。
@return: 返回邀请码、合作公司、归因绑定、日活写入或报表结果。
@raises HTTPException: 邀请码无效、已停用、格式错误、会话失效或管理员参数非法时抛出 HTTP 错误。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import re
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access
from app.models.entities import (
    InviteActivityDaily,
    InviteAuditLog,
    InviteCode,
    InvitePartner,
    InvitePaymentEvent,
    InviteRegistrationEvent,
    PaymentOrder,
    User,
)
from app.schemas.common import (
    AuthUser,
    InviteAttributionCorrectionRequest,
    InviteCodeCreateRequest,
    InviteCodeUpdateRequest,
    InvitePartnerCreateRequest,
    InvitePartnerUpdateRequest,
    InviteReportQueryRequest,
    WechatMiniProgramInviteBindRequest,
)


INVITE_CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{3,32}$")
INVITE_SESSION_PREF_KEY = "wechatInviteFirstSession"
INVITE_SESSION_TTL_SECONDS = 15 * 60
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_today(now: datetime | None = None) -> date:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(BEIJING_TZ).date()


def normalize_invite_code(value: str | None) -> str:
    return str(value or "").strip().upper()


def validate_invite_code_format(code: str) -> str:
    normalized = normalize_invite_code(code)
    if not normalized:
        return ""
    if not INVITE_CODE_PATTERN.match(normalized):
        raise HTTPException(status_code=400, detail="邀请码格式不正确")
    return normalized


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _preferences(user: User) -> dict:
    return dict(user.preferences) if isinstance(user.preferences, dict) else {}


def _save_preferences(user: User, prefs: dict) -> None:
    user.preferences = prefs


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _parse_datetime(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _partner_snapshot(partner: InvitePartner | None) -> dict:
    if not partner:
        return {}
    return {
        "id": int(partner.id or 0),
        "name": partner.name or "",
        "enabled": bool(partner.enabled),
        "remark": partner.remark or "",
        "contactName": partner.contact_name or "",
        "contactPhone": partner.contact_phone or "",
        "contactWechat": partner.contact_wechat or "",
        "createdAt": partner.created_at.isoformat() if partner.created_at else "",
        "updatedAt": partner.updated_at.isoformat() if partner.updated_at else "",
    }


def _code_snapshot(code: InviteCode | None) -> dict:
    if not code:
        return {}
    partner = getattr(code, "partner", None)
    return {
        "id": int(code.id or 0),
        "code": code.code or "",
        "partnerId": int(code.partner_id or 0),
        "partnerName": partner.name if partner else "",
        "enabled": bool(code.enabled),
        "remark": code.remark or "",
        "createdBy": code.created_by or "",
        "createdAt": code.created_at.isoformat() if code.created_at else "",
        "updatedAt": code.updated_at.isoformat() if code.updated_at else "",
    }


def _user_invite_snapshot(user: User) -> dict:
    return {
        "username": user.username,
        "inviteCode": user.invite_code or "",
        "invitePartnerId": int(user.invite_partner_id or 0) if user.invite_partner_id else None,
        "inviteSource": user.invite_source or "",
        "inviteBoundAt": user.invite_bound_at.isoformat() if user.invite_bound_at else "",
    }


def _audit(
    db: Session,
    action_type: str,
    target_type: str,
    target_id: str,
    operator: str,
    before_snapshot: dict | None = None,
    after_snapshot: dict | None = None,
    reason: str = "",
) -> InviteAuditLog:
    record = InviteAuditLog(
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id or ""),
        operator=str(operator or ""),
        before_snapshot=before_snapshot or {},
        after_snapshot=after_snapshot or {},
        reason=str(reason or ""),
    )
    db.add(record)
    return record


def resolve_active_invite_code(db: Session, invite_code: str | None) -> InviteCode | None:
    code = validate_invite_code_format(invite_code)
    if not code:
        return None
    row = db.query(InviteCode).filter(InviteCode.code == code).first()
    if not row or not bool(row.enabled):
        raise HTTPException(status_code=400, detail="邀请码无效或已停用")
    partner = row.partner or db.query(InvitePartner).filter(InvitePartner.id == row.partner_id).first()
    if not partner or not bool(partner.enabled):
        raise HTTPException(status_code=400, detail="邀请码无效或已停用")
    return row


def user_has_invite_attribution(user: User) -> bool:
    return bool(user.invite_code or user.invite_partner_id or user.invite_bound_at)


def _apply_user_attribution(user: User, invite: InviteCode, source: str) -> None:
    partner = invite.partner
    user.invite_code = invite.code
    user.invite_partner_id = int(partner.id or invite.partner_id)
    user.invite_bound_at = _now()
    user.invite_source = source


def bind_registration_invite(db: Session, user: User, invite_code: str | None, source: str) -> bool:
    invite = resolve_active_invite_code(db, invite_code)
    if not invite:
        return False
    if user_has_invite_attribution(user):
        return False
    _apply_user_attribution(user, invite, source)
    partner = invite.partner
    existing = db.query(InviteRegistrationEvent).filter(
        InviteRegistrationEvent.username == user.username,
    ).first()
    if not existing:
        db.add(InviteRegistrationEvent(
            username=user.username,
            registered_date=beijing_today(user.registered_at or _now()),
            invite_code_id=int(invite.id or 0),
            invite_partner_id=int(partner.id or invite.partner_id),
            invite_code_snapshot=invite.code,
            invite_partner_snapshot=partner.name if partner else "",
            source=source,
        ))
    return True


def create_first_session_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    prefs = _preferences(user)
    prefs[INVITE_SESSION_PREF_KEY] = {
        "tokenHash": _token_hash(token),
        "expiresAt": (_now() + timedelta(seconds=INVITE_SESSION_TTL_SECONDS)).isoformat(),
        "used": False,
        "createdAt": _now().isoformat(),
    }
    _save_preferences(user, prefs)
    return token


def clear_first_session_token(user: User) -> None:
    prefs = _preferences(user)
    if INVITE_SESSION_PREF_KEY in prefs:
        prefs.pop(INVITE_SESSION_PREF_KEY, None)
        _save_preferences(user, prefs)


def _assert_first_session_token(user: User, token: str | None) -> dict:
    prefs = _preferences(user)
    session = prefs.get(INVITE_SESSION_PREF_KEY) if isinstance(prefs.get(INVITE_SESSION_PREF_KEY), dict) else {}
    if not session or session.get("used"):
        raise HTTPException(status_code=400, detail="邀请码补填会话已失效")
    expires_at = _parse_datetime(session.get("expiresAt") or "")
    if not expires_at or expires_at < _now():
        clear_first_session_token(user)
        raise HTTPException(status_code=400, detail="邀请码补填会话已失效")
    if _token_hash(token or "") != session.get("tokenHash"):
        raise HTTPException(status_code=400, detail="邀请码补填凭证不正确")
    return session


def bind_wechat_first_session_invite(
    db: Session,
    current_user: AuthUser,
    data: WechatMiniProgramInviteBindRequest,
) -> dict:
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user_has_invite_attribution(user):
        clear_first_session_token(user)
        db.commit()
        return {"success": True, "message": "邀请码已绑定，无需重复提交"}
    _assert_first_session_token(user, data.inviteSessionToken)
    bind_registration_invite(db, user, data.inviteCode, "wechat_first_session_bind")
    clear_first_session_token(user)
    db.commit()
    return {"success": True, "message": "邀请码已绑定"}


def bind_wechat_account_setup_invite(
    db: Session,
    user: User,
    invite_code: str | None,
    invite_session_token: str | None,
) -> bool:
    if not normalize_invite_code(invite_code):
        return False
    if user_has_invite_attribution(user):
        clear_first_session_token(user)
        return False
    _assert_first_session_token(user, invite_session_token)
    bound = bind_registration_invite(db, user, invite_code, "wechat_account_setup")
    clear_first_session_token(user)
    return bound


def record_user_daily_activity(db: Session, user: User, active_at: datetime | None = None) -> None:
    if not user or not user_has_invite_attribution(user):
        return
    active_date = beijing_today(active_at or _now())
    existing = db.query(InviteActivityDaily).filter(
        InviteActivityDaily.username == user.username,
        InviteActivityDaily.active_date == active_date,
    ).first()
    if existing:
        return
    partner_name = ""
    partner_id = int(user.invite_partner_id or 0) if user.invite_partner_id else None
    if partner_id:
        partner = db.query(InvitePartner).filter(InvitePartner.id == partner_id).first()
        partner_name = partner.name if partner else ""
    code = db.query(InviteCode).filter(InviteCode.code == user.invite_code).first() if user.invite_code else None
    db.add(InviteActivityDaily(
        username=user.username,
        active_date=active_date,
        invite_code_id=int(code.id or 0) if code else None,
        invite_partner_id=partner_id,
        invite_code_snapshot=user.invite_code or "",
        invite_partner_snapshot=partner_name,
    ))


def record_payment_event_for_order(db: Session, order: PaymentOrder) -> None:
    if not order or order.status != "paid":
        return
    existing = db.query(InvitePaymentEvent).filter(
        InvitePaymentEvent.order_no == order.order_no,
    ).first()
    if existing:
        return
    user = db.query(User).filter(User.username == order.username).first()
    if not user or not user_has_invite_attribution(user):
        return
    partner_name = ""
    partner_id = int(user.invite_partner_id or 0) if user.invite_partner_id else None
    if partner_id:
        partner = db.query(InvitePartner).filter(InvitePartner.id == partner_id).first()
        partner_name = partner.name if partner else ""
    code = db.query(InviteCode).filter(InviteCode.code == user.invite_code).first() if user.invite_code else None
    paid_amount = Decimal(str(order.amount or 0))
    db.add(InvitePaymentEvent(
        order_no=order.order_no,
        username=order.username,
        paid_date=beijing_today(order.paid_at or _now()),
        invite_code_id=int(code.id or 0) if code else None,
        invite_partner_id=partner_id,
        invite_code_snapshot=user.invite_code or "",
        invite_partner_snapshot=partner_name,
        paid_amount=paid_amount,
        refunded_amount=Decimal("0"),
        net_amount=paid_amount,
    ))


def update_payment_event_refund(db: Session, order: PaymentOrder, refunded_amount) -> None:
    event = db.query(InvitePaymentEvent).filter(InvitePaymentEvent.order_no == order.order_no).first()
    if not event:
        return
    amount = Decimal(str(refunded_amount or 0))
    event.refunded_amount = amount
    event.net_amount = Decimal(str(event.paid_amount or 0)) - amount
    if event.net_amount < 0:
        event.net_amount = Decimal("0")


def _clean_text(value: str | None, limit: int = 1000) -> str:
    return str(value or "").strip()[:limit]


def create_invite_partner(db: Session, current_user: AuthUser, data: InvitePartnerCreateRequest) -> dict:
    ensure_admin_access(current_user)
    name = _clean_text(data.name, 100)
    if db.query(InvitePartner).filter(InvitePartner.name == name).first():
        raise HTTPException(status_code=400, detail="合作公司名称已存在")
    partner = InvitePartner(
        name=name,
        enabled=bool(data.enabled),
        remark=_clean_text(data.remark),
        contact_name=_clean_text(data.contactName, 100),
        contact_phone=_clean_text(data.contactPhone, 50),
        contact_wechat=_clean_text(data.contactWechat, 100),
    )
    db.add(partner)
    db.flush()
    _audit(db, "create_partner", "invite_partner", str(partner.id), current_user.username, {}, _partner_snapshot(partner))
    db.commit()
    db.refresh(partner)
    return _partner_snapshot(partner)


def update_invite_partner(db: Session, current_user: AuthUser, partner_id: int, data: InvitePartnerUpdateRequest) -> dict:
    ensure_admin_access(current_user)
    partner = db.query(InvitePartner).filter(InvitePartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="合作公司不存在")
    before = _partner_snapshot(partner)
    if data.name is not None:
        name = _clean_text(data.name, 100)
        conflict = db.query(InvitePartner).filter(InvitePartner.name == name, InvitePartner.id != partner.id).first()
        if conflict:
            raise HTTPException(status_code=400, detail="合作公司名称已存在")
        partner.name = name
    if data.enabled is not None:
        partner.enabled = bool(data.enabled)
    if data.remark is not None:
        partner.remark = _clean_text(data.remark)
    if data.contactName is not None:
        partner.contact_name = _clean_text(data.contactName, 100)
    if data.contactPhone is not None:
        partner.contact_phone = _clean_text(data.contactPhone, 50)
    if data.contactWechat is not None:
        partner.contact_wechat = _clean_text(data.contactWechat, 100)
    db.flush()
    after = _partner_snapshot(partner)
    _audit(db, "update_partner", "invite_partner", str(partner.id), current_user.username, before, after)
    db.commit()
    db.refresh(partner)
    return _partner_snapshot(partner)


def delete_invite_partner(db: Session, current_user: AuthUser, partner_id: int) -> dict:
    ensure_admin_access(current_user)
    partner = db.query(InvitePartner).filter(InvitePartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="合作公司不存在")
    if db.query(InviteCode).filter(InviteCode.partner_id == partner.id).first():
        raise HTTPException(status_code=400, detail="合作公司下仍有邀请码，请先删除未使用邀请码或改为停用")
    used = (
        db.query(User).filter(User.invite_partner_id == partner.id).first()
        or db.query(InviteRegistrationEvent).filter(InviteRegistrationEvent.invite_partner_id == partner.id).first()
        or db.query(InviteActivityDaily).filter(InviteActivityDaily.invite_partner_id == partner.id).first()
        or db.query(InvitePaymentEvent).filter(InvitePaymentEvent.invite_partner_id == partner.id).first()
    )
    if used:
        raise HTTPException(status_code=400, detail="合作公司已有归因数据，不能删除，可改为停用")
    before = _partner_snapshot(partner)
    _audit(db, "delete_partner", "invite_partner", str(partner.id), current_user.username, before, {}, "delete unused partner")
    db.delete(partner)
    db.commit()
    return {"success": True, "message": "合作公司已删除"}


def list_invite_partners(db: Session, current_user: AuthUser) -> dict:
    ensure_admin_access(current_user)
    rows = db.query(InvitePartner).order_by(InvitePartner.created_at.desc(), InvitePartner.id.desc()).all()
    return {"list": [_partner_snapshot(row) for row in rows], "total": len(rows)}


def create_invite_code(db: Session, current_user: AuthUser, data: InviteCodeCreateRequest) -> dict:
    ensure_admin_access(current_user)
    code = validate_invite_code_format(data.code)
    partner = db.query(InvitePartner).filter(InvitePartner.id == data.partnerId).first()
    if not partner:
        raise HTTPException(status_code=404, detail="合作公司不存在")
    if db.query(InviteCode).filter(InviteCode.code == code).first():
        raise HTTPException(status_code=400, detail="邀请码已存在")
    row = InviteCode(
        code=code,
        partner_id=int(partner.id or 0),
        enabled=bool(data.enabled),
        remark=_clean_text(data.remark),
        created_by=current_user.username,
    )
    db.add(row)
    db.flush()
    _audit(db, "create_code", "invite_code", str(row.id), current_user.username, {}, _code_snapshot(row))
    db.commit()
    db.refresh(row)
    return _code_snapshot(row)


def update_invite_code(db: Session, current_user: AuthUser, code_id: int, data: InviteCodeUpdateRequest) -> dict:
    ensure_admin_access(current_user)
    row = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    before = _code_snapshot(row)
    has_attribution_data = (
        db.query(User).filter(User.invite_code == row.code).first()
        or db.query(InviteRegistrationEvent).filter(InviteRegistrationEvent.invite_code_id == row.id).first()
        or db.query(InviteActivityDaily).filter(InviteActivityDaily.invite_code_id == row.id).first()
        or db.query(InvitePaymentEvent).filter(InvitePaymentEvent.invite_code_id == row.id).first()
    )
    if data.code is not None:
        code = validate_invite_code_format(data.code)
        if has_attribution_data and code != row.code:
            raise HTTPException(status_code=400, detail="邀请码已有归因数据，不能修改码值，可改为停用后新建")
        conflict = db.query(InviteCode).filter(InviteCode.code == code, InviteCode.id != row.id).first()
        if conflict:
            raise HTTPException(status_code=400, detail="邀请码已存在")
        row.code = code
    if data.partnerId is not None:
        if has_attribution_data and int(data.partnerId) != int(row.partner_id or 0):
            raise HTTPException(status_code=400, detail="邀请码已有归因数据，不能修改归属公司，可改为停用后新建")
        partner = db.query(InvitePartner).filter(InvitePartner.id == data.partnerId).first()
        if not partner:
            raise HTTPException(status_code=404, detail="合作公司不存在")
        row.partner_id = int(partner.id or 0)
    if data.enabled is not None:
        row.enabled = bool(data.enabled)
    if data.remark is not None:
        row.remark = _clean_text(data.remark)
    db.flush()
    after = _code_snapshot(row)
    _audit(db, "update_code", "invite_code", str(row.id), current_user.username, before, after)
    db.commit()
    db.refresh(row)
    return _code_snapshot(row)


def delete_invite_code(db: Session, current_user: AuthUser, code_id: int) -> dict:
    ensure_admin_access(current_user)
    row = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    used = (
        db.query(User).filter(User.invite_code == row.code).first()
        or db.query(InviteRegistrationEvent).filter(InviteRegistrationEvent.invite_code_id == row.id).first()
        or db.query(InviteActivityDaily).filter(InviteActivityDaily.invite_code_id == row.id).first()
        or db.query(InvitePaymentEvent).filter(InvitePaymentEvent.invite_code_id == row.id).first()
    )
    if used:
        raise HTTPException(status_code=400, detail="邀请码已有归因数据，不能删除，可改为停用")
    before = _code_snapshot(row)
    _audit(db, "delete_code", "invite_code", str(row.id), current_user.username, before, {}, "delete unused code")
    db.delete(row)
    db.commit()
    return {"success": True, "message": "邀请码已删除"}


def list_invite_codes(db: Session, current_user: AuthUser, partner_id: int | None = None) -> dict:
    ensure_admin_access(current_user)
    query = db.query(InviteCode)
    if partner_id:
        query = query.filter(InviteCode.partner_id == int(partner_id))
    rows = query.order_by(InviteCode.created_at.desc(), InviteCode.id.desc()).all()
    return {"list": [_code_snapshot(row) for row in rows], "total": len(rows)}


def correct_user_invite_attribution(
    db: Session,
    current_user: AuthUser,
    username: str,
    data: InviteAttributionCorrectionRequest,
) -> dict:
    ensure_admin_access(current_user)
    reason = _clean_text(data.reason)
    if not reason:
        raise HTTPException(status_code=400, detail="修正原因不能为空")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    invite = resolve_active_invite_code(db, data.inviteCode)
    if not invite:
        raise HTTPException(status_code=400, detail="邀请码不能为空")
    before = _user_invite_snapshot(user)
    _apply_user_attribution(user, invite, "admin_correction")
    after = _user_invite_snapshot(user)
    _audit(db, "correct_user_attribution", "user", username, current_user.username, before, after, reason)
    db.commit()
    return {"success": True, "user": after}


def _parse_report_date(value: str, field: str) -> date:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field}格式应为 YYYY-MM-DD") from exc


def _empty_metrics() -> dict:
    return {
        "registrations": 0,
        "activeUsers": 0,
        "paidOrders": 0,
        "netPaidAmount": 0.0,
    }


def _metric_key(partner_id, code_id, partner_name: str, code: str) -> tuple:
    return (int(partner_id or 0), int(code_id or 0), partner_name or "", code or "")


def get_invite_report(db: Session, current_user: AuthUser, query: InviteReportQueryRequest) -> dict:
    ensure_admin_access(current_user)
    start_date = _parse_report_date(query.startDate, "开始日期")
    end_date = _parse_report_date(query.endDate, "结束日期")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")

    def apply_filters(q, model):
        if query.partnerId:
            q = q.filter(model.invite_partner_id == int(query.partnerId))
        if query.codeId:
            q = q.filter(model.invite_code_id == int(query.codeId))
        return q

    summary_map: dict[tuple, dict] = {}
    daily_map: dict[tuple, dict] = {}

    reg_q = db.query(
        InviteRegistrationEvent.registered_date.label("event_date"),
        InviteRegistrationEvent.invite_partner_id,
        InviteRegistrationEvent.invite_code_id,
        InviteRegistrationEvent.invite_partner_snapshot,
        InviteRegistrationEvent.invite_code_snapshot,
        func.count(InviteRegistrationEvent.id).label("registrations"),
    ).filter(
        InviteRegistrationEvent.registered_date >= start_date,
        InviteRegistrationEvent.registered_date <= end_date,
    )
    reg_q = apply_filters(reg_q, InviteRegistrationEvent)
    for row in reg_q.group_by(
        InviteRegistrationEvent.registered_date,
        InviteRegistrationEvent.invite_partner_id,
        InviteRegistrationEvent.invite_code_id,
        InviteRegistrationEvent.invite_partner_snapshot,
        InviteRegistrationEvent.invite_code_snapshot,
    ):
        key = _metric_key(row.invite_partner_id, row.invite_code_id, row.invite_partner_snapshot, row.invite_code_snapshot)
        summary_map.setdefault(key, _empty_metrics())["registrations"] += int(row.registrations or 0)
        dkey = (row.event_date.isoformat(), *key)
        daily_map.setdefault(dkey, _empty_metrics())["registrations"] += int(row.registrations or 0)

    active_q = db.query(
        InviteActivityDaily.active_date.label("event_date"),
        InviteActivityDaily.invite_partner_id,
        InviteActivityDaily.invite_code_id,
        InviteActivityDaily.invite_partner_snapshot,
        InviteActivityDaily.invite_code_snapshot,
        func.count(InviteActivityDaily.username).label("active_users"),
    ).filter(
        InviteActivityDaily.active_date >= start_date,
        InviteActivityDaily.active_date <= end_date,
    )
    active_q = apply_filters(active_q, InviteActivityDaily)
    for row in active_q.group_by(
        InviteActivityDaily.active_date,
        InviteActivityDaily.invite_partner_id,
        InviteActivityDaily.invite_code_id,
        InviteActivityDaily.invite_partner_snapshot,
        InviteActivityDaily.invite_code_snapshot,
    ):
        key = _metric_key(row.invite_partner_id, row.invite_code_id, row.invite_partner_snapshot, row.invite_code_snapshot)
        summary_map.setdefault(key, _empty_metrics())["activeUsers"] += int(row.active_users or 0)
        dkey = (row.event_date.isoformat(), *key)
        daily_map.setdefault(dkey, _empty_metrics())["activeUsers"] += int(row.active_users or 0)

    pay_q = db.query(
        InvitePaymentEvent.paid_date.label("event_date"),
        InvitePaymentEvent.invite_partner_id,
        InvitePaymentEvent.invite_code_id,
        InvitePaymentEvent.invite_partner_snapshot,
        InvitePaymentEvent.invite_code_snapshot,
        func.count(InvitePaymentEvent.id).label("paid_orders"),
        func.coalesce(func.sum(InvitePaymentEvent.net_amount), 0).label("net_paid_amount"),
    ).filter(
        InvitePaymentEvent.paid_date >= start_date,
        InvitePaymentEvent.paid_date <= end_date,
    )
    pay_q = apply_filters(pay_q, InvitePaymentEvent)
    for row in pay_q.group_by(
        InvitePaymentEvent.paid_date,
        InvitePaymentEvent.invite_partner_id,
        InvitePaymentEvent.invite_code_id,
        InvitePaymentEvent.invite_partner_snapshot,
        InvitePaymentEvent.invite_code_snapshot,
    ):
        key = _metric_key(row.invite_partner_id, row.invite_code_id, row.invite_partner_snapshot, row.invite_code_snapshot)
        summary = summary_map.setdefault(key, _empty_metrics())
        summary["paidOrders"] += int(row.paid_orders or 0)
        summary["netPaidAmount"] += float(row.net_paid_amount or 0)
        dkey = (row.event_date.isoformat(), *key)
        daily = daily_map.setdefault(dkey, _empty_metrics())
        daily["paidOrders"] += int(row.paid_orders or 0)
        daily["netPaidAmount"] += float(row.net_paid_amount or 0)

    def serialize_summary(item):
        partner_id, code_id, partner_name, code = item[0]
        metrics = item[1]
        return {
            "partnerId": partner_id or None,
            "codeId": code_id or None,
            "partnerName": partner_name,
            "code": code,
            **{
                "registrations": int(metrics["registrations"]),
                "activeUsers": int(metrics["activeUsers"]),
                "paidOrders": int(metrics["paidOrders"]),
                "netPaidAmount": round(float(metrics["netPaidAmount"]), 2),
            },
        }

    def serialize_daily(item):
        event_date, partner_id, code_id, partner_name, code = item[0]
        metrics = item[1]
        return {
            "date": event_date,
            "partnerId": partner_id or None,
            "codeId": code_id or None,
            "partnerName": partner_name,
            "code": code,
            "registrations": int(metrics["registrations"]),
            "activeUsers": int(metrics["activeUsers"]),
            "paidOrders": int(metrics["paidOrders"]),
            "netPaidAmount": round(float(metrics["netPaidAmount"]), 2),
        }

    summary_rows = [serialize_summary(item) for item in sorted(summary_map.items(), key=lambda item: (item[0][2], item[0][3]))]
    daily_rows = [serialize_daily(item) for item in sorted(daily_map.items(), key=lambda item: (item[0][0], item[0][3]))]
    totals = _empty_metrics()
    for row in summary_rows:
        totals["registrations"] += row["registrations"]
        totals["activeUsers"] += row["activeUsers"]
        totals["paidOrders"] += row["paidOrders"]
        totals["netPaidAmount"] += row["netPaidAmount"]
    totals["netPaidAmount"] = round(float(totals["netPaidAmount"]), 2)
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "summary": summary_rows,
        "daily": daily_rows,
        "totals": totals,
    }


def get_invite_report_csv(db: Session, current_user: AuthUser, query: InviteReportQueryRequest) -> str:
    report = get_invite_report(db, current_user, query)
    lines = ["date,partnerName,code,registrations,activeUsers,paidOrders,netPaidAmount"]

    def esc(value) -> str:
        text = str(value if value is not None else "")
        text = text.replace('"', '""')
        return f'"{text}"'

    for row in report["daily"]:
        lines.append(",".join([
            esc(row["date"]),
            esc(row["partnerName"]),
            esc(row["code"]),
            str(row["registrations"]),
            str(row["activeUsers"]),
            str(row["paidOrders"]),
            f'{float(row["netPaidAmount"]):.2f}',
        ]))
    return "\n".join(lines) + "\n"
