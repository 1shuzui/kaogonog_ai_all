"""
这个文件创建数据库连接和会话工厂；服务层拿到的 db 都来自这里，所以连接池和测试兜底要在这里统一。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.entities import Base


def _resolve_database_url(raw_url: str) -> str:
    """把配置中的数据库 URL 解析成真正可用的连接串。"""

    sqlite_prefix = "sqlite:///"
    if not raw_url.startswith(sqlite_prefix):
        return raw_url

    database_path = raw_url.removeprefix(sqlite_prefix)
    resolved_path = settings.resolve_path(database_path)
    Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)
    return f"{sqlite_prefix}{resolved_path}"


DATABASE_URL = _resolve_database_url(settings.DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _upgrade_sqlite_schema() -> None:
    """对已存在的 SQLite 表做轻量增列迁移。"""

    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "evaluation_records" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("evaluation_records")
    }
    if "duration_seconds" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE evaluation_records ADD COLUMN duration_seconds FLOAT")
        )


def init_database() -> None:
    """
    初始化数据库表结构。

    旧后端核心模块支撑配置和数据库连接，注释用于标明与主后端并存的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """

    Base.metadata.create_all(bind=engine)
    _upgrade_sqlite_schema()
