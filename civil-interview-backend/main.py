"""
后端生产服务入口，负责把配置、数据库、路由、静态上传目录和启动生命周期组装成同一个 FastAPI 应用。

这里会在服务启动时做三件对现网很关键的事：创建缺失的数据表、挂载所有 `/api/v1`
业务路由、同步内置题库 JSON 资产。它不是一次性迁移脚本，启动阶段只适合做幂等补齐；
涉及清库、重建或批量导入的动作必须放到专门脚本里，避免重启服务时误伤线上数据。

@param: 无；ASGI 服务器导入 `app` 后由 FastAPI 根据请求路径分发到具体路由。
@return: 暴露 `app` 供 uvicorn/systemd、本地开发和健康检查复用。
@raises ImportError: 配置、数据库驱动、路由模块或依赖包缺失时，应用导入阶段会失败。
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1 import api_router
from app.services.dashboard_service import collect_system_metric_snapshot, record_server_error_event

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def sync_subscription_package_seeds(db) -> int:
    """
    启动时同步套餐种子，避免线上手动改漏价格、时长或每日限额。

    这里只维护内置套餐定义，不处理用户订单；这样重启服务不会改动真实购买记录。

    @param db: 启动生命周期中创建的 SQLAlchemy 会话。
    @return: 实际新增或更新的套餐行数。
    @raises: 不主动包装数据库异常，提交失败会让启动日志记录 seed 同步失败。
    """
    from database_setup import SUBSCRIPTION_PACKAGE_SEEDS
    from app.models.entities import SubscriptionPackage

    synced = 0
    for code, name, package_type, price, total_minutes, daily_limit_minutes, duration_days, description in SUBSCRIPTION_PACKAGE_SEEDS:
        row = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == code).first()
        if not row:
            row = SubscriptionPackage(package_code=code)
            db.add(row)
        before = (
            row.package_name,
            row.package_type,
            float(row.price or 0),
            int(row.total_minutes or 0),
            int(row.daily_limit_minutes or 0),
            int(row.duration_days or 0),
            row.description or "",
            bool(row.is_active),
        )
        row.package_name = name
        row.package_type = package_type
        row.price = price
        row.total_minutes = total_minutes
        row.daily_limit_minutes = daily_limit_minutes
        row.duration_days = duration_days
        row.description = description
        row.is_active = True
        after = (name, package_type, float(price), total_minutes, daily_limit_minutes, duration_days, description, True)
        if before != after:
            synced += 1
    if synced:
        db.commit()
    return synced


def ensure_question_indexes() -> None:
    """
    启动时补齐题库常用索引，让省份和题型筛选不再退化成全表扫描。

    索引创建失败只记录 warning，是为了避免低权限数据库环境直接阻断服务启动。

    @param: 无；使用模块级数据库 engine 读取和创建索引。
    @return: 无返回值；缺失索引会被创建，已有索引保持不动。
    @raises: 内部捕获并记录异常，避免索引补齐失败直接阻断服务启动。
    """
    index_specs = {
        "idx_questions_province_dimension": "CREATE INDEX idx_questions_province_dimension ON questions (province, dimension)",
        "idx_questions_dimension_province": "CREATE INDEX idx_questions_dimension_province ON questions (dimension, province)",
    }
    try:
        inspector = inspect(engine)
        existing = {item.get("name") for item in inspector.get_indexes("questions")}
        missing = [(name, sql) for name, sql in index_specs.items() if name not in existing]
        if not missing:
            return
        with engine.begin() as conn:
            for name, sql in missing:
                conn.execute(text(sql))
                logger.info("Created question index: %s", name)
    except Exception as exc:
        logger.warning("Question index sync skipped: %s", exc)


def ensure_targeted_focus_config_schema() -> None:
    """
    补齐定向备面管理表的新字段，让旧数据库也能使用管理员发布的重点分析。

    这段保留 legacy target_key，是为了不丢掉早期按 province + position 保存的配置。

    @param: 无；使用模块级数据库 engine 检查现有表结构。
    @return: 无返回值；缺失列和索引会按需补齐。
    @raises: 内部捕获并记录异常，避免旧表补字段失败直接阻断服务启动。
    """
    column_specs = {
        "target_key": "ALTER TABLE targeted_focus_configs ADD COLUMN target_key VARCHAR(255) NULL",
        "target_code": "ALTER TABLE targeted_focus_configs ADD COLUMN target_code VARCHAR(100) NULL DEFAULT ''",
        "target_name": "ALTER TABLE targeted_focus_configs ADD COLUMN target_name VARCHAR(255) NULL DEFAULT ''",
        "payload": "ALTER TABLE targeted_focus_configs ADD COLUMN payload JSON NULL",
        "enabled": "ALTER TABLE targeted_focus_configs ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE",
    }
    try:
        inspector = inspect(engine)
        if not inspector.has_table("targeted_focus_configs"):
            return
        existing_columns = {item.get("name") for item in inspector.get_columns("targeted_focus_configs")}
        with engine.begin() as conn:
            for column, sql in column_specs.items():
                if column not in existing_columns:
                    conn.execute(text(sql))
                    logger.info("Added targeted focus config column: %s", column)

            refreshed = inspect(engine)
            existing_indexes = {item.get("name") for item in refreshed.get_indexes("targeted_focus_configs")}
            if "uq_tfc_target_key" not in existing_indexes:
                conn.execute(text(
                    "UPDATE targeted_focus_configs "
                    "SET target_key = CONCAT('legacy:', province, '|', position, '|', id) "
                    "WHERE target_key IS NULL OR target_key = ''"
                ))
                conn.execute(text("ALTER TABLE targeted_focus_configs MODIFY COLUMN target_key VARCHAR(255) NOT NULL"))
                conn.execute(text("CREATE UNIQUE INDEX uq_tfc_target_key ON targeted_focus_configs (target_key)"))
            if "idx_tfc_code" not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_tfc_code ON targeted_focus_configs (target_code)"))
            if "idx_tfc_enabled" not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_tfc_enabled ON targeted_focus_configs (enabled)"))
    except Exception as exc:
        logger.warning("Targeted focus config schema sync skipped: %s", exc)


def ensure_user_activity_schema() -> None:
    """
    补齐用户登录、活跃和注册时间字段，支撑日活、新用户和留存统计。

    旧用户没有 registered_at 时用 created_at 回填，避免统计面板把历史用户当成今天注册。

    @param: 无；使用模块级数据库 engine 检查 users 表。
    @return: 无返回值；缺失活跃时间字段和索引会按需补齐。
    @raises: 内部捕获并记录异常，避免统计字段补齐失败直接阻断服务启动。
    """
    column_specs = {
        "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL",
        "last_active_at": "ALTER TABLE users ADD COLUMN last_active_at DATETIME NULL",
        "registered_at": "ALTER TABLE users ADD COLUMN registered_at DATETIME NULL",
    }
    index_specs = {
        "idx_users_last_login_at": "CREATE INDEX idx_users_last_login_at ON users (last_login_at)",
        "idx_users_last_active_at": "CREATE INDEX idx_users_last_active_at ON users (last_active_at)",
        "idx_users_registered_at": "CREATE INDEX idx_users_registered_at ON users (registered_at)",
    }
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            return
        existing_columns = {item.get("name") for item in inspector.get_columns("users")}
        with engine.begin() as conn:
            for column, sql in column_specs.items():
                if column not in existing_columns:
                    conn.execute(text(sql))
                    logger.info("Added user activity column: %s", column)
            conn.execute(text("UPDATE users SET registered_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE registered_at IS NULL"))

            refreshed = inspect(engine)
            existing_indexes = {item.get("name") for item in refreshed.get_indexes("users")}
            for index_name, sql in index_specs.items():
                if index_name not in existing_indexes:
                    conn.execute(text(sql))
                    logger.info("Created user activity index: %s", index_name)
    except Exception as exc:
        logger.warning("User activity schema sync skipped: %s", exc)


def ensure_invite_schema() -> None:
    """
    补齐邀请码相关表和 users 表上的归因字段。

    新增的历史快照表只负责写入，不回写用户侧旧数据；老用户没有邀请码归因时保持空值。
    """
    column_specs = {
        "invite_code": "ALTER TABLE users ADD COLUMN invite_code VARCHAR(32) NULL DEFAULT ''",
        "invite_partner_id": "ALTER TABLE users ADD COLUMN invite_partner_id BIGINT NULL",
        "invite_bound_at": "ALTER TABLE users ADD COLUMN invite_bound_at DATETIME NULL",
        "invite_source": "ALTER TABLE users ADD COLUMN invite_source VARCHAR(40) NULL DEFAULT ''",
    }
    index_specs = {
        "idx_users_invite_code": "CREATE INDEX idx_users_invite_code ON users (invite_code)",
        "idx_users_invite_partner_id": "CREATE INDEX idx_users_invite_partner_id ON users (invite_partner_id)",
    }
    table_sqls = [
        """
        CREATE TABLE IF NOT EXISTS invite_partners (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            remark TEXT NULL,
            contact_name VARCHAR(100) NULL DEFAULT '',
            contact_phone VARCHAR(50) NULL DEFAULT '',
            contact_wechat VARCHAR(100) NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_invite_partners_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invite_codes (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            code VARCHAR(32) NOT NULL UNIQUE,
            partner_id BIGINT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            remark TEXT NULL,
            created_by VARCHAR(64) NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_invite_codes_partner FOREIGN KEY (partner_id) REFERENCES invite_partners(id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            INDEX idx_invite_codes_partner_id (partner_id),
            INDEX idx_invite_codes_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invite_registration_events (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(64) NOT NULL UNIQUE,
            registered_date DATE NOT NULL,
            invite_code_id BIGINT NULL,
            invite_partner_id BIGINT NULL,
            invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
            invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
            source VARCHAR(40) NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ire_registered_date (registered_date),
            INDEX idx_ire_invite_partner_id (invite_partner_id),
            INDEX idx_ire_invite_code_id (invite_code_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invite_activity_daily (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL,
            active_date DATE NOT NULL,
            invite_code_id BIGINT NULL,
            invite_partner_id BIGINT NULL,
            invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
            invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_iad_username_active_date (username, active_date),
            INDEX idx_iad_date_partner_code (active_date, invite_partner_id, invite_code_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invite_payment_events (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            order_no VARCHAR(100) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL,
            paid_date DATE NOT NULL,
            invite_code_id BIGINT NULL,
            invite_partner_id BIGINT NULL,
            invite_code_snapshot VARCHAR(32) NULL DEFAULT '',
            invite_partner_snapshot VARCHAR(100) NULL DEFAULT '',
            paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            refunded_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            net_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ipe_username (username),
            INDEX idx_ipe_paid_date (paid_date),
            INDEX idx_ipe_invite_partner_id (invite_partner_id),
            INDEX idx_ipe_invite_code_id (invite_code_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invite_audit_logs (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            action_type VARCHAR(50) NOT NULL,
            target_type VARCHAR(50) NOT NULL,
            target_id VARCHAR(100) NOT NULL DEFAULT '',
            operator VARCHAR(64) NOT NULL DEFAULT '',
            before_snapshot JSON NULL,
            after_snapshot JSON NULL,
            reason TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ial_action_type (action_type),
            INDEX idx_ial_target_type (target_type),
            INDEX idx_ial_operator (operator)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]
    try:
        inspector = inspect(engine)
        if inspector.has_table("users"):
            existing_columns = {item.get("name") for item in inspector.get_columns("users")}
            with engine.begin() as conn:
                for column, sql in column_specs.items():
                    if column not in existing_columns:
                        conn.execute(text(sql))
                        logger.info("Added invite user column: %s", column)
                refreshed = inspect(engine)
                existing_indexes = {item.get("name") for item in refreshed.get_indexes("users")}
                for index_name, sql in index_specs.items():
                    if index_name not in existing_indexes:
                        conn.execute(text(sql))
                        logger.info("Created invite user index: %s", index_name)
        with engine.begin() as conn:
            for sql in table_sqls:
                conn.execute(text(sql))
    except Exception as exc:
        logger.warning("Invite schema sync skipped: %s", exc)


def ensure_dashboard_schema() -> None:
    """
    补齐管理员数据看板所需的系统快照、错误计数和用户活跃心跳表。

    这些表只从本功能上线后开始积累，不回填历史活跃时长；启动补齐保持幂等，方便旧数据库平滑升级。
    """
    table_sqls = [
        """
        CREATE TABLE IF NOT EXISTS system_metric_snapshots (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            bucket_start DATETIME NOT NULL,
            cpu_percent DOUBLE NOT NULL DEFAULT 0,
            memory_percent DOUBLE NOT NULL DEFAULT 0,
            memory_used_mb INT NOT NULL DEFAULT 0,
            memory_total_mb INT NOT NULL DEFAULT 0,
            disk_percent DOUBLE NOT NULL DEFAULT 0,
            disk_used_gb DOUBLE NOT NULL DEFAULT 0,
            disk_total_gb DOUBLE NOT NULL DEFAULT 0,
            load_1m DOUBLE NOT NULL DEFAULT 0,
            load_5m DOUBLE NOT NULL DEFAULT 0,
            load_15m DOUBLE NOT NULL DEFAULT 0,
            backend_pid INT NOT NULL DEFAULT 0,
            backend_status VARCHAR(30) NOT NULL DEFAULT 'running',
            db_ok BOOLEAN NOT NULL DEFAULT FALSE,
            redis_ok BOOLEAN NOT NULL DEFAULT FALSE,
            extra_payload JSON NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_sms_bucket_start (bucket_start),
            INDEX idx_sms_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS server_error_events (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            status_code INT NOT NULL DEFAULT 500,
            method VARCHAR(10) NOT NULL DEFAULT '',
            path VARCHAR(255) NOT NULL DEFAULT '',
            request_id VARCHAR(80) NULL DEFAULT '',
            error_type VARCHAR(120) NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_see_status_code (status_code),
            INDEX idx_see_created_at (created_at),
            INDEX idx_see_created_status (created_at, status_code),
            INDEX idx_see_path_created (path, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS user_activity_sessions (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            event_id VARCHAR(80) NOT NULL,
            username VARCHAR(64) NOT NULL,
            session_id VARCHAR(80) NOT NULL DEFAULT '',
            client_type VARCHAR(30) NOT NULL DEFAULT 'pc',
            route_path VARCHAR(255) NULL DEFAULT '',
            duration_seconds INT NOT NULL DEFAULT 0,
            active_at DATETIME NOT NULL,
            active_date DATE NOT NULL,
            extra_payload JSON NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_uas_event_id (event_id),
            INDEX idx_uas_username (username),
            INDEX idx_uas_client_type (client_type),
            INDEX idx_uas_active_at (active_at),
            INDEX idx_uas_active_date (active_date),
            INDEX idx_uas_username_active (username, active_at),
            INDEX idx_uas_session (session_id),
            CONSTRAINT fk_uas_username FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS user_activity_daily (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(64) NOT NULL,
            active_date DATE NOT NULL,
            active_seconds INT NOT NULL DEFAULT 0,
            heartbeat_count INT NOT NULL DEFAULT 0,
            last_active_at DATETIME NULL,
            client_types JSON NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_uad_username_active_date (username, active_date),
            INDEX idx_uad_username (username),
            INDEX idx_uad_active_date (active_date),
            CONSTRAINT fk_uad_username FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]
    try:
        with engine.begin() as conn:
            for sql in table_sqls:
                conn.execute(text(sql))
    except Exception as exc:
        logger.warning("Dashboard schema sync skipped: %s", exc)


async def run_dashboard_metric_sampler() -> None:
    """
    后台系统资源采样循环。

    失败只记录 warning 并继续下一轮，避免临时 Redis/DB 抖动导致整个 FastAPI 生命周期退出。
    """
    while True:
        try:
            await collect_system_metric_snapshot()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Dashboard metric sampling skipped: %s", exc)
        await asyncio.sleep(5 * 60)


# ── lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    """
    在 FastAPI 启动时完成建表、补字段、同步套餐和题库资产。

    这些工作放在生命周期里，是为了让第一批真实请求进来前数据库已经处于可用形态。

    @param app: FastAPI 应用实例，由框架在生命周期阶段传入。
    @return: 异步上下文管理器；yield 前执行启动准备，yield 后关闭 Redis 连接。
    @raises: 建表失败会中断启动；种子同步失败只记录 warning，避免题库或套餐 seed 阻断主服务。
    """
    Base.metadata.create_all(bind=engine)
    ensure_user_activity_schema()
    ensure_invite_schema()
    ensure_dashboard_schema()
    ensure_question_indexes()
    ensure_targeted_focus_config_schema()
    logger.info(f"Database tables ready ({settings.database_url.split(':')[0]})")
    dashboard_sampler_task = asyncio.create_task(run_dashboard_metric_sampler())
    try:
        from seed import seed
        from app.db.session import SessionLocal
        from app.models.entities import Question
        from app.services.question_service import sync_curated_question_assets
        db = SessionLocal()
        package_sync_count = sync_subscription_package_seeds(db)
        if package_sync_count:
            logger.info("Subscription package seeds synced: %s rows", package_sync_count)
        count = db.query(Question).count()
        if count == 0:
            logger.info("Empty database, running seed...")
            seed()
            count = db.query(Question).count()
        sync_result = sync_curated_question_assets(db)
        if sync_result.get("synced") or sync_result.get("updated"):
            logger.info(
                "Curated question assets synced: +%s new, %s updated",
                sync_result.get("synced", 0),
                sync_result.get("updated", 0),
            )
        db.close()
    except Exception as e:
        logger.warning(f"Seed skipped: {e}")
    try:
        yield
    finally:
        dashboard_sampler_task.cancel()
        try:
            await dashboard_sampler_task
        except asyncio.CancelledError:
            pass
    # shutdown
    from app.core.redis_cache import close_redis
    await close_redis()


# ── app factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="公务员面试练习平台 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.middleware("http")
async def dashboard_error_event_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            record_server_error_event(
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
                request_id=request.headers.get("X-Request-ID", ""),
                error_type="http_5xx",
            )
        return response
    except Exception as exc:
        record_server_error_event(
            status_code=500,
            method=request.method,
            path=request.url.path,
            request_id=request.headers.get("X-Request-ID", ""),
            error_type=exc.__class__.__name__,
        )
        raise


# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """
    提供给 Nginx、进程守护和人工排查的轻量探活接口。

    它不访问数据库，避免数据库短抖动时把整个 Web 进程误判成不可达。

    @param: 无。
    @return: 固定的服务存活状态和版本号。
    @raises: 不主动抛业务异常。
    """
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
def root():
    """
    给直接访问后端根路径的人一个明确入口，避免空白页被误认为部署失败。

    真正的业务接口仍挂在 API 路由下，根路径只做服务说明。

    @param: 无。
    @return: 后端服务名称和文档入口提示。
    @raises: 不主动抛业务异常。
    """
    return {"message": "Civil Interview API", "docs": "/docs"}


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
