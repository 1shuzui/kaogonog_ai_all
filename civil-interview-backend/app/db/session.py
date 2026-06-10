"""
SQLAlchemy 连接和会话工厂，给 FastAPI 依赖、服务层和脚本提供同一套数据库入口。

当前生产和后续本地开发都以 MySQL 为准，因此这里默认启用连接保活和连接池回收，减少长时间运行后连接失效。
代码里仍保留 SQLite 分支，是为了历史单测尚未完全迁移 MySQL 前不直接崩溃；新功能测试不要继续依赖 SQLite，
否则会绕开 MySQL 的外键、collation 和 JSON 行为，容易在服务器启动时才暴露问题。

@param: 无；数据库地址来自 `settings.database_url`。
@return: 暴露 `engine`、`SessionLocal`、`Base` 和 FastAPI 依赖 `get_db`。
@raises ImportError: SQLAlchemy 或配置模块缺失时导入失败；数据库不可达通常在首次连接时暴露。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

is_sqlite = settings.database_url.startswith("sqlite")
engine_options = {
    "connect_args": {"check_same_thread": False} if is_sqlite else {},
    "echo": False,
}

if not is_sqlite:
    engine_options.update(
        {
            "pool_pre_ping": True,
            "pool_recycle": 1800,
        }
    )

engine = create_engine(
    settings.database_url,
    **engine_options,
)

# Enable WAL mode and foreign keys for SQLite
if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    为 FastAPI 请求提供一次性数据库会话。

    路由层通过依赖注入拿到同一个会话，服务层就能复用外层事务和连接池配置。
    这里用 `finally` 关闭会话，是为了保证接口异常、支付回调异常或评分超时后也不会泄漏连接。

    @param: 无；由 FastAPI 依赖系统调用。
    @return: 逐次产出 SQLAlchemy Session，供请求处理函数使用。
    @raises: 不主动包装数据库异常，交给上层错误处理和日志记录。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
