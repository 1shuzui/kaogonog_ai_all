from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.access import ensure_paid_access
from app.core.access import ensure_admin_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import (
    AuthUser,
    FocusAnalysisRequest,
    GenerateQuestionsRequest,
    TargetedFocusAdminRequest,
    TargetedFocusConfigUpdate,
    TrainingGenerateRequest,
)
from app.core.ai import PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES
from app.services.question_service import generate_questions_by_position, generate_training_questions
from app.services.targeted_focus_service import (
    analyze_focus_config,
    disable_focus_config,
    get_focus_analysis,
    get_focus_config,
    list_focus_configs,
    publish_focus_config,
    update_focus_config,
)

router = APIRouter(tags=["targeted_training"])

POSITIONS = [
    {"id": "tax", "name": "税务系统"},
    {"id": "customs", "name": "海关系统"},
    {"id": "police", "name": "公安系统"},
    {"id": "court", "name": "法院系统"},
    {"id": "procurate", "name": "检察系统"},
    {"id": "market", "name": "市场监管"},
    {"id": "general", "name": "综合管理"},
    {"id": "township", "name": "乡镇基层"},
    {"id": "finance", "name": "银保监会"},
    {"id": "diplomacy", "name": "外交系统"},
    {"id": "prison", "name": "监狱系统"},
]

@router.get("/positions")
def get_positions():
    return POSITIONS


@router.post("/targeted/focus")
async def get_focus(data: FocusAnalysisRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    return get_focus_analysis(db, data.province, data.position)


@router.get("/targeted/focus/admin")
def list_focus_admin(
    province: str = "",
    position: str = "",
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_access(current_user)
    if province and position:
        return get_focus_config(db, province, position)
    return {"list": list_focus_configs(db, province=province, position=position)}


@router.post("/targeted/focus/admin/analyze")
def analyze_focus_admin(
    data: TargetedFocusAdminRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_access(current_user)
    return analyze_focus_config(db, data.province, data.position, current_user.username)


@router.put("/targeted/focus/admin/{config_id}")
def update_focus_admin(
    config_id: int,
    data: TargetedFocusConfigUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_access(current_user)
    return update_focus_config(
        db,
        config_id,
        published_result=data.publishedResult,
        publish_mode=data.publishMode,
        is_active=data.isActive,
        username=current_user.username,
    )


@router.post("/targeted/focus/admin/{config_id}/publish")
def publish_focus_admin(
    config_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_access(current_user)
    return publish_focus_config(db, config_id, current_user.username)


@router.post("/targeted/focus/admin/{config_id}/disable")
def disable_focus_admin(
    config_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_access(current_user)
    return disable_focus_config(db, config_id, current_user.username)


@router.post("/targeted/generate")
async def targeted_generate(data: GenerateQuestionsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    questions = await generate_questions_by_position(
        db,
        data.province,
        data.position,
        data.count,
        "local",
    )
    return {
        "questions": questions,
        "province": data.province,
        "position": data.position,
        "sourceMode": data.sourceMode,
    }


@router.post("/training/generate")
async def training_generate(data: TrainingGenerateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="专项训练需付费开通后使用")
    questions = await generate_training_questions(
        db,
        data.dimension,
        data.count,
        data.sourceMode,
    )
    return {
        "questions": questions,
        "dimension": data.dimension,
        "dimensionName": DIMENSION_NAMES.get(data.dimension, data.dimension),
        "sourceMode": data.sourceMode,
    }
