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
