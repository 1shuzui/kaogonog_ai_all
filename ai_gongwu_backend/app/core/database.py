"""数据库连接与建表初始化。"""

from pathlib import Path

from sqlalchemy import create_engine
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


def init_database() -> None:
    """初始化数据库表结构。"""

    Base.metadata.create_all(bind=engine)
