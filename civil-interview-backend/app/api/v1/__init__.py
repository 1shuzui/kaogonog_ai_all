"""
第一版业务 API 聚合模块。

当前 PC 端、小程序端和管理端都依赖 v1 路由；这个文件把认证、用户、题库、考试、评分、支付、订阅、定向备面等 router 统一挂到 api_router 上。集中聚合的目的，是让 main.py 只关心“挂载 v1”，而不用知道每条业务接口的细节。

@param: 无；这是路由聚合模块，不直接接收 HTTP 请求体。
@return: 导出 api_router，供 FastAPI 应用启动时一次性挂载全部 v1 路由。
@raises ImportError: 任一路由模块、服务依赖或 FastAPI 依赖异常时会在导入阶段失败。
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
from app.api.v1.routes.invite_routes import router as invite_router
from app.api.v1.routes.dashboard_routes import router as dashboard_router
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
api_router.include_router(invite_router)
api_router.include_router(dashboard_router)
api_router.include_router(scoring_router)
api_router.include_router(support_router)
api_router.include_router(legal_router)
