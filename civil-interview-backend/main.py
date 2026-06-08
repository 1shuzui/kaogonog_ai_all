"""
这个文件是主后端入口，负责挂路由、启动生命周期和初始化种子数据；生产服务跑起来后，外部只应该通过这里暴露的 FastAPI 应用访问。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1 import api_router

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

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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


# ── lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    """
    在 FastAPI 启动时完成建表、补字段、同步套餐和题库资产。

    这些工作放在生命周期里，是为了让第一批真实请求进来前数据库已经处于可用形态。

    @param app: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    Base.metadata.create_all(bind=engine)
    ensure_user_activity_schema()
    ensure_question_indexes()
    ensure_targeted_focus_config_schema()
    logger.info(f"Database tables ready ({settings.database_url.split(':')[0]})")
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
    yield
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


# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """
    提供给 Nginx、进程守护和人工排查的轻量探活接口。

    它不访问数据库，避免数据库短抖动时把整个 Web 进程误判成不可达。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
def root():
    """
    给直接访问后端根路径的人一个明确入口，避免空白页被误认为部署失败。

    真正的业务接口仍挂在 API 路由下，根路径只做服务说明。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return {"message": "Civil Interview API", "docs": "/docs"}


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
