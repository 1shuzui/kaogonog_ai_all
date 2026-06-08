"""
这个文件创建 SQLAlchemy 连接和会话；MySQL 线上运行和 SQLite 兜底测试都从这里拿同一个 SessionLocal。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    get_db 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    后端入口模块承接应用启动、路由挂载和数据库初始化，注释用于说明上线环境的启动约束。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
