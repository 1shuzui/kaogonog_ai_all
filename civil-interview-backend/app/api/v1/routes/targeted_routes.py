from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.access import ensure_paid_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, FocusAnalysisRequest, GenerateQuestionsRequest, TrainingGenerateRequest
from app.core.ai import PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES
from app.services.question_service import generate_questions_by_position, generate_training_questions

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

FOCUS_AREAS = {
    "tax": [
        {"type": "analysis", "label": "税务稽查政策理解", "description": "准确理解税法法规，合理应用", "priority": "high"},
        {"type": "practical", "label": "纳税人服务优化", "description": "提升纳税服务体验", "priority": "medium"},
        {"type": "legal", "label": "法规遵从与执法边界", "description": "严格依法办事", "priority": "high"},
    ],
    "general": [
        {"type": "analysis", "label": "政策分析", "description": "全面分析政策背景与影响", "priority": "high"},
        {"type": "practical", "label": "工作落实", "description": "将政策落到实处", "priority": "medium"},
        {"type": "emergency", "label": "应急处置", "description": "突发情况快速响应", "priority": "medium"},
    ],
    "prison": [
        {"type": "analysis", "label": "监管安全底线", "description": "围绕监狱系统安全稳定与底线思维作答", "priority": "high"},
        {"type": "practical", "label": "教育改造落地", "description": "体现教育改造、人文关怀和流程执行能力", "priority": "high"},
        {"type": "legal", "label": "依法履职意识", "description": "强调依法管理、公正执法和制度执行", "priority": "medium"},
    ],
}


@router.get("/positions")
def get_positions():
    return POSITIONS


@router.post("/targeted/focus")
async def get_focus(data: FocusAnalysisRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    focus_list = FOCUS_AREAS.get(data.position, FOCUS_AREAS["general"])
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = POSITION_NAMES.get(data.position, data.position)
    return {
        "province": data.province, "provinceName": province_name,
        "position": data.position, "positionName": position_name,
        "focusAreas": focus_list,
    }


@router.post("/targeted/generate")
async def targeted_generate(data: GenerateQuestionsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    questions = await generate_questions_by_position(
        db,
        data.province,
        data.position,
        data.count,
        data.sourceMode,
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
