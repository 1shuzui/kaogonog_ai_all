from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.access import ensure_paid_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Question
from app.schemas.common import AuthUser, FocusAnalysisRequest, GenerateQuestionsRequest, TrainingGenerateRequest
from app.core.ai import PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES
from app.services.question_service import (
    _question_matches_position,
    _question_meta_from_keywords,
    generate_questions_by_position,
    generate_training_questions,
    sync_curated_question_assets,
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
    {"id": "bank", "name": "银行招考"},
    {"id": "medical", "name": "医疗卫生"},
    {"id": "jiangsu_a", "name": "江苏A类综合管理岗"},
    {"id": "jiangsu_b", "name": "江苏B类社会科学专技岗"},
    {"id": "jiangsu_c", "name": "江苏C类自然科学专技岗"},
    {"id": "jiangsu_d", "name": "江苏D类中小学教师岗"},
    {"id": "jiangsu_e", "name": "江苏E类医疗卫生岗"},
    {"id": "jiangsu_worker", "name": "江苏工勤技能岗"},
]

FOCUS_MIN_QUESTION_COUNT = 1


def _dimension_label(code: str) -> str:
    return DIMENSION_NAMES.get(code, code or "综合分析")


def _priority_by_rank(index: int) -> str:
    return "high" if index == 0 else "medium" if index <= 2 else "low"


def _frequency_by_rank(index: int, count: int) -> str:
    if index == 0 or count >= 5:
        return "高"
    if count >= 2:
        return "中"
    return "低"


def _meta_list(meta: dict, key: str) -> list[str]:
    value = meta.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("，", "、").replace(",", "、").split("、") if item.strip()]
    return []


def _question_type_label(question: Question, meta: dict) -> str:
    return (
        str(meta.get("questionTypeCategory") or "").strip()
        or str(meta.get("questionType") or "").split("·", 1)[0].strip()
        or _dimension_label(question.dimension)
    )


def _collect_focus_questions(db: Session, province: str, position: str) -> list[Question]:
    sync_curated_question_assets(db)
    normalized_province = str(province or "").strip()
    query = db.query(Question)
    if normalized_province and normalized_province not in {"all", "national"}:
        query = query.filter(Question.province == normalized_province)
    elif normalized_province == "national":
        query = query.filter(Question.province == "national")
    rows = query.limit(1500).all()
    if position:
        rows = [question for question in rows if _question_matches_position(question, position)]
    return rows


def _build_empty_focus_response(data: FocusAnalysisRequest) -> dict:
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = POSITION_NAMES.get(data.position, data.position)
    message = "暂无足够题库数据，请管理员补充该地区/岗位真题或发布重点词条后再生成分析。"
    return {
        "province": data.province,
        "provinceName": province_name,
        "position": data.position,
        "positionName": position_name,
        "focusAreas": [],
        "coreFocus": [],
        "highFreqTypes": [],
        "hotTopics": [],
        "strategy": [message],
        "questionCount": 0,
        "dataSource": "question_bank",
        "isFallback": True,
        "emptyMessage": message,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _build_real_focus_response(data: FocusAnalysisRequest, questions: list[Question]) -> dict:
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = POSITION_NAMES.get(data.position, data.position)
    dimension_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for question in questions:
        meta = _question_meta_from_keywords(question.keywords)
        dimension_counter[question.dimension or "analysis"] += 1
        type_counter[_question_type_label(question, meta)] += 1
        source = str(meta.get("sourceDocument") or meta.get("sourceLabel") or "").strip()
        if source:
            source_counter[source] += 1
        for key in ("tags", "coreKeywords", "strongKeywords"):
            for term in _meta_list(meta, key):
                if len(term) <= 2 or term in {province_name, position_name, "全真模拟", "事业单位", "省考"}:
                    continue
                topic_counter[term] += 1

    total = max(1, len(questions))
    core_focus = []
    for index, (dimension, count) in enumerate(dimension_counter.most_common(4)):
        weight = max(10, round(count / total * 100))
        name = _dimension_label(dimension)
        core_focus.append({
            "name": name,
            "weight": weight,
            "desc": f"基于当前题库中 {count} 道匹配题统计，{province_name}{position_name}方向较常考{name}能力。",
            "questionCount": count,
        })

    high_freq_types = []
    for index, (type_name, count) in enumerate(type_counter.most_common(5)):
        high_freq_types.append({
            "type": type_name,
            "frequency": _frequency_by_rank(index, count),
            "example": f"当前匹配题库中出现 {count} 次，建议结合真实套题反复练习。",
            "questionCount": count,
        })

    hot_topics = [topic for topic, _ in topic_counter.most_common(10)]
    if not hot_topics:
        hot_topics = [name for name, _ in type_counter.most_common(5)]

    focus_areas = [
        {
            "type": dimension,
            "label": _dimension_label(dimension),
            "description": item["desc"],
            "priority": _priority_by_rank(index),
            "questionCount": item["questionCount"],
        }
        for index, (dimension, item) in enumerate(zip([key for key, _ in dimension_counter.most_common(4)], core_focus))
    ]

    top_dimension = core_focus[0]["name"] if core_focus else "综合分析"
    top_type = high_freq_types[0]["type"] if high_freq_types else "真实套题"
    strategy = [
        f"优先复盘{province_name}{position_name}方向的{top_type}题，先按真实套题题序训练，再按题型拆解。",
        f"围绕{top_dimension}建立答题框架，作答时区分考试体系、岗位场景和题型维度。",
        "练习后对照采分点检查关键词、岗位贴合度和举措落地性，避免只背通用模板。",
    ]
    if source_counter:
        strategy.append(f"当前分析主要来自 {len(source_counter)} 个题库来源；新增真题后可刷新分析。")

    return {
        "province": data.province,
        "provinceName": province_name,
        "position": data.position,
        "positionName": position_name,
        "focusAreas": focus_areas,
        "coreFocus": core_focus,
        "highFreqTypes": high_freq_types,
        "hotTopics": hot_topics,
        "strategy": strategy,
        "questionCount": len(questions),
        "dataSource": "question_bank",
        "isFallback": False,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/positions")
def get_positions():
    return POSITIONS


@router.post("/targeted/focus")
async def get_focus(data: FocusAnalysisRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    questions = _collect_focus_questions(db, data.province, data.position)
    if len(questions) < FOCUS_MIN_QUESTION_COUNT:
        return _build_empty_focus_response(data)
    return _build_real_focus_response(data, questions)


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
