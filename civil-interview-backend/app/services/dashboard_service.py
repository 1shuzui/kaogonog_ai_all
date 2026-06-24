"""
管理员数据看板服务。

本模块集中处理系统资源采样、应用错误计数、用户活跃心跳和后台聚合统计。看板只展示运营与运维
摘要，不返回日志正文，也不把历史最后活跃时间伪造成真实活跃时长。
"""
from __future__ import annotations

import os
import shutil
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import case, distinct, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access
from app.db.session import SessionLocal
from app.models.entities import (
    PaymentOrder,
    ServerErrorEvent,
    SystemMetricSnapshot,
    UsageRecord,
    User,
    UserActivityDaily,
    UserActivitySession,
)
from app.schemas.common import AuthUser, DashboardHeartbeatRequest
from app.services.user_service import get_user_or_404

SYSTEM_RETENTION_DAYS = 30
SYSTEM_SAMPLE_SECONDS = 5 * 60
HEARTBEAT_MAX_SECONDS = 120
DEFAULT_USER_PAGE_SIZE = 20
TEST_ACCOUNT_PREFIXES = ("test", "demo", "wx_test")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _date_from_datetime(value: datetime) -> date:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.date()


def _parse_datetime(value: str | None, field: str, default: datetime | None = None) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        if default is None:
            raise HTTPException(status_code=400, detail=f"{field}不能为空")
        return default
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field}格式不正确") from exc
    return _as_naive_utc(parsed)


def _parse_date(value: str | None, field: str, default: date | None = None) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field}格式应为 YYYY-MM-DD") from exc


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max)


def _safe_page(page: int) -> int:
    return max(int(page or 1), 1)


def _safe_page_size(page_size: int) -> int:
    return min(max(int(page_size or DEFAULT_USER_PAGE_SIZE), 1), 100)


def _user_filter(query):
    query = query.filter(func.lower(User.username) != "admin")
    for prefix in TEST_ACCOUNT_PREFIXES:
        query = query.filter(~func.lower(User.username).like(f"{prefix}%"))
    return query


def _usernames_subquery(db: Session):
    return select(User.username).where(
        func.lower(User.username) != "admin",
        *[
            ~func.lower(User.username).like(f"{prefix}%")
            for prefix in TEST_ACCOUNT_PREFIXES
        ],
    )


def _active_user_filter(query, username_column):
    subquery = _usernames_subquery(query.session)
    return query.filter(username_column.in_(subquery))


def _money(value) -> float:
    return round(float(value or 0), 2)


def _seconds(value) -> int:
    return max(int(value or 0), 0)

def _iso(value: datetime | date | None) -> str:
    return value.isoformat() if value else ""


def _bucket_start(now: datetime | None = None) -> datetime:
    now = _as_naive_utc(now or _utc_now())
    epoch = int(now.replace(tzinfo=timezone.utc).timestamp())
    bucket_epoch = epoch - (epoch % SYSTEM_SAMPLE_SECONDS)
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc).replace(tzinfo=None)


def _read_cpu_percent() -> float:
    stat = Path("/proc/stat")
    if not stat.exists():
        return 0.0
    try:
        def read_cpu_stats() -> tuple[int, int]:
            parts = stat.read_text(encoding="utf-8").splitlines()[0].split()[1:]
            values = [int(item) for item in parts[:8]]
            total_value = sum(values)
            idle_value = values[3] + (values[4] if len(values) > 4 else 0)
            return total_value, idle_value

        total1, idle1 = read_cpu_stats()
        time_module.sleep(0.1)
        total2, idle2 = read_cpu_stats()
        total_delta = max(total2 - total1, 0)
        idle_delta = max(idle2 - idle1, 0)
        busy_delta = max(total_delta - idle_delta, 0)
        return round((busy_delta / total_delta) * 100, 2) if total_delta > 0 else 0.0
    except Exception:
        return 0.0


def _read_memory() -> tuple[float, int, int]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0.0, 0, 0
    values: dict[str, int] = {}
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0])
        total_kb = int(values.get("MemTotal", 0))
        available_kb = int(values.get("MemAvailable", 0))
        used_kb = max(total_kb - available_kb, 0)
        percent = round((used_kb / total_kb) * 100, 2) if total_kb > 0 else 0.0
        return percent, int(used_kb / 1024), int(total_kb / 1024)
    except Exception:
        return 0.0, 0, 0


def _read_disk() -> tuple[float, float, float]:
    try:
        usage = shutil.disk_usage("/")
        used = usage.total - usage.free
        percent = round((used / usage.total) * 100, 2) if usage.total > 0 else 0.0
        gb = 1024 ** 3
        return percent, round(used / gb, 2), round(usage.total / gb, 2)
    except Exception:
        return 0.0, 0.0, 0.0


def _read_load() -> tuple[float, float, float]:
    try:
        load = os.getloadavg()
        return round(float(load[0]), 2), round(float(load[1]), 2), round(float(load[2]), 2)
    except Exception:
        return 0.0, 0.0, 0.0


def _check_db(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis_status() -> bool:
    try:
        from app.core.redis_cache import get_redis

        client = await get_redis()
        if client is None:
            return False
        await client.ping()
        return True
    except Exception:
        return False


async def collect_system_metric_snapshot(now: datetime | None = None) -> dict:
    """
    写入一个系统资源采样快照。

    采样按 5 分钟时间桶唯一，多个 worker 或重复调用只会保留第一条，返回最新可用快照摘要。
    """
    bucket = _bucket_start(now)
    db = SessionLocal()
    try:
        existing = db.query(SystemMetricSnapshot).filter(SystemMetricSnapshot.bucket_start == bucket).first()
        if existing:
            return _serialize_system_snapshot(existing)

        memory_percent, memory_used_mb, memory_total_mb = _read_memory()
        disk_percent, disk_used_gb, disk_total_gb = _read_disk()
        load_1m, load_5m, load_15m = _read_load()
        snapshot = SystemMetricSnapshot(
            bucket_start=bucket,
            cpu_percent=_read_cpu_percent(),
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_total_mb=memory_total_mb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            load_1m=load_1m,
            load_5m=load_5m,
            load_15m=load_15m,
            backend_pid=os.getpid(),
            backend_status="running",
            db_ok=_check_db(db),
            redis_ok=await check_redis_status(),
            extra_payload={"sampleSeconds": SYSTEM_SAMPLE_SECONDS},
        )
        db.add(snapshot)
        cutoff = _as_naive_utc(_utc_now()) - timedelta(days=SYSTEM_RETENTION_DAYS)
        db.query(SystemMetricSnapshot).filter(SystemMetricSnapshot.bucket_start < cutoff).delete(synchronize_session=False)
        db.commit()
        db.refresh(snapshot)
        return _serialize_system_snapshot(snapshot)
    except IntegrityError:
        db.rollback()
        row = db.query(SystemMetricSnapshot).filter(SystemMetricSnapshot.bucket_start == bucket).first()
        return _serialize_system_snapshot(row) if row else {}
    finally:
        db.close()


def record_server_error_event(
    status_code: int = 500,
    method: str = "",
    path: str = "",
    request_id: str = "",
    error_type: str = "",
) -> None:
    db = SessionLocal()
    try:
        db.add(ServerErrorEvent(
            status_code=max(int(status_code or 500), 0),
            method=str(method or "")[:10],
            path=str(path or "")[:255],
            request_id=str(request_id or "")[:80],
            error_type=str(error_type or "")[:120],
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _serialize_system_snapshot(row: SystemMetricSnapshot | None) -> dict:
    if not row:
        return {}
    return {
        "id": int(row.id or 0),
        "bucketStart": _iso(row.bucket_start),
        "cpuPercent": round(float(row.cpu_percent or 0), 2),
        "memoryPercent": round(float(row.memory_percent or 0), 2),
        "memoryUsedMb": int(row.memory_used_mb or 0),
        "memoryTotalMb": int(row.memory_total_mb or 0),
        "diskPercent": round(float(row.disk_percent or 0), 2),
        "diskUsedGb": round(float(row.disk_used_gb or 0), 2),
        "diskTotalGb": round(float(row.disk_total_gb or 0), 2),
        "load1m": round(float(row.load_1m or 0), 2),
        "load5m": round(float(row.load_5m or 0), 2),
        "load15m": round(float(row.load_15m or 0), 2),
        "backendPid": int(row.backend_pid or 0),
        "backendStatus": row.backend_status or "",
        "dbOk": bool(row.db_ok),
        "redisOk": bool(row.redis_ok),
        "createdAt": _iso(row.created_at),
    }


def _parse_system_range(system_range: str = "", start_at: str = "", end_at: str = "") -> tuple[datetime, datetime, str]:
    now = _as_naive_utc(_utc_now())
    if start_at or end_at:
        start = _parse_datetime(start_at, "系统开始时间", now - timedelta(days=SYSTEM_RETENTION_DAYS))
        end = _parse_datetime(end_at, "系统结束时间", now)
        range_key = "custom"
    else:
        raw = str(system_range or "30d").strip().lower()
        ranges = {
            "1h": timedelta(hours=1),
            "3h": timedelta(hours=3),
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = ranges.get(raw, ranges["30d"])
        end = now
        start = end - delta
        range_key = raw if raw in ranges else "30d"
    retention_start = now - timedelta(days=SYSTEM_RETENTION_DAYS)
    if start < retention_start:
        start = retention_start
    if end < start:
        raise HTTPException(status_code=400, detail="系统结束时间不能早于开始时间")
    return start, min(end, now), range_key


def _parse_user_range(start_date: str = "", end_date: str = "") -> tuple[date | None, date | None, datetime | None, datetime | None]:
    start = _parse_date(start_date, "用户开始日期")
    end = _parse_date(end_date, "用户结束日期")
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="用户结束日期不能早于开始日期")
    return start, end, _start_of_day(start) if start else None, _end_of_day(end) if end else None


def _date_series(start_date: date | None, end_date: date | None, fallback_days: int = 7) -> list[date]:
    if not start_date or not end_date:
        end_date = _date_from_datetime(_utc_now())
        start_date = end_date - timedelta(days=fallback_days - 1)
    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def _filter_datetime(query, column, start_dt: datetime | None, end_dt: datetime | None):
    if start_dt:
        query = query.filter(column >= start_dt)
    if end_dt:
        query = query.filter(column <= end_dt)
    return query


def _filter_date(query, column, start_date: date | None, end_date: date | None):
    if start_date:
        query = query.filter(column >= start_date)
    if end_date:
        query = query.filter(column <= end_date)
    return query


def _payment_refunded_amount_expr():
    return case(
        (
            PaymentOrder.status == "refunded",
            PaymentOrder.amount,
        ),
        else_=0,
    )


def _payment_net_amount_expr():
    return case(
        (
            PaymentOrder.status == "paid",
            PaymentOrder.amount,
        ),
        else_=0,
    )


def _system_summary(db: Session, start: datetime, end: datetime) -> dict:
    rows = db.query(SystemMetricSnapshot).filter(
        SystemMetricSnapshot.bucket_start >= start,
        SystemMetricSnapshot.bucket_start <= end,
    ).order_by(SystemMetricSnapshot.bucket_start.asc()).all()
    latest = rows[-1] if rows else None
    error_q = db.query(
        func.count(ServerErrorEvent.id),
        func.max(ServerErrorEvent.created_at),
    ).filter(ServerErrorEvent.created_at >= start, ServerErrorEvent.created_at <= end)
    error_count, last_error_at = error_q.one()
    return {
        "latest": _serialize_system_snapshot(latest),
        "snapshots": [_serialize_system_snapshot(row) for row in rows],
        "errorCount": int(error_count or 0),
        "lastErrorAt": _iso(last_error_at),
        "range": {"startAt": _iso(start), "endAt": _iso(end)},
    }


def _usage_summary(db: Session, start_dt: datetime | None, end_dt: datetime | None) -> dict:
    usernames = _usernames_subquery(db)
    q = db.query(
        func.count(UsageRecord.id),
        func.coalesce(func.sum(UsageRecord.usage_seconds), 0),
        func.coalesce(func.sum(UsageRecord.billed_minutes), 0),
        func.count(distinct(UsageRecord.username)),
    ).filter(UsageRecord.username.in_(usernames))
    q = _filter_datetime(q, UsageRecord.reported_at, start_dt, end_dt)
    record_count, usage_seconds, billed_minutes, users = q.one()
    return {
        "records": int(record_count or 0),
        "usageSeconds": int(usage_seconds or 0),
        "usageMinutes": round(float(usage_seconds or 0) / 60, 2),
        "billedMinutes": int(billed_minutes or 0),
        "users": int(users or 0),
    }


def _payment_summary(db: Session, start_dt: datetime | None, end_dt: datetime | None) -> dict:
    usernames = _usernames_subquery(db)
    q = db.query(
        func.count(PaymentOrder.id),
        func.coalesce(func.sum(case((PaymentOrder.status == "paid", 1), else_=0)), 0),
        func.coalesce(func.sum(case((PaymentOrder.status == "refunded", 1), else_=0)), 0),
        func.coalesce(func.sum(PaymentOrder.amount), 0),
        func.coalesce(func.sum(_payment_net_amount_expr()), 0),
        func.coalesce(func.sum(_payment_refunded_amount_expr()), 0),
        func.count(distinct(PaymentOrder.username)),
    ).filter(PaymentOrder.username.in_(usernames))
    q = _filter_datetime(q, PaymentOrder.created_at, start_dt, end_dt)
    total, paid_orders, refunded_orders, gross, net, refunded, pay_users = q.one()
    return {
        "orders": int(total or 0),
        "paidOrders": int(paid_orders or 0),
        "refundedOrders": int(refunded_orders or 0),
        "grossAmount": _money(gross),
        "netAmount": _money(net),
        "refundedAmount": _money(refunded),
        "payingUsers": int(pay_users or 0),
    }


def _user_summary(db: Session, start_date: date | None, end_date: date | None, start_dt: datetime | None, end_dt: datetime | None) -> dict:
    base = _user_filter(db.query(User))
    total_users = base.count()
    registered_q = _filter_datetime(_user_filter(db.query(User)), User.registered_at, start_dt, end_dt)
    active_q = db.query(func.count(distinct(UserActivityDaily.username)))
    active_q = _filter_date(active_q, UserActivityDaily.active_date, start_date, end_date)
    active_q = active_q.filter(UserActivityDaily.username.in_(_usernames_subquery(db)))
    active_seconds_q = db.query(func.coalesce(func.sum(UserActivityDaily.active_seconds), 0)).filter(
        UserActivityDaily.username.in_(_usernames_subquery(db))
    )
    active_seconds_q = _filter_date(active_seconds_q, UserActivityDaily.active_date, start_date, end_date)
    return {
        "totalUsers": int(total_users or 0),
        "registrations": int(registered_q.count() or 0),
        "activeUsers": int(active_q.scalar() or 0),
        "activeSeconds": int(active_seconds_q.scalar() or 0),
    }


def _trend_rows(db: Session, start_date: date | None, end_date: date | None) -> list[dict]:
    days = _date_series(start_date, end_date, fallback_days=7)
    rows = {
        day.isoformat(): {
            "date": day.isoformat(),
            "registrations": 0,
            "activeUsers": 0,
            "activeSeconds": 0,
            "usageSeconds": 0,
            "usageRecords": 0,
            "paidOrders": 0,
            "netAmount": 0.0,
        }
        for day in days
    }
    usernames = _usernames_subquery(db)
    start_day, end_day = days[0], days[-1]
    for event_date, count in db.query(
        func.date(User.registered_at),
        func.count(User.id),
    ).filter(
        User.username.in_(usernames),
        User.registered_at >= _start_of_day(start_day),
        User.registered_at <= _end_of_day(end_day),
    ).group_by(func.date(User.registered_at)):
        key = event_date.isoformat() if hasattr(event_date, "isoformat") else str(event_date)
        if key in rows:
            rows[key]["registrations"] = int(count or 0)

    for row in db.query(
        UserActivityDaily.active_date,
        func.count(distinct(UserActivityDaily.username)),
        func.coalesce(func.sum(UserActivityDaily.active_seconds), 0),
    ).filter(
        UserActivityDaily.username.in_(usernames),
        UserActivityDaily.active_date >= start_day,
        UserActivityDaily.active_date <= end_day,
    ).group_by(UserActivityDaily.active_date):
        key = row[0].isoformat()
        if key in rows:
            rows[key]["activeUsers"] = int(row[1] or 0)
            rows[key]["activeSeconds"] = int(row[2] or 0)

    for row in db.query(
        func.date(UsageRecord.reported_at),
        func.count(UsageRecord.id),
        func.coalesce(func.sum(UsageRecord.usage_seconds), 0),
    ).filter(
        UsageRecord.username.in_(usernames),
        UsageRecord.reported_at >= _start_of_day(start_day),
        UsageRecord.reported_at <= _end_of_day(end_day),
    ).group_by(func.date(UsageRecord.reported_at)):
        key = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        if key in rows:
            rows[key]["usageRecords"] = int(row[1] or 0)
            rows[key]["usageSeconds"] = int(row[2] or 0)

    for row in db.query(
        func.date(PaymentOrder.created_at),
        func.coalesce(func.sum(case((PaymentOrder.status == "paid", 1), else_=0)), 0),
        func.coalesce(func.sum(_payment_net_amount_expr()), 0),
    ).filter(
        PaymentOrder.username.in_(usernames),
        PaymentOrder.created_at >= _start_of_day(start_day),
        PaymentOrder.created_at <= _end_of_day(end_day),
    ).group_by(func.date(PaymentOrder.created_at)):
        key = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        if key in rows:
            rows[key]["paidOrders"] = int(row[1] or 0)
            rows[key]["netAmount"] = _money(row[2])
    return list(rows.values())


def get_dashboard_overview(
    db: Session,
    current_user: AuthUser,
    user_start_date: str = "",
    user_end_date: str = "",
    system_range: str = "30d",
    system_start_at: str = "",
    system_end_at: str = "",
) -> dict:
    ensure_admin_access(current_user)
    user_start, user_end, user_start_dt, user_end_dt = _parse_user_range(user_start_date, user_end_date)
    system_start, system_end, parsed_range = _parse_system_range(system_range, system_start_at, system_end_at)
    users = _user_summary(db, user_start, user_end, user_start_dt, user_end_dt)
    payments = _payment_summary(db, user_start_dt, user_end_dt)
    usage = _usage_summary(db, user_start_dt, user_end_dt)
    conversion_rate = round((payments["payingUsers"] / users["registrations"]) * 100, 2) if users["registrations"] else 0.0
    return {
        "system": _system_summary(db, system_start, system_end),
        "users": users,
        "payments": {**payments, "conversionRate": conversion_rate},
        "usage": usage,
        "trend": _trend_rows(db, user_start, user_end),
        "userRange": {
            "startDate": user_start.isoformat() if user_start else "",
            "endDate": user_end.isoformat() if user_end else "",
        },
        "systemRange": {
            "range": parsed_range,
            "startAt": _iso(system_start),
            "endAt": _iso(system_end),
        },
    }


def get_dashboard_system(
    db: Session,
    current_user: AuthUser,
    system_range: str = "30d",
    system_start_at: str = "",
    system_end_at: str = "",
) -> dict:
    ensure_admin_access(current_user)
    start, end, parsed_range = _parse_system_range(system_range, system_start_at, system_end_at)
    return {**_system_summary(db, start, end), "rangeKey": parsed_range}


def list_dashboard_users(
    db: Session,
    current_user: AuthUser,
    keyword: str = "",
    start_date: str = "",
    end_date: str = "",
    page: int = 1,
    page_size: int = DEFAULT_USER_PAGE_SIZE,
) -> dict:
    ensure_admin_access(current_user)
    start, end, start_dt, end_dt = _parse_user_range(start_date, end_date)
    safe_page = _safe_page(page)
    safe_page_size = _safe_page_size(page_size)
    query = _user_filter(db.query(User))
    raw_keyword = str(keyword or "").strip()
    if raw_keyword:
        pattern = f"%{raw_keyword}%"
        query = query.filter(or_(User.username.like(pattern), User.full_name.like(pattern), User.email.like(pattern)))
    query = _filter_datetime(query, User.registered_at, start_dt, end_dt)
    total = query.count()
    users = query.order_by(User.last_active_at.desc(), User.id.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    usernames = [item.username for item in users]
    usage_map = {}
    if usernames:
        uq = db.query(
            UsageRecord.username,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.usage_seconds), 0),
            func.coalesce(func.sum(UsageRecord.billed_minutes), 0),
        ).filter(UsageRecord.username.in_(usernames))
        uq = _filter_datetime(uq, UsageRecord.reported_at, start_dt, end_dt)
        for row in uq.group_by(UsageRecord.username):
            usage_map[row[0]] = {"records": int(row[1] or 0), "usageSeconds": int(row[2] or 0), "billedMinutes": int(row[3] or 0)}

    active_map = {}
    if usernames:
        aq = db.query(
            UserActivityDaily.username,
            func.coalesce(func.sum(UserActivityDaily.active_seconds), 0),
            func.count(UserActivityDaily.active_date),
        ).filter(UserActivityDaily.username.in_(usernames))
        aq = _filter_date(aq, UserActivityDaily.active_date, start, end)
        for row in aq.group_by(UserActivityDaily.username):
            active_map[row[0]] = {"activeSeconds": int(row[1] or 0), "activeDays": int(row[2] or 0)}

    pay_map = {}
    if usernames:
        pq = db.query(
            PaymentOrder.username,
            func.coalesce(func.sum(case((PaymentOrder.status == "paid", 1), else_=0)), 0),
            func.coalesce(func.sum(_payment_net_amount_expr()), 0),
        ).filter(PaymentOrder.username.in_(usernames))
        pq = _filter_datetime(pq, PaymentOrder.created_at, start_dt, end_dt)
        for row in pq.group_by(PaymentOrder.username):
            pay_map[row[0]] = {"paidOrders": int(row[1] or 0), "netAmount": _money(row[2])}

    rows = []
    for user in users:
        usage = usage_map.get(user.username, {"records": 0, "usageSeconds": 0, "billedMinutes": 0})
        active = active_map.get(user.username, {"activeSeconds": 0, "activeDays": 0})
        payment = pay_map.get(user.username, {"paidOrders": 0, "netAmount": 0.0})
        rows.append({
            "username": user.username,
            "fullName": user.full_name or "",
            "email": user.email or "",
            "province": user.province or "",
            "registeredAt": _iso(user.registered_at),
            "lastLoginAt": _iso(user.last_login_at),
            "lastActiveAt": _iso(user.last_active_at),
            **usage,
            **active,
            **payment,
        })
    return {"list": rows, "total": total, "page": safe_page, "pageSize": safe_page_size}


def get_dashboard_user_detail(
    db: Session,
    current_user: AuthUser,
    username: str,
    start_date: str = "",
    end_date: str = "",
    page: int = 1,
    page_size: int = DEFAULT_USER_PAGE_SIZE,
) -> dict:
    ensure_admin_access(current_user)
    user = get_user_or_404(db, username)
    start, end, start_dt, end_dt = _parse_user_range(start_date, end_date)
    uq = db.query(
        func.count(UsageRecord.id),
        func.coalesce(func.sum(UsageRecord.usage_seconds), 0),
        func.coalesce(func.sum(UsageRecord.billed_minutes), 0),
    ).filter(UsageRecord.username == username)
    uq = _filter_datetime(uq, UsageRecord.reported_at, start_dt, end_dt)
    usage_count, usage_seconds, billed_minutes = uq.one()
    aq = db.query(
        func.coalesce(func.sum(UserActivityDaily.active_seconds), 0),
        func.count(UserActivityDaily.active_date),
    ).filter(UserActivityDaily.username == username)
    aq = _filter_date(aq, UserActivityDaily.active_date, start, end)
    active_seconds, active_days = aq.one()
    pq = db.query(
        func.count(PaymentOrder.id),
        func.coalesce(func.sum(case((PaymentOrder.status == "paid", 1), else_=0)), 0),
        func.coalesce(func.sum(case((PaymentOrder.status == "refunded", 1), else_=0)), 0),
        func.coalesce(func.sum(PaymentOrder.amount), 0),
        func.coalesce(func.sum(_payment_net_amount_expr()), 0),
        func.coalesce(func.sum(_payment_refunded_amount_expr()), 0),
    ).filter(PaymentOrder.username == username)
    pq = _filter_datetime(pq, PaymentOrder.created_at, start_dt, end_dt)
    orders, paid_orders, refunded_orders, gross, net, refunded = pq.one()
    safe_page = _safe_page(page)
    safe_page_size = _safe_page_size(page_size)
    record_query = db.query(UsageRecord).filter(UsageRecord.username == username)
    record_query = _filter_datetime(record_query, UsageRecord.reported_at, start_dt, end_dt)
    total_records = record_query.count()
    usage_records = record_query.order_by(UsageRecord.reported_at.desc(), UsageRecord.id.desc()).offset(
        (safe_page - 1) * safe_page_size
    ).limit(safe_page_size).all()
    daily_usage = []
    duq = db.query(
        func.date(UsageRecord.reported_at),
        func.count(UsageRecord.id),
        func.coalesce(func.sum(UsageRecord.usage_seconds), 0),
        func.coalesce(func.sum(UsageRecord.billed_minutes), 0),
    ).filter(UsageRecord.username == username)
    duq = _filter_datetime(duq, UsageRecord.reported_at, start_dt, end_dt)
    usage_by_day = {
        (row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])): {
            "date": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            "usageRecords": int(row[1] or 0),
            "usageSeconds": int(row[2] or 0),
            "billedMinutes": int(row[3] or 0),
            "activeSeconds": 0,
            "heartbeatCount": 0,
        }
        for row in duq.group_by(func.date(UsageRecord.reported_at))
    }
    adq = db.query(UserActivityDaily).filter(UserActivityDaily.username == username)
    adq = _filter_date(adq, UserActivityDaily.active_date, start, end)
    for row in adq.order_by(UserActivityDaily.active_date.asc()).all():
        key = row.active_date.isoformat()
        usage_by_day.setdefault(key, {
            "date": key,
            "usageRecords": 0,
            "usageSeconds": 0,
            "billedMinutes": 0,
            "activeSeconds": 0,
            "heartbeatCount": 0,
        })
        usage_by_day[key]["activeSeconds"] = int(row.active_seconds or 0)
        usage_by_day[key]["heartbeatCount"] = int(row.heartbeat_count or 0)
    daily_usage = [usage_by_day[key] for key in sorted(usage_by_day)]
    return {
        "user": {
            "username": user.username,
            "fullName": user.full_name or "",
            "email": user.email or "",
            "province": user.province or "",
            "registeredAt": _iso(user.registered_at),
            "createdAt": _iso(user.created_at),
            "lastLoginAt": _iso(user.last_login_at),
            "lastActiveAt": _iso(user.last_active_at),
        },
        "summary": {
            "usageRecords": int(usage_count or 0),
            "usageSeconds": int(usage_seconds or 0),
            "usageMinutes": round(float(usage_seconds or 0) / 60, 2),
            "billedMinutes": int(billed_minutes or 0),
            "activeSeconds": int(active_seconds or 0),
            "activeDays": int(active_days or 0),
            "orders": int(orders or 0),
            "paidOrders": int(paid_orders or 0),
            "refundedOrders": int(refunded_orders or 0),
            "grossAmount": _money(gross),
            "netAmount": _money(net),
            "refundedAmount": _money(refunded),
        },
        "daily": daily_usage,
        "usageRecords": {
            "list": [
                {
                    "id": int(record.id or 0),
                    "examId": record.exam_id,
                    "questionId": record.question_id or "",
                    "usageType": record.usage_type or "",
                    "usageSeconds": int(record.usage_seconds or 0),
                    "billedMinutes": int(record.billed_minutes or 0),
                    "reportedAt": _iso(record.reported_at),
                    "createdAt": _iso(record.created_at),
                }
                for record in usage_records
            ],
            "total": total_records,
            "page": safe_page,
            "pageSize": safe_page_size,
        },
    }


def record_dashboard_heartbeat(db: Session, current_user: AuthUser, data: DashboardHeartbeatRequest) -> dict:
    user = get_user_or_404(db, current_user.username)
    event_id = str(data.eventId or "").strip()[:80]
    session_id = str(data.sessionId or "").strip()[:80]
    if not event_id or not session_id:
        raise HTTPException(status_code=400, detail="心跳缺少会话或事件标识")
    existing = db.query(UserActivitySession).filter(UserActivitySession.event_id == event_id).first()
    if existing:
        return {"success": True, "duplicate": True}
    active_at = _parse_datetime(data.activeAt, "活跃时间", _as_naive_utc(_utc_now()))
    duration = min(max(int(data.durationSeconds or 0), 0), HEARTBEAT_MAX_SECONDS)
    client_type = str(data.clientType or "pc").strip().lower()[:30] or "pc"
    route_path = str(data.routePath or "")[:255]
    active_date = _date_from_datetime(active_at.replace(tzinfo=timezone.utc))
    event = UserActivitySession(
        event_id=event_id,
        username=user.username,
        session_id=session_id,
        client_type=client_type,
        route_path=route_path,
        duration_seconds=duration,
        active_at=active_at,
        active_date=active_date,
    )
    db.add(event)
    daily = db.query(UserActivityDaily).filter(
        UserActivityDaily.username == user.username,
        UserActivityDaily.active_date == active_date,
    ).first()
    if not daily:
        daily = UserActivityDaily(
            username=user.username,
            active_date=active_date,
            active_seconds=0,
            heartbeat_count=0,
            client_types=[],
        )
        db.add(daily)
    clients = list(daily.client_types) if isinstance(daily.client_types, list) else []
    if client_type not in clients:
        clients.append(client_type)
    daily.active_seconds = int(daily.active_seconds or 0) + duration
    daily.heartbeat_count = int(daily.heartbeat_count or 0) + 1
    daily.last_active_at = active_at
    daily.client_types = clients
    user.last_active_at = active_at
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"success": True, "duplicate": True}
    return {
        "success": True,
        "duplicate": False,
        "activeSeconds": daily.active_seconds,
        "activeDate": active_date.isoformat(),
    }
