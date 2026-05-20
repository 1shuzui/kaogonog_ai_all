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
    "jiangsu_a": [
        {"type": "analysis", "label": "江苏省情与公共治理", "description": "围绕省属和13市事业单位治理场景，体现政策理解与综合研判", "priority": "high"},
        {"type": "practical", "label": "综合协调与任务推进", "description": "突出跨部门协同、资源统筹和工作闭环", "priority": "high"},
        {"type": "logic", "label": "机关沟通与群众服务", "description": "兼顾同事协作、群众诉求和服务效能", "priority": "medium"},
    ],
    "jiangsu_b": [
        {"type": "analysis", "label": "社科政策理解", "description": "结合法律、经济、会计等专业背景分析公共事务", "priority": "high"},
        {"type": "legal", "label": "依法履职与规范意识", "description": "突出规则边界、程序意识和风险防控", "priority": "high"},
        {"type": "practical", "label": "专业能力落地", "description": "把专业判断转化为可执行的管理建议", "priority": "medium"},
    ],
    "jiangsu_c": [
        {"type": "analysis", "label": "技术服务公共治理", "description": "结合计算机、工程、农技等方向回应事业单位实际问题", "priority": "high"},
        {"type": "practical", "label": "项目实施与现场管理", "description": "体现流程控制、质量安全和协同推进", "priority": "high"},
        {"type": "emergency", "label": "技术风险处置", "description": "面对系统故障、工程风险或农业生产问题能快速研判", "priority": "medium"},
    ],
    "jiangsu_d": [
        {"type": "analysis", "label": "教育政策与育人理念", "description": "围绕立德树人、教育公平和校园治理展开分析", "priority": "high"},
        {"type": "logic", "label": "师生家校沟通", "description": "处理学生、家长、同事之间的沟通协调问题", "priority": "high"},
        {"type": "practical", "label": "教学活动组织", "description": "体现班级管理、活动策划和安全责任", "priority": "medium"},
    ],
    "jiangsu_e": [
        {"type": "analysis", "label": "医疗卫生公共服务", "description": "围绕基层医疗、公共卫生和健康服务能力展开", "priority": "high"},
        {"type": "logic", "label": "医患沟通与服务温度", "description": "面对患者诉求和现场矛盾体现沟通安抚能力", "priority": "high"},
        {"type": "emergency", "label": "卫生应急处置", "description": "能在突发公共卫生或医疗现场问题中快速响应", "priority": "medium"},
    ],
    "jiangsu_worker": [
        {"type": "practical", "label": "服务规范与技能保障", "description": "突出岗位技能、流程规范和服务质量", "priority": "high"},
        {"type": "logic", "label": "一线协作沟通", "description": "在保障服务中处理群众、同事和管理要求之间的关系", "priority": "medium"},
        {"type": "emergency", "label": "现场问题处置", "description": "面对设备、秩序或服务异常能及时处置", "priority": "medium"},
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
