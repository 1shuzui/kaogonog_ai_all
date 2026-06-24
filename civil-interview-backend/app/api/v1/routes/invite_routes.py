"""
邀请码后台管理与报表路由。

路由只负责管理员鉴权、请求体解析和 CSV 响应封装；合作公司、邀请码、归因修正和报表统计规则都在 invite_service 中统一处理。
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    InviteAttributionCorrectionRequest,
    InviteCodeCreateRequest,
    InviteCodeUpdateRequest,
    InvitePartnerCreateRequest,
    InvitePartnerUpdateRequest,
    InviteReportQueryRequest,
)
from app.services.invite_service import (
    correct_user_invite_attribution,
    create_invite_code,
    create_invite_partner,
    delete_invite_code,
    delete_invite_partner,
    get_invite_report,
    get_invite_report_csv,
    list_invite_codes,
    list_invite_partners,
    update_invite_code,
    update_invite_partner,
)

router = APIRouter(prefix="/invite/admin", tags=["invite-admin"])


@router.get("/partners")
def invite_partners(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_invite_partners(db, current_user)


@router.post("/partners")
def invite_partner_create(
    data: InvitePartnerCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_invite_partner(db, current_user, data)


@router.put("/partners/{partner_id}")
def invite_partner_update(
    partner_id: int,
    data: InvitePartnerUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_invite_partner(db, current_user, partner_id, data)


@router.delete("/partners/{partner_id}")
def invite_partner_delete(
    partner_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_invite_partner(db, current_user, partner_id)


@router.get("/codes")
def invite_codes(
    partnerId: int | None = Query(default=None),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_invite_codes(db, current_user, partnerId)


@router.post("/codes")
def invite_code_create(
    data: InviteCodeCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_invite_code(db, current_user, data)


@router.put("/codes/{code_id}")
def invite_code_update(
    code_id: int,
    data: InviteCodeUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_invite_code(db, current_user, code_id, data)


@router.delete("/codes/{code_id}")
def invite_code_delete(
    code_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_invite_code(db, current_user, code_id)


@router.post("/users/{username}/correction")
def invite_user_correction(
    username: str,
    data: InviteAttributionCorrectionRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return correct_user_invite_attribution(db, current_user, username, data)


@router.post("/report")
def invite_report(
    data: InviteReportQueryRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_invite_report(db, current_user, data)


@router.post("/report.csv")
def invite_report_export(
    data: InviteReportQueryRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    csv_text = get_invite_report_csv(db, current_user, data)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="invite-report.csv"'},
    )
