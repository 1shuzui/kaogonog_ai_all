"""
定向备面路由，提供多层级分类树、真实题库重点分析、管理员发布重点和定向/专项训练抽题。

这里承载了题库分类重构后的核心口径：真实考试体系、地区来源、岗位方向、系统单位、面试形式和题型维度必须分开；
银行、医疗、法检可以是展示入口，但不能抢掉题目的真实来源。重点分析只能来自真实题库统计或管理员发布内容，
没有匹配题库时返回明确空态，不能用其他地区或通用模板伪装。

@param: FastAPI 注入定向选择参数、管理员配置请求、当前用户和数据库 Session。
@return: 返回分类树、重点分析、管理员配置、训练题或生成题结果。
@raises HTTPException: 未登录、非管理员、参数缺失、题库不足或目标配置不存在时返回 HTTP 错误。
"""
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.access import ensure_admin_access, ensure_paid_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Question, TargetedFocusConfig
from app.schemas.common import AuthUser, FocusAnalysisRequest, GenerateQuestionsRequest, TrainingGenerateRequest
from app.services.question_labels import PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES
from app.services.targeted_catalog import POSITIONS, TARGETED_POSITION_TREE
from app.services.question_filters import apply_target_filters, question_matches_position, question_meta
from app.services.question_service import (
    generate_questions_by_position,
    generate_training_questions,
    sync_curated_question_assets,
)

router = APIRouter(tags=["targeted_training"])


FOCUS_MIN_QUESTION_COUNT = 1
ABILITY_DIMENSION_LABELS = {
    "analysis": "综合分析",
    "practical": "实务落地",
    "emergency": "应急应变",
    "legal": "行政思维",
    "logic": "逻辑结构",
    "expression": "语言表达",
}
ABILITY_DIMENSION_KEYS_BY_LABEL = {label: key for key, label in ABILITY_DIMENSION_LABELS.items()}
ABILITY_DIMENSION_ALIASES = {
    "法治思维": "行政思维",
    "职业认知": "行政思维",
    "岗位认知": "行政思维",
    "组织管理": "实务落地",
    "人际沟通": "逻辑结构",
    "人际关系": "逻辑结构",
    "情景模拟": "语言表达",
    "现场模拟": "语言表达",
}
QUESTION_TYPE_LABELS = {"综合分析", "组织管理", "应急应变", "人际沟通", "情景模拟", "岗位认知"}
QUESTION_TYPE_ALIASES = {
    "analysis": "综合分析",
    "practical": "组织管理",
    "organization": "组织管理",
    "emergency": "应急应变",
    "adaptability": "应急应变",
    "logic": "人际沟通",
    "interpersonal": "人际沟通",
    "expression": "情景模拟",
    "simulation": "情景模拟",
    "legal": "岗位认知",
    "career": "岗位认知",
    "实务落地": "组织管理",
    "逻辑结构": "人际沟通",
    "语言表达": "情景模拟",
    "现场模拟": "情景模拟",
    "行政思维": "岗位认知",
    "法治思维": "岗位认知",
    "职业认知": "岗位认知",
    "人际关系": "人际沟通",
}
QUESTION_TYPE_KEYWORDS = (
    ("组织管理", ("组织", "计划", "调研", "宣传", "活动", "接待", "推进", "落实", "协调")),
    ("应急应变", ("应急", "突发", "危机", "舆情", "处置", "投诉", "冲突")),
    ("人际沟通", ("人际", "沟通", "劝导", "同事", "领导", "群众", "关系")),
    ("情景模拟", ("情景模拟", "现场模拟", "模拟", "演讲", "发言", "串词", "宣讲")),
    ("岗位认知", ("职业认知", "岗位认知", "自我认知", "报考动机", "价值观", "岗位匹配")),
    ("综合分析", ("综合分析", "社会现象", "政策理解", "观点", "漫画", "寓言", "名言", "现象", "分析")),
)
FOCUS_TARGET_FIELDS = (
    "targetCode",
    "province",
    "position",
    "examCategory", "examTrack", "portalTag", "positionType", "city", "district", "areaLevel", "system",
    "examSubcategory",
    "subcategory",
    "subcategory2",
    "year",
    "targetName",
    "interviewFormat",
    "timingMode",
    "questionCount",
    "prepTime",
    "answerTime",
)


def parse_timing_format(text: str) -> tuple[int | None, int | None]:
    """
    解析真实套题时间模式。

    定向分类里会出现“8+12”“15分钟包干”“5+5/15分钟包干”等中文时间表达；这里把可确定的读题/答题时间转为秒，原文不明确时保持兜底，避免端侧自行猜。

    @param timing: 原始时间模式文本。
    @return: (prepTime, answerTime) 秒数元组；无法拆分时返回包干或默认值。
    @raises: 不主动抛业务异常；无法识别时按兜底规则返回。
    """
    if not text:
        return None, None
    text = text.strip()
    # "8+12" → prep=480s, answer=720s
    m = re.fullmatch(r"(\d+)\+(\d+)", text)
    if m:
        return int(m.group(1)) * 60, int(m.group(2)) * 60
    # "15分钟包干" / "20分钟作答" → prep=0, answer=N*60
    m = re.search(r"(\d+)\s*分钟\s*(?:包干|作答|答题)", text)
    if m:
        return 0, int(m.group(1)) * 60
    return None, None


def _dimension_label(code: str) -> str:
    return ABILITY_DIMENSION_LABELS.get(code, code or "综合分析")


def _normalize_ability_dimension(value: str | None) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        return "analysis", "综合分析"
    if text in ABILITY_DIMENSION_LABELS:
        return text, ABILITY_DIMENSION_LABELS[text]
    normalized = ABILITY_DIMENSION_ALIASES.get(text, text)
    if normalized in ABILITY_DIMENSION_KEYS_BY_LABEL:
        return ABILITY_DIMENSION_KEYS_BY_LABEL[normalized], normalized
    return "analysis", "综合分析"


def _normalize_question_type_label(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "综合分析"
    text = text.split("·", 1)[0].strip()
    return QUESTION_TYPE_ALIASES.get(text, text if text in QUESTION_TYPE_LABELS else "综合分析")


def _infer_question_type_label(text: str) -> str:
    haystack = str(text or "")
    for label, keywords in QUESTION_TYPE_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "综合分析"


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
    raw_label = (
        str(meta.get("questionTypeCategory") or "").strip()
        or str(meta.get("questionType") or "").split("·", 1)[0].strip()
    )
    return _normalize_question_type_label(raw_label) if raw_label else _infer_question_type_label(question.stem)


def _target_filters_from_request(data: FocusAnalysisRequest | GenerateQuestionsRequest) -> dict:
    filters = {}
    for key in ("examCategory", "examTrack", "examSubcategory", "subcategory", "subcategory2", "city", "district", "areaLevel", "system"):
        value = str(getattr(data, key, "") or "").strip()
        if value:
            filters[key] = value
    for key in ("portalTag", "displayPortal", "positionTag", "positionType"):
        value = str(getattr(data, key, "") or "").strip()
        if value:
            filters[key] = value
    position_tags = getattr(data, "positionTags", None)
    if isinstance(position_tags, list):
        filters["positionTags"] = [str(value).strip() for value in position_tags if str(value).strip()]
    elif isinstance(position_tags, str) and position_tags.strip():
        filters["positionTags"] = position_tags.strip()
    year = getattr(data, "year", "")
    if year:
        if isinstance(year, list):
            year = [str(y).strip() for y in year if str(y).strip()]
        elif isinstance(year, str):
            year = [y.strip() for y in year.replace(",", "、").replace("，", ",").split(",") if y.strip()]
        if year:
            filters["year"] = year
    return filters


def _target_name(data: FocusAnalysisRequest | GenerateQuestionsRequest) -> str:
    return str(getattr(data, "targetName", "") or "").strip() or POSITION_NAMES.get(data.position, data.position)


def _focus_request_payload(data: FocusAnalysisRequest | dict) -> dict:
    if isinstance(data, dict):
        source = data
        get_value = source.get
    else:
        get_value = lambda key, default="": getattr(data, key, default)

    payload = {}
    for field in FOCUS_TARGET_FIELDS:
        value = get_value(field, "")
        if value is None:
            continue
        text = str(value).strip()
        if text:
            payload[field] = text
    payload["province"] = payload.get("province") or "national"
    payload["position"] = payload.get("position") or ""

    # Auto-fill prepTime/answerTime from timingMode/interviewFormat if not explicitly set
    prep_time = int(payload.get("prepTime", 0) or 0)
    answer_time = int(payload.get("answerTime", 0) or 0)
    if prep_time == 0 and answer_time == 0:
        for field in ("timingMode", "interviewFormat"):
            parsed_prep, parsed_answer = parse_timing_format(payload.get(field, ""))
            if parsed_prep is not None and parsed_answer is not None:
                payload["prepTime"] = str(parsed_prep)
                payload["answerTime"] = str(parsed_answer)
                break
    return payload


def _focus_target_key(data: FocusAnalysisRequest | dict) -> str:
    payload = _focus_request_payload(data)
    target_code = payload.get("targetCode")
    if target_code:
        return f"code:{target_code}"
    parts = [
        payload.get("province", ""),
        payload.get("position", ""),
        payload.get("examCategory", ""),
        payload.get("examSubcategory", ""),
        payload.get("subcategory", ""),
        payload.get("subcategory2", ""),
    ]
    # Preserve keys for legacy unscoped configurations; scoped units must never collide.
    if any(payload.get(field) for field in ("examTrack", "portalTag", "positionType", "city", "district", "areaLevel", "system")):
        parts += [payload.get(field, "") for field in ("examTrack", "portalTag", "positionType", "city", "district", "areaLevel", "system")]
    return "fields:" + "|".join(str(item).strip() for item in parts)


def _focus_data_from_payload(payload: dict) -> FocusAnalysisRequest:
    return FocusAnalysisRequest(**_focus_request_payload(payload))


def _clamp_int(value, default: int = 0, min_value: int = 0, max_value: int = 100) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = value.replace("，", "\n").replace(",", "\n").splitlines()
    else:
        raw_items = []
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _sanitize_focus_payload(raw: dict | None) -> dict:
    raw = raw if isinstance(raw, dict) else {}

    core_focus = []
    for item in raw.get("coreFocus") or []:
        if not isinstance(item, dict):
            continue
        dimension_key, name = _normalize_ability_dimension(item.get("dimensionKey") or item.get("name"))
        if not name:
            continue
        core_focus.append({
            "dimensionKey": dimension_key,
            "name": name,
            "weight": _clamp_int(item.get("weight"), default=20, min_value=0, max_value=100),
            "desc": str(item.get("desc") or "").strip(),
            "questionCount": _clamp_int(item.get("questionCount"), default=0, min_value=0, max_value=100000),
        })

    high_freq_types = []
    for item in raw.get("highFreqTypes") or []:
        if not isinstance(item, dict):
            continue
        type_name = _normalize_question_type_label(item.get("questionTypeKey") or item.get("type"))
        if not type_name:
            continue
        high_freq_types.append({
            "questionTypeKey": type_name,
            "type": type_name,
            "frequency": str(item.get("frequency") or "中").strip(),
            "example": str(item.get("example") or "").strip(),
            "questionCount": _clamp_int(item.get("questionCount"), default=0, min_value=0, max_value=100000),
        })

    focus_areas = []
    for index, item in enumerate(core_focus):
        focus_areas.append({
            "type": item.get("dimensionKey") or item["name"],
            "dimensionKey": item.get("dimensionKey", ""),
            "label": item["name"],
            "description": item["desc"],
            "priority": _priority_by_rank(index),
            "questionCount": item.get("questionCount", 0),
        })

    question_count = _clamp_int(raw.get("questionCount"), default=0, min_value=0, max_value=1000000)
    return {
        "focusAreas": focus_areas,
        "coreFocus": core_focus,
        "highFreqTypes": high_freq_types,
        "hotTopics": _string_list(raw.get("hotTopics")),
        "strategy": _string_list(raw.get("strategy")),
        "questionCount": question_count,
        "dataSource": "admin_config",
        "isFallback": False,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _merge_focus_config_response(data: FocusAnalysisRequest, config: TargetedFocusConfig) -> dict:
    payload = deepcopy(config.payload if isinstance(config.payload, dict) else {})
    payload.update({
        "province": data.province,
        "provinceName": PROVINCE_NAMES.get(data.province, data.province),
        "position": data.position,
        "positionName": _target_name(data),
        "targetCode": str(getattr(data, "targetCode", "") or config.target_code or "").strip(),
        "targetName": str(getattr(data, "targetName", "") or config.target_name or _target_name(data)).strip(),
        "dataSource": "admin_config",
        "isFallback": False,
        "updatedAt": config.updated_at.isoformat() if config.updated_at else payload.get("updatedAt"),
    })
    return payload


def _serialize_focus_config(config: TargetedFocusConfig | None) -> dict | None:
    if not config:
        return None
    return {
        "id": config.id,
        "targetKey": config.target_key,
        "targetCode": config.target_code,
        "targetName": config.target_name,
        "province": config.province,
        "position": config.position,
        "payload": config.payload or {},
        "enabled": bool(config.enabled),
        "updatedBy": config.updated_by,
        "createdAt": config.created_at.isoformat() if config.created_at else "",
        "updatedAt": config.updated_at.isoformat() if config.updated_at else "",
    }


def _load_focus_config(db: Session, data: FocusAnalysisRequest | dict) -> TargetedFocusConfig | None:
    return db.query(TargetedFocusConfig).filter(TargetedFocusConfig.target_key == _focus_target_key(data)).first()


def _collect_focus_questions(db: Session, data: FocusAnalysisRequest) -> list[Question]:
    sync_curated_question_assets(db)
    normalized_province = str(data.province or "").strip()
    query = db.query(Question)
    if normalized_province and normalized_province not in {"all", "national"}:
        query = query.filter(Question.province == normalized_province)
    elif normalized_province == "national":
        query = query.filter(Question.province == "national")
    rows = query.limit(1500).all()
    if data.position:
        rows = [question for question in rows if question_matches_position(question, data.position)]
    rows = apply_target_filters(rows, _target_filters_from_request(data))
    return rows


def _build_empty_focus_response(data: FocusAnalysisRequest) -> dict:
    province_name = PROVINCE_NAMES.get(data.province, data.province)
    position_name = _target_name(data)
    message = "暂无足够题库数据，请选择已有真实题库的考试方向后再试。"
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
    position_name = _target_name(data)
    dimension_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for question in questions:
        meta = question_meta(question.keywords)
        dimension_key, _ = _normalize_ability_dimension(question.dimension or "analysis")
        dimension_counter[dimension_key] += 1
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
            "dimensionKey": dimension,
            "name": name,
            "weight": weight,
            "desc": f"基于当前题库中 {count} 道匹配题统计，{province_name}{position_name}方向较常考{name}能力。",
            "questionCount": count,
        })

    high_freq_types = []
    for index, (type_name, count) in enumerate(type_counter.most_common(5)):
        high_freq_types.append({
            "questionTypeKey": type_name,
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
            "dimensionKey": dimension,
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
    """
    返回定向备面分类树。

    分类树体现真实考试体系和特色入口的展示关系，PC、小程序和管理员页都应复用这里，避免各端出现不同层级。

    @param: 无；分类树由后端静态结构和题库元数据共同维护。
    @return: 考试体系、动态层级标签、地区/来源、方向和时间模式信息。
    @raises: 不主动抛业务异常。
    """
    return {
        "tree": TARGETED_POSITION_TREE,
        "legacy": POSITIONS,
    }


@router.post("/targeted/focus")
async def get_focus(data: FocusAnalysisRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    生成或读取定向备面重点分析。

    普通用户优先看到管理员已发布内容；没有发布内容时只使用真实题库统计，题库不足则返回空态，不能套用其他地区模板。

    @param body: 考试体系、地区/来源、方向和可选时间模式。
    @param db: 请求级数据库会话。
    @return: 重点分析结构，包含能力重点、题型高频、热点和策略。
    @raises HTTPException: 请求体非法或服务端分析失败时抛出。
    """
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    config = _load_focus_config(db, data)
    if config and config.enabled:
        return _merge_focus_config_response(data, config)
    questions = _collect_focus_questions(db, data)
    if len(questions) < FOCUS_MIN_QUESTION_COUNT:
        return _build_empty_focus_response(data)
    return _build_real_focus_response(data, questions)


@router.get("/targeted/focus/admin")
async def get_focus_admin_config(
    targetCode: str = "",
    province: str = "national",
    position: str = "",
    examCategory: str = "",
    examTrack: str = "",
    portalTag: str = "",
    positionType: str = "",
    city: str = "",
    district: str = "",
    areaLevel: str = "",
    system: str = "",
    examSubcategory: str = "",
    subcategory: str = "",
    subcategory2: str = "",
    year: str = "",
    targetName: str = "",
    interviewFormat: str = "",
    timingMode: str = "",
    questionCount: str = "",
    prepTime: int | None = None,
    answerTime: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员读取重点分析配置的路由。

    管理员页面需要同时看到自动分析、已发布内容和可编辑字段，因此这里按目标 key 聚合配置，而不是让前端自己拼。

    @param targetCode: 可选目标编码。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 当前目标的自动分析、发布状态和编辑内容。
    @raises HTTPException: 非管理员访问时抛出 403。
    """
    ensure_admin_access(current_user)
    target_payload = {
        "targetCode": targetCode,
        "province": province,
        "position": position,
        "examCategory": examCategory,
        "examTrack": examTrack,
        "portalTag": portalTag,
        "positionType": positionType,
        "city": city,
        "district": district,
        "areaLevel": areaLevel,
        "system": system,
        "examSubcategory": examSubcategory,
        "subcategory": subcategory,
        "subcategory2": subcategory2,
        "year": year,
        "targetName": targetName,
        "interviewFormat": interviewFormat,
        "timingMode": timingMode,
        "questionCount": questionCount,
        "prepTime": prepTime,
        "answerTime": answerTime,
    }
    data = _focus_data_from_payload(target_payload)
    config = _load_focus_config(db, target_payload)
    questions = _collect_focus_questions(db, data)
    auto_payload = (
        _build_real_focus_response(data, questions)
        if len(questions) >= FOCUS_MIN_QUESTION_COUNT
        else _build_empty_focus_response(data)
    )
    current_payload = _merge_focus_config_response(data, config) if config and config.enabled else auto_payload
    return {
        "targetKey": _focus_target_key(target_payload),
        "target": _focus_request_payload(target_payload),
        "config": _serialize_focus_config(config),
        "auto": auto_payload,
        "current": current_payload,
    }


@router.put("/targeted/focus/admin")
async def save_focus_admin_config(
    body: dict,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员保存并可发布重点分析配置。

    发布内容会优先覆盖自动统计，适合题库不足或需要人工修正文案的场景；保存时仍保留目标分类字段，方便停用后回到自动分析。

    @param body: 管理员编辑后的重点分析内容和发布状态。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 保存后的配置。
    @raises HTTPException: 非管理员、字段非法或数据库写入失败时抛出。
    """
    ensure_admin_access(current_user)
    target_payload = body.get("target") if isinstance(body.get("target"), dict) else body
    target_payload = _focus_request_payload(target_payload if isinstance(target_payload, dict) else {})
    if not target_payload.get("targetCode") and not target_payload.get("examCategory") and not target_payload.get("portalTag"):
        raise HTTPException(status_code=400, detail="缺少定向入口信息")

    payload = _sanitize_focus_payload(body.get("payload") if isinstance(body.get("payload"), dict) else body.get("focus"))
    target_key = _focus_target_key(target_payload)
    config = db.query(TargetedFocusConfig).filter(TargetedFocusConfig.target_key == target_key).first()
    if not config:
        config = TargetedFocusConfig(target_key=target_key)
        db.add(config)

    config.target_code = target_payload.get("targetCode", "")
    config.target_name = target_payload.get("targetName", "")
    config.province = target_payload.get("province", "")
    config.position = target_payload.get("position", "")
    config.payload = payload
    config.enabled = bool(body.get("enabled", True))
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    return {
        "targetKey": target_key,
        "config": _serialize_focus_config(config),
        "current": _merge_focus_config_response(_focus_data_from_payload(target_payload), config),
    }


@router.post("/targeted/focus/admin/disable")
async def disable_focus_admin_config(
    body: dict,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    管理员停用已发布重点分析配置。

    停用不会删除历史配置，只让普通用户重新走自动统计或空态，便于管理员回滚误发布。

    @param body: 目标分类定位字段。
    @param current_user: 当前管理员用户。
    @param db: 请求级数据库会话。
    @return: 停用结果。
    @raises HTTPException: 非管理员或目标不存在时抛出。
    """
    ensure_admin_access(current_user)
    target_payload = body.get("target") if isinstance(body.get("target"), dict) else body
    target_payload = _focus_request_payload(target_payload if isinstance(target_payload, dict) else {})
    config = _load_focus_config(db, target_payload)
    if not config:
        return {"targetKey": _focus_target_key(target_payload), "config": None, "disabled": True}
    config.enabled = False
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    return {"targetKey": config.target_key, "config": _serialize_focus_config(config), "disabled": True}


@router.post("/targeted/generate")
async def targeted_generate(data: GenerateQuestionsRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    定向备面生成题目路由。

    生成逻辑应按真实分类筛选题库；方向为“不限”时放宽到考试体系和地区/来源，不能跨省或套用其他考试体系。

    @param body: 定向生成条件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 生成的练习题目和考试上下文。
    @raises HTTPException: 未登录、权益不足或无可用题目时抛出。
    """
    ensure_paid_access(current_user, detail="定向备考需付费开通后使用")
    questions = await generate_questions_by_position(
        db,
        data.province,
        data.position,
        data.count,
        "local",
        _target_filters_from_request(data),
    )
    return {
        "questions": questions,
        "province": data.province,
        "position": data.position,
        "sourceMode": data.sourceMode,
    }


@router.post("/training/generate")
async def training_generate(data: TrainingGenerateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    专项训练生成题目路由。

    专项训练使用题型分类，不能和考生能力维度混用；路由层只转发参数，筛题和兜底由生成逻辑处理。

    @param body: 题型、地区和数量等训练条件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 生成的专项训练题目。
    @raises HTTPException: 未登录、权益不足或无可用题目时抛出。
    """
    ensure_paid_access(current_user, detail="专项训练需付费开通后使用")
    target_filters = _target_filters_from_request(data)
    questions = await generate_training_questions(
        db,
        data.dimension,
        data.count,
        data.sourceMode,
        province=data.province or "national",
        target_filters=target_filters if target_filters else None,
    )
    return {
        "questions": questions,
        "dimension": data.dimension,
        "dimensionName": DIMENSION_NAMES.get(data.dimension, data.dimension),
        "sourceMode": data.sourceMode,
    }
