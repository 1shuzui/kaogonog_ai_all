"""FastAPI 应用入口。

这个文件的职责很单纯：创建应用、注册路由、暴露健康检查接口。
如果你第一次接触 FastAPI，可以把它理解成“后端程序真正启动的地方”。
"""

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# 兼容直接执行 python app/main.py 的场景。
# 这时 Python 只会把 app/ 本身加入 sys.path，找不到顶层包名 app。
if __package__ in (None, ""):
    backend_root_str = str(BACKEND_ROOT)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)

from app.api.endpoints import interview
from app.core.config import settings
from app.core.database import init_database
from app.core.dependencies import get_question_bank


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    为什么要单独写成 create_app 函数？
    1. 方便测试时单独创建应用。
    2. 方便以后按不同环境（开发 / 测试 / 生产）扩展初始化逻辑。
    """

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="支持多模态解析、结构化评分和评分结果校验的后端引擎",
    )

    # 启动时确保数据库表存在。
    init_database()

    # 注册“面试测评”相关接口。
    # prefix 表示这组接口统一带上 /api/v1/interview 前缀。
    app.include_router(
        interview.router,
        prefix="/api/v1/interview",
        tags=["面试核心引擎"],
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        # 访问根路径时自动跳转到 Swagger 文档页面，便于本地调试。
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["系统监控"])
    async def health_check():
        # 健康检查接口常用于：
        # 1. 部署平台判断服务是否正常启动
        # 2. 运维监控查看基础状态
        # 3. 本地开发快速确认服务是否活着
        question_bank = get_question_bank()
        return {
            "status": "ok",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "question_count": question_bank.count,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 直接执行 python app/main.py 时，会通过 uvicorn 启动服务。
    # reload=True 表示代码改动后自动重启，适合开发环境，不建议生产环境打开。
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        app_dir=str(BACKEND_ROOT),
        reload_dirs=[str(BACKEND_ROOT)],
    )
