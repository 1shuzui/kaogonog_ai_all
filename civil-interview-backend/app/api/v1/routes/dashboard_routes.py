"""
管理员数据看板与用户活跃心跳路由。

管理员接口只返回聚合后的资源、用户、付费和使用数据；心跳接口开放给已登录普通用户，用于从上线后开始累计真实活跃时长。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, DashboardHeartbeatRequest
from app.services.dashboard_service import (
    get_dashboard_overview,
    get_dashboard_system,
    get_dashboard_user_detail,
    list_dashboard_users,
    record_dashboard_heartbeat,
)

router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])


@router.get("/overview")
def dashboard_overview(
    userStartDate: str = "",
    userEndDate: str = "",
    systemRange: str = "30d",
    systemStartAt: str = "",
    systemEndAt: str = "",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_overview(
        db,
        current_user,
        user_start_date=userStartDate,
        user_end_date=userEndDate,
        system_range=systemRange,
        system_start_at=systemStartAt,
        system_end_at=systemEndAt,
    )


@router.get("/system")
def dashboard_system(
    systemRange: str = "30d",
    systemStartAt: str = "",
    systemEndAt: str = "",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_system(
        db,
        current_user,
        system_range=systemRange,
        system_start_at=systemStartAt,
        system_end_at=systemEndAt,
    )


@router.get("/users")
def dashboard_users(
    keyword: str = "",
    startDate: str = "",
    endDate: str = "",
    page: int = 1,
    pageSize: int = Query(default=20, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_dashboard_users(
        db,
        current_user,
        keyword=keyword,
        start_date=startDate,
        end_date=endDate,
        page=page,
        page_size=pageSize,
    )


@router.get("/users/{username}")
def dashboard_user_detail(
    username: str,
    startDate: str = "",
    endDate: str = "",
    page: int = 1,
    pageSize: int = Query(default=20, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_user_detail(
        db,
        current_user,
        username,
        start_date=startDate,
        end_date=endDate,
        page=page,
        page_size=pageSize,
    )


@router.post("/heartbeat")
def dashboard_heartbeat(
    data: DashboardHeartbeatRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return record_dashboard_heartbeat(db, current_user, data)
