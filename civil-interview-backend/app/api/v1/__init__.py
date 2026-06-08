"""
这个包初始化文件让 `api/v1` 目录可以被稳定导入；保留它主要是为了让路由、服务或测试按包路径引用代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from fastapi import APIRouter

from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.user_routes import router as user_router
from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.exam_routes import router as exam_router
from app.api.v1.routes.history_routes import router as history_router
from app.api.v1.routes.targeted_routes import router as targeted_router
from app.api.v1.routes.subscription_routes import router as subscription_router
from app.api.v1.routes.trial_routes import router as trial_router
from app.api.v1.routes.usage_routes import router as usage_router
from app.api.v1.routes.payment_routes import router as payment_router
from app.api.v1.routes.scoring_routes import router as scoring_router
from app.api.v1.routes.support_routes import router as support_router
from app.api.v1.routes.legal_routes import router as legal_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(question_router)
api_router.include_router(exam_router)
api_router.include_router(history_router)
api_router.include_router(targeted_router)
api_router.include_router(subscription_router)
api_router.include_router(trial_router)
api_router.include_router(usage_router)
api_router.include_router(payment_router)
api_router.include_router(scoring_router)
api_router.include_router(support_router)
api_router.include_router(legal_router)
