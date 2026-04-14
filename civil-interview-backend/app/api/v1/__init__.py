from fastapi import APIRouter

from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.user_routes import router as user_router
from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.exam_routes import router as exam_router
from app.api.v1.routes.scoring_routes import router as scoring_router
from app.api.v1.routes.history_routes import router as history_router
from app.api.v1.routes.targeted_routes import router as targeted_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(question_router)
api_router.include_router(exam_router)
api_router.include_router(scoring_router)
api_router.include_router(history_router)
api_router.include_router(targeted_router)
