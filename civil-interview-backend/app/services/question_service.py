"""
题库服务层，负责题目增删改查、后台导入清洗、年份/地区/岗位筛选、随机抽题和真实题库资产同步。

题库分类已经拆成真实考试体系、地区来源、系统/岗位、面试形式和题型维度几套概念，本文件的筛选逻辑要尽量保持这些字段不串味。
江苏事业单位、安徽省考、湖南省考等真实来源不能因为岗位词或题型关键词被挪到别的考试体系；全真模拟优先保留真实套题名、
考试日期、题号和时间规则。这里可以为用户生成可练习的题目，但不能伪造某地区“有题库重点”，重点分析应回到真实统计或管理员发布内容。

@param: 服务函数接收数据库 Session、筛选条件、题目创建/更新模型、导入文件或抽题数量。
@return: 返回题目列表、单题详情、导入结果或随机题集合，字段需兼容 PC 和小程序。
@raises HTTPException: 题目不存在、导入格式错误、权限不足或筛选参数无法解析时抛出 HTTP 错误。
"""
import base64
import copy
import hashlib
import json
import random
import re
import time
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import String, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Question
from app.schemas.common import QuestionCreate, QuestionUpdate
from app.core.ai import call_llm_api_async, PROVINCE_NAMES, POSITION_NAMES, DIMENSION_NAMES

REPO_ROOT = Path(__file__).resolve().parents[3]
CURATED_QUESTION_DIR = REPO_ROOT / "ai_gongwu_backend" / "assets" / "questions"
CURATED_SYNC_GATE_SECONDS = 60
QUESTION_PICK_CACHE_SECONDS = 45
FULL_EXAM_CACHE_SECONDS = 90
_last_curated_sync_at = 0.0
_question_pick_cache: dict[str, tuple[float, list[dict]]] = {}
_full_exam_suite_cache: dict[str, tuple[float, list[dict]]] = {}
QUESTION_SOURCE_LABELS = {
    "local_asset": "本地真题",
    "imported_file": "题库导入",
    "ai_generated": "AI生成",
    "manual": "手工录入",
    "seed": "内置示例",
}
POSITION_ALIASES = {
    "tax": ("税务", "税费", "纳税", "税收"),
    "customs": ("海关",),
    "police": ("公安", "特警", "交警", "民警", "警民"),
    "court": ("法院", "法官"),
    "procurate": ("检察", "检察院"),
    "market": ("市场监管", "市监"),
    "general": ("综合管理", "综合岗", "通用岗", "遴选"),
    "township": ("乡镇", "基层", "村", "社区"),
    "finance": ("银保监", "金融监管"),
    "diplomacy": ("外交",),
    "prison": ("监狱", "狱警"),
    "jiangsu_a": ("A类", "A 类"),
    "jiangsu_b": ("B类", "B 类"),
    "jiangsu_c": ("C类", "C 类"),
    "jiangsu_d": ("D类", "D 类"),
    "jiangsu_e": ("E类", "E 类"),
    "jiangsu_worker": ("工勤技能岗", "工勤", "技能保障", "服务规范"),
    "bank": ("银行", "农商行", "城商行", "柜面", "客户经理"),
    "medical": ("医疗", "卫生", "医师", "护理", "药师", "医技"),
}

QUESTION_TYPE_CATEGORY_RULES = (
    ("综合分析", ("综合分析", "社会现象", "政策理解", "观点", "漫画", "寓言", "名言", "现象", "分析")),
    ("组织管理", ("组织", "计划", "调研", "宣传", "活动", "接待", "工作落实", "协调", "推进")),
    ("应急应变", ("应急", "突发", "危机", "舆情", "处置", "投诉", "冲突")),
    ("人际沟通", ("人际", "沟通", "劝导", "同事", "领导", "群众", "关系")),
    ("情景模拟", ("情景模拟", "现场模拟", "模拟", "演讲", "发言", "串词", "宣讲")),
    ("岗位认知", ("职业认知", "岗位认知", "自我认知", "报考动机", "价值观", "岗位匹配")),
)

INTERVIEW_FORMAT_RULES = (
    ("结构化小组", ("结构化小组",)),
    ("结构化+追问", ("结构化+追问", "追问")),
    ("结构化+视频", ("结构化+视频", "视频题")),
    ("结构化+专业题", ("专业题", "专业知识")),
    ("结构化+专业答辩", ("专业答辩",)),
    ("结构化+病例分析", ("病例分析",)),
    ("结构化+实操考核", ("实操考核", "设备操作")),
    ("无领导小组讨论", ("无领导",)),
    ("半结构化", ("半结构化",)),
    ("结构化面试", ("结构化", "面试题")),
)

PROVINCE_SUFFIX_MUNICIPALITIES = {"北京", "上海", "天津", "重庆"}

CLASSIFICATION_META_KEYS = (
    "examCategory",
    "examSubcategory",
    "subcategory",
    "subcategory2",
    "interviewFormat",
    "questionTypeCategory",
    "jobLevel",
    "year",
    "timingMode",
    "questionCount",
    "classificationSource",
    "classificationConfidence",
    "reviewStatus",
    "reviewReason",
    "hasCompleteSuiteLevel",
    "hasAppearanceScore",
)


def _cache_key(prefix: str, payload: dict | None = None) -> str:
    """
    为短缓存生成稳定 key。

    这里用 JSON 排序再哈希，是因为筛选条件来自 PC、小程序和定向树，不同端字段顺序不应导致缓存失效。

    @param prefix: 缓存业务前缀，例如 training、targeted 或 full_suite。
    @param payload: 参与缓存区分的筛选条件。
    @return: 可直接作为内存字典 key 的短字符串。
    @raises: 不主动包装序列化异常；异常会沿调用栈暴露给调用方。
    """
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _get_cached_list(cache: dict[str, tuple[float, list[dict]]], key: str, ttl_seconds: int) -> list[dict] | None:
    """
    读取短缓存列表，并返回深拷贝避免调用方原地修改污染缓存。

    缓存只用于削掉连续点击和重复筛选的热路径压力，因此 TTL 很短；过期即删除，不做复杂失效协议。

    @param cache: 模块级短缓存字典。
    @param key: `_cache_key` 生成的缓存 key。
    @param ttl_seconds: 最大可复用秒数。
    @return: 命中时返回列表副本，未命中或过期返回 None。
    @raises: 不主动包装深拷贝异常；异常会沿调用栈暴露给调用方。
    """
    entry = cache.get(key)
    if not entry:
        return None
    cached_at, value = entry
    if time.monotonic() - cached_at > ttl_seconds:
        cache.pop(key, None)
        return None
    return copy.deepcopy(value)


def _set_cached_list(cache: dict[str, tuple[float, list[dict]]], key: str, value: list[dict], max_items: int = 128) -> None:
    """
    写入模块级短缓存，并限制条目数防止长时间运行时无界增长。

    这里没有引入 Redis，是为了先用最小改动解决小程序重复抽题慢的问题；多进程部署下每个进程各自缓存也能降低热请求压力。

    @param cache: 模块级短缓存字典。
    @param key: `_cache_key` 生成的缓存 key。
    @param value: 需要缓存的列表结果。
    @param max_items: 缓存最大条目数。
    @return: None。
    @raises: 不主动包装深拷贝异常；异常会沿调用栈暴露给调用方。
    """
    if len(cache) >= max_items:
        oldest_key = min(cache.items(), key=lambda item: item[1][0])[0]
        cache.pop(oldest_key, None)
    cache[key] = (time.monotonic(), copy.deepcopy(value))


def _normalize_stem_key(text: str | None) -> str:
    # Remove leading colons and trailing score patterns, then whitespace
    cleaned = str(text or "")
    cleaned = re.sub(r"^[：:]\s*", "", cleaned)  # strip leading fullwidth/halfwidth colon
    cleaned = re.sub(r"[（(]\s*\d+(?:\.\d+)?\s*分\s*[）)]\s*$", "", cleaned)  # strip trailing score like （32分）
    return re.sub(r"\s+", "", cleaned).strip()


def _split_tags(value) -> list[str]:
    if isinstance(value, list):
        return _unique_preserve_order([str(item).strip() for item in value if str(item).strip()])
    if isinstance(value, str):
        return _unique_preserve_order(
            [item.strip() for item in re.split(r"[、，,；;/\s]+", value) if item.strip()]
        )
    return []


def _parse_timing_format(text: str) -> tuple[int, int] | None:
    """Parse '8+12' → (480, 720) or '15分钟包干' → (0, 900). Returns None if unparseable."""
    if not text:
        return None
    text = text.strip()
    m = re.fullmatch(r"(\d+)\+(\d+)", text)
    if m:
        return int(m.group(1)) * 60, int(m.group(2)) * 60
    m = re.search(r"(\d+)\s*分钟\s*(?:包干|作答|答题)", text)
    if m:
        return 0, int(m.group(1)) * 60
    return None


def _question_meta_from_keywords(keywords: dict | None) -> dict:
    if not isinstance(keywords, dict):
        return {}
    meta = keywords.get("_meta")
    return meta if isinstance(meta, dict) else {}


def _question_source_label(source: str) -> str:
    return QUESTION_SOURCE_LABELS.get(source, source or "未知来源")


def _normalize_year_values(value) -> list[str]:
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        candidates = re.split(r"[、，,；;/\s]+", value)
    elif value in (None, ""):
        candidates = []
    else:
        candidates = [value]
    years: list[str] = []
    for item in candidates:
        match = re.search(r"(?:19|20)\d{2}", str(item or ""))
        if match and match.group(0) not in years:
            years.append(match.group(0))
    return years


def _infer_year_values(*values) -> list[str]:
    years: list[str] = []
    for value in values:
        for year in _normalize_year_values(value):
            if year not in years:
                years.append(year)
    return years


def _question_years_from_meta(meta: dict | None) -> list[str]:
    if not isinstance(meta, dict):
        return []
    date_years = _normalize_year_values(meta.get("examDate"))
    if date_years:
        return date_years
    explicit_years = _normalize_year_values(meta.get("year"))
    if explicit_years:
        return explicit_years
    for group in (
        (meta.get("examDate"),),
        (meta.get("suiteName"), meta.get("sourceTitleRaw")),
        (meta.get("sourceQuestionId"),),
        (meta.get("sourceDocument"), meta.get("originFile")),
    ):
        inferred_years = _infer_year_values(*group)
        if inferred_years:
            return inferred_years
    return []


def _first_rule_match(text: str, rules) -> str:
    for label, aliases in rules:
        if any(alias in text for alias in aliases):
            return label
    return ""


def _all_rule_matches(text: str, rules) -> list[str]:
    matches: list[str] = []
    for label, aliases in rules:
        if any(alias in text for alias in aliases) and label not in matches:
            matches.append(label)
    return matches


def _infer_subcategories(text: str, exam_category: str, province: str) -> tuple[str, str]:
    """Infer subcategory (L3) and subcategory2 (L4) from text context.

    subcategory captures city-level or system-level classification.
    subcategory2 captures district/county-level or specific unit classification.
    """
    value = re.sub(r"\s+", "", str(text or ""))
    province_name = _normalize_province_label(province)
    subcategory = ""
    subcategory2 = ""
    if province_name:
        match = re.search(
            rf"{re.escape(province_name)}(?P<subcategory>[一-鿿]{{2,12}}市)?(?P<subcategory2>[一-鿿]{{2,12}}(?:区|县|市))?",
            value,
        )
        if match:
            subcategory = match.group("subcategory") or ""
            subcategory2 = match.group("subcategory2") or ""
    if not subcategory:
        match = re.search(r"([一-鿿]{2,12}市)", value)
        subcategory = match.group(1) if match else ""
    if not subcategory2:
        match = re.search(r"([一-鿿]{2,12}(?:区|县))", value)
        subcategory2 = match.group(1) if match else ""
    return subcategory, subcategory2


def _normalize_province_label(value: str) -> str:
    province = re.sub(r"\s+", "", str(value or "").strip())
    if not province:
        return ""
    if province in PROVINCE_SUFFIX_MUNICIPALITIES or province.endswith(("省", "市", "区")):
        return province
    if province in {"内蒙古", "广西", "西藏", "宁夏", "新疆"}:
        suffix = {
            "内蒙古": "自治区",
            "广西": "壮族自治区",
            "西藏": "自治区",
            "宁夏": "回族自治区",
            "新疆": "维吾尔自治区",
        }[province]
        return f"{province}{suffix}"
    return f"{province}省"


def _province_label_from_code(value: str) -> str:
    raw = str(value or "").strip()
    if raw in PROVINCE_NAMES:
        return PROVINCE_NAMES[raw]
    return raw




def _infer_job_level(text: str) -> str:
    for label, aliases in (
        ("中央机关", ("中央", "中央国家行政机关", "中央党群机关")),
        ("省直", ("省直", "省属")),
        ("市属", ("市属", "市直")),
        ("县乡", ("县乡", "区县", "县级")),
        ("乡镇基层", ("乡镇", "基层", "村", "社区")),
    ):
        if any(alias in text for alias in aliases):
            return label
    return ""


def _infer_exam_category(text: str, province: str) -> tuple[str, str, str]:
    province_name = _normalize_province_label(province)
    if any(token in text for token in ("国考", "国家公务员", "中央国家行政机关", "中央党群机关", "海关系统", "铁路公安")):
        return "国家公务员考试", "中央/国家直属系统", "source_title"
    if "事业单位" in text:
        return "事业单位考试", province_name or province, "suite_title"
    if any(token in text for token in ("银行招考", "农商行", "城商行", "银行面试")):
        return "银行招考面试", province_name or province, "source_title"
    if any(token in text for token in ("医疗卫生", "医师岗", "护理岗", "药师岗", "医技岗")):
        return "医疗卫生面试", province_name or province, "source_title"
    if any(token in text for token in ("法检", "书记员", "法院", "检察院")):
        return "法检书记员面试", province_name or province, "source_title"
    if any(token in text for token in ("省考", "省属公务员", "省级公务员", "公务员")):
        return "省级公务员考试", province_name or province, "source_title"
    return "", province_name or province, "unresolved"


def _infer_question_type_category(question_type: str, stem: str = "") -> str:
    return _first_rule_match(f"{question_type} {stem}", QUESTION_TYPE_CATEGORY_RULES) or "综合分析"


def _infer_classification_meta(item: dict, existing: dict, source_document: str) -> dict:
    text = " ".join(
        str(value or "")
        for value in (
            existing.get("suiteName"),
            existing.get("sourceTitleRaw"),
            source_document,
            existing.get("position"),
            existing.get("batch"),
            item.get("type"),
            item.get("stem"),
            item.get("question"),
        )
    )
    province_label = _province_label_from_code(str(item.get("province") or existing.get("province") or ""))
    exam_category, exam_subcategory, classification_source = _infer_exam_category(text, province_label)
    subcategory, subcategory2 = _infer_subcategories(text, exam_category, province_label)
    question_no = existing.get("questionNo")
    question_score = existing.get("questionScore") or item.get("fullScore")
    review_reasons: list[str] = []
    if not exam_category:
        review_reasons.append("未能识别一级考试大类")
    if not existing.get("suiteName"):
        review_reasons.append("缺少真实中文套题名")
    if not question_no:
        review_reasons.append("缺少套题内题序")
    if not question_score:
        review_reasons.append("缺少单题分值")
    if not _first_rule_match(text, INTERVIEW_FORMAT_RULES):
        review_reasons.append("未明确面试形式")
    if any(token in text for token in ("国企招聘", "特岗", "定岗特选", "强村行动")):
        review_reasons.append("标题含非标准事业单位/特殊招聘表述，需人工确认分类")

    if not review_reasons:
        confidence = "high"
        review_status = "已确认"
    elif exam_category and existing.get("suiteName") and question_no:
        confidence = "medium"
        review_status = "待确认"
    else:
        confidence = "low"
        review_status = "需人工复核"

    return {
        "examCategory": exam_category,
        "examSubcategory": exam_subcategory,
        "subcategory": subcategory,
        "subcategory2": subcategory2,
        "interviewFormat": _first_rule_match(text, INTERVIEW_FORMAT_RULES),
        "questionTypeCategory": _infer_question_type_category(str(item.get("type") or existing.get("questionType") or ""), str(item.get("stem") or item.get("question") or "")),
        "jobLevel": _infer_job_level(text),
        "classificationSource": classification_source,
        "classificationConfidence": confidence,
        "reviewStatus": review_status,
        "reviewReason": "；".join(review_reasons),
        "hasCompleteSuiteLevel": bool(existing.get("suiteKey") and existing.get("suiteName") and question_no),
    }


def _infer_position_tags(*values) -> list[str]:
    haystack = " ".join(str(value or "") for value in values)
    tags: list[str] = []
    for code, aliases in POSITION_ALIASES.items():
        if any(alias in haystack for alias in aliases):
            tags.append(code)
    return tags or ["general"]


def _build_question_meta(
    item: dict,
    *,
    source_kind: str,
    source_name: str = "",
    asset_path: str = "",
    source_question_id: str = "",
) -> dict:
    tags = _split_tags(item.get("tags"))
    source_document = str(item.get("sourceDocument") or source_name or "").strip()
    origin_file = str(asset_path or source_name or "").strip()
    item_meta = item.get("_meta") if isinstance(item.get("_meta"), dict) else {}
    keyword_meta = {}
    if isinstance(item.get("keywords"), dict) and isinstance(item["keywords"].get("_meta"), dict):
        keyword_meta = item["keywords"].get("_meta") or {}

    def metadata_value(*keys: str):
        for key in keys:
            for source in (item, item_meta, keyword_meta):
                value = source.get(key) if isinstance(source, dict) else None
                if value not in ("", [], None):
                    return value
        return None

    meta = {
        "source": source_kind,
        "sourceLabel": _question_source_label(source_kind),
        "sourceDocument": source_document,
        "originFile": origin_file,
        "sourceQuestionId": source_question_id or str(item.get("id") or "").strip(),
        "tags": tags,
        "positionTags": _infer_position_tags(
            source_document,
            origin_file,
            item.get("type"),
            item.get("question"),
            item.get("stem"),
            " ".join(tags),
        ),
        "referenceAnswer": str(item.get("referenceAnswer") or "").strip(),
        "scoreBands": item.get("scoreBands") if isinstance(item.get("scoreBands"), list) else [],
        "regressionCases": item.get("regressionCases") if isinstance(item.get("regressionCases"), list) else [],
        "coreKeywords": _split_keyword_list(item.get("coreKeywords")),
        "strongKeywords": _split_keyword_list(item.get("strongKeywords")),
        "weakKeywords": _split_keyword_list(item.get("weakKeywords")),
        "bonusKeywords": _split_keyword_list(item.get("bonusKeywords")),
        "penaltyKeywords": _split_keyword_list(item.get("penaltyKeywords")),
        "questionType": str(item.get("type") or "").strip(),
        "suiteId": metadata_value("suiteId", "fullExamSuiteId"),
        "suiteKey": metadata_value("suiteKey", "fullExamSuiteKey", "suiteId"),
        "suiteName": metadata_value("suiteName", "fullExamSuiteTitle"),
        "sourceTitleRaw": metadata_value("sourceTitleRaw"),
        "examDate": metadata_value("examDate"),
        "position": metadata_value("position"),
        "batch": metadata_value("batch"),
        "questionNo": metadata_value("questionNo", "fullExamQuestionNumber"),
        "questionScore": metadata_value("questionScore", "fullScore", "questionMaxScore"),
        "answerScoreTotal": metadata_value("answerScoreTotal", "fullExamAnswerScoreTotal"),
        "appearanceScore": metadata_value("appearanceScore", "fullExamAppearanceScore"),
        "suiteTotalScore": metadata_value("suiteTotalScore", "totalScore", "fullExamTotalScore"),
        "totalScore": metadata_value("totalScore", "suiteTotalScore", "fullExamTotalScore"),
        "sourceDocumentType": metadata_value("sourceDocumentType"),
    }
    classification_meta = _infer_classification_meta(item, meta, source_document)
    for key in CLASSIFICATION_META_KEYS:
        value = metadata_value(key)
        if value in ("", [], None):
            value = classification_meta.get(key)
        if value not in ("", [], None):
            meta[key] = value
    date_years = _normalize_year_values(meta.get("examDate"))
    if date_years:
        meta["year"] = date_years
    elif not meta.get("year"):
        inferred_years = _question_years_from_meta(meta)
        if inferred_years:
            meta["year"] = inferred_years
    return {key: value for key, value in meta.items() if value not in ("", [], None)}


def _q_to_dict(q: Question) -> dict:
    payload = {
        "id": q.id,
        "stem": q.stem,
        "dimension": q.dimension,
        "province": q.province,
        "prepTime": q.prep_time,
        "answerTime": q.answer_time,
        "scoringPoints": q.scoring_points or [],
        "keywords": q.keywords or {"scoring": [], "deducting": [], "bonus": []},
    }
    meta = _question_meta_from_keywords(q.keywords)
    if meta:
        payload.update({
            "questionSource": meta.get("source", ""),
            "questionSourceLabel": meta.get("sourceLabel") or _question_source_label(meta.get("source", "")),
            "sourceDocument": meta.get("sourceDocument", ""),
            "sourceFile": meta.get("originFile", ""),
            "sourceQuestionId": meta.get("sourceQuestionId", ""),
            "positionTags": meta.get("positionTags", []),
            "tags": meta.get("tags", []),
            "hasReferenceAnswer": bool(meta.get("referenceAnswer")),
            "suiteId": meta.get("suiteId", ""),
            "suiteKey": meta.get("suiteKey", ""),
            "suiteName": meta.get("suiteName", ""),
            "sourceTitleRaw": meta.get("sourceTitleRaw", ""),
            "examDate": meta.get("examDate", ""),
            "position": meta.get("position", ""),
            "batch": meta.get("batch", ""),
            "questionNo": meta.get("questionNo"),
            "questionScore": meta.get("questionScore"),
            "fullScore": meta.get("questionScore"),
            "answerScoreTotal": meta.get("answerScoreTotal"),
            "appearanceScore": meta.get("appearanceScore"),
            "suiteTotalScore": meta.get("suiteTotalScore") or meta.get("totalScore"),
            "totalScore": meta.get("totalScore") or meta.get("suiteTotalScore"),
            "hasAppearanceScore": meta.get("hasAppearanceScore"),
            "examCategory": meta.get("examCategory", ""),
            "examSubcategory": meta.get("examSubcategory", ""),
            "subcategory": meta.get("subcategory", ""),
            "subcategory2": meta.get("subcategory2", ""),
            "interviewFormat": meta.get("interviewFormat", ""),
            "questionTypeCategory": meta.get("questionTypeCategory", ""),
            "jobLevel": meta.get("jobLevel", ""),
            "year": _question_years_from_meta(meta),
            "timingMode": meta.get("timingMode", ""),
            "questionCount": meta.get("questionCount"),
            "classificationSource": meta.get("classificationSource", ""),
            "classificationConfidence": meta.get("classificationConfidence", ""),
            "reviewStatus": meta.get("reviewStatus", ""),
            "reviewReason": meta.get("reviewReason", ""),
            "hasCompleteSuiteLevel": meta.get("hasCompleteSuiteLevel"),
        })
    return payload


def _normalize_keywords(keywords: dict | None, meta: dict | None = None) -> dict:
    base = {"scoring": [], "deducting": [], "bonus": []}
    merged_meta: dict = {}
    if isinstance(keywords, dict):
        for key in base:
            value = keywords.get(key, [])
            base[key] = value if isinstance(value, list) else []
        existing_meta = keywords.get("_meta")
        if isinstance(existing_meta, dict):
            merged_meta.update(existing_meta)
    if isinstance(meta, dict):
        merged_meta.update({key: value for key, value in meta.items() if value not in ("", [], None)})
    if merged_meta:
        base["_meta"] = merged_meta
    return base


def _question_input_meta(data) -> dict:
    """Collect optional suite/classification fields from admin import/edit payloads."""

    fields = (
        "suiteId",
        "suiteKey",
        "suiteName",
        "examDate",
        "batch",
        "position",
        "questionNo",
        "questionScore",
        "answerScoreTotal",
        "appearanceScore",
        "suiteTotalScore",
        "totalScore",
        "hasAppearanceScore",
        *CLASSIFICATION_META_KEYS,
    )
    result: dict = {}
    for field in fields:
        value = getattr(data, field, None)
        if value not in ("", [], None):
            result[field] = value
    return result


PROVINCE_CODE_BY_NAME = {name: code for code, name in PROVINCE_NAMES.items()}
PROVINCE_ALIASES = {
    "national": "national",
    "国家": "national",
    "国家公务员考试": "national",
    "国考": "national",
    "beijing": "beijing",
    "北京": "beijing",
    "guangdong": "guangdong",
    "广东": "guangdong",
    "zhejiang": "zhejiang",
    "浙江": "zhejiang",
    "sichuan": "sichuan",
    "四川": "sichuan",
    "jiangsu": "jiangsu",
    "江苏": "jiangsu",
    "anhui": "anhui",
    "安徽": "anhui",
    "安徽消防": "anhui",
    "henan": "henan",
    "河南": "henan",
    "shandong": "shandong",
    "山东": "shandong",
    "hubei": "hubei",
    "湖北": "hubei",
    "hunan": "hunan",
    "湖南": "hunan",
    "liaoning": "liaoning",
    "辽宁": "liaoning",
    "shanxi": "shanxi",
    "陕西": "shanxi",
}
DIMENSION_CODE_BY_NAME = {name: code for code, name in DIMENSION_NAMES.items()}


def _normalize_province(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "national"
    if normalized in PROVINCE_CODE_BY_NAME:
        return PROVINCE_CODE_BY_NAME[normalized]
    lowered = normalized.lower()
    return PROVINCE_ALIASES.get(lowered, PROVINCE_ALIASES.get(normalized, lowered or "national"))


def _normalize_dimension(value: str | None, question_type: str = "", stem: str = "") -> str:
    normalized = str(value or "").strip()
    if normalized in DIMENSION_NAMES:
        return normalized
    if normalized in DIMENSION_CODE_BY_NAME:
        return DIMENSION_CODE_BY_NAME[normalized]

    text = f"{normalized} {question_type} {stem}"
    if any(token in text for token in ("应急", "突发", "危机", "舆情")):
        return "emergency"
    if any(token in text for token in ("法治", "法律", "执法", "依法")):
        return "legal"
    if any(token in text for token in ("表达", "演讲", "发言", "口才")):
        return "expression"
    if any(token in text for token in ("逻辑", "论证", "结构")):
        return "logic"
    if any(token in text for token in ("组织", "策划", "沟通", "协调", "宣传", "调研", "接待", "群众工作", "人际")):
        return "practical"
    return "analysis"


def _split_keyword_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                return _split_keyword_list(parsed)
            except Exception:
                pass
        return [item.strip() for item in raw.replace("；", ",").replace("，", ",").split(",") if item.strip()]
    return []


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _normalize_scoring_points(raw_points, raw_dimensions=None, raw_criteria=None) -> list[dict]:
    points: list[dict] = []

    if isinstance(raw_points, list):
        for item in raw_points:
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("name") or "").strip()
                if content:
                    points.append({"content": content, "score": float(item.get("score") or 5)})
            elif isinstance(item, str) and item.strip():
                points.append({"content": item.strip(), "score": 5})
    if points:
        return points

    if isinstance(raw_dimensions, list):
        for item in raw_dimensions:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            points.append({"content": name, "score": float(item.get("score") or 5)})
    if points:
        return points

    if isinstance(raw_criteria, list):
        for item in raw_criteria:
            text = str(item or "").strip()
            if text:
                points.append({"content": text[:120], "score": 5})
    return points


def _normalize_question_item(
    item: dict,
    *,
    source_kind: str = "imported_file",
    source_name: str = "",
    asset_path: str = "",
) -> dict | None:
    if not isinstance(item, dict):
        return None

    stem = str(
        item.get("stem")
        or item.get("question")
        or item.get("questionText")
        or item.get("content")
        or item.get("title")
        or ""
    ).strip()
    if not stem:
        return None

    raw_keywords = item.get("keywords")
    if isinstance(raw_keywords, dict):
        keywords = {
            "scoring": _split_keyword_list(raw_keywords.get("scoring")),
            "deducting": _split_keyword_list(raw_keywords.get("deducting") or raw_keywords.get("penalty")),
            "bonus": _split_keyword_list(raw_keywords.get("bonus")),
        }
    else:
        keywords = {
            "scoring": _unique_preserve_order(
                _split_keyword_list(item.get("scoringKeywords"))
                + _split_keyword_list(item.get("coreKeywords"))
                + _split_keyword_list(item.get("strongKeywords"))
                + _split_keyword_list(item.get("weakKeywords"))
            ),
            "deducting": _unique_preserve_order(
                _split_keyword_list(item.get("deductingKeywords"))
                + _split_keyword_list(item.get("penaltyKeywords"))
            ),
            "bonus": _unique_preserve_order(_split_keyword_list(item.get("bonusKeywords"))),
        }

    source_question_id = str(item.get("id") or "").strip()
    meta = _build_question_meta(
        item,
        source_kind=source_kind,
        source_name=source_name,
        asset_path=asset_path,
        source_question_id=source_question_id,
    )

    return {
        "id": source_question_id,
        "stem": stem,
        "dimension": _normalize_dimension(item.get("dimension"), str(item.get("type") or ""), stem),
        "province": _normalize_province(item.get("province")),
        "prepTime": int(item.get("prepTime") or 90),
        "answerTime": int(item.get("answerTime") or 180),
        "scoringPoints": _normalize_scoring_points(
            item.get("scoringPoints"),
            item.get("dimensions"),
            item.get("scoringCriteria"),
        ),
        "keywords": _normalize_keywords(keywords, meta),
    }


def _normalize_json_payload(
    payload,
    *,
    source_kind: str = "imported_file",
    source_name: str = "",
    asset_path: str = "",
) -> list[dict]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("questions"), list):
            items = payload.get("questions") or []
        else:
            items = [payload]
    else:
        return []

    normalized_items: list[dict] = []
    for item in items:
        normalized = _normalize_question_item(
            item,
            source_kind=source_kind,
            source_name=source_name,
            asset_path=asset_path,
        )
        if normalized:
            normalized_items.append(normalized)
    return normalized_items


def _pick_question_id(preferred_id: str | None = "") -> str:
    candidate = str(preferred_id or "").strip()
    if candidate and not candidate.startswith(("preview_", "import_")):
        return candidate
    return f"q_{uuid.uuid4().hex[:8]}"


def _build_existing_question_indexes(db: Session) -> tuple[dict[str, Question], dict[str, Question]]:
    by_id: dict[str, Question] = {}
    by_stem: dict[str, Question] = {}
    for row in db.query(Question).all():
        by_id[row.id] = row
        stem_key = _normalize_stem_key(row.stem)
        if stem_key and stem_key not in by_stem:
            by_stem[stem_key] = row
    return by_id, by_stem


def _upsert_normalized_question(
    db: Session,
    item: dict,
    *,
    allow_update: bool = True,
    by_id: dict[str, Question] | None = None,
    by_stem: dict[str, Question] | None = None,
) -> Question:
    preferred_id = _pick_question_id(item.get("id"))
    stem_key = _normalize_stem_key(item.get("stem"))
    if by_id is not None:
        question = by_id.get(preferred_id)
    else:
        question = db.query(Question).filter(Question.id == preferred_id).first()

    if not question and stem_key:
        if by_stem is not None:
            question = by_stem.get(stem_key)
        else:
            question = next(
                (
                    row for row in db.query(Question).all()
                    if _normalize_stem_key(row.stem) == stem_key
                ),
                None,
            )

    if not question:
        question = Question(id=preferred_id)
        db.add(question)
        if by_id is not None:
            by_id[preferred_id] = question
        if by_stem is not None and stem_key:
            by_stem[stem_key] = question
    elif not allow_update:
        return question

    old_stem_key = _normalize_stem_key(question.stem)
    question.stem = item["stem"]
    question.dimension = item.get("dimension", "analysis")
    question.province = item.get("province", "national")
    question.prep_time = item.get("prepTime", 90)
    question.answer_time = item.get("answerTime", 180)
    question.scoring_points = item.get("scoringPoints", [])
    question.keywords = _normalize_keywords(item.get("keywords"))
    if by_stem is not None and old_stem_key and old_stem_key != stem_key:
        by_stem.pop(old_stem_key, None)
    if by_stem is not None and stem_key:
        by_stem[stem_key] = question
    return question


def sync_curated_question_assets(db: Session) -> dict:
    """
    将仓库内已整理的题库 JSON 资产同步到数据库。

    这个入口会被应用启动、导入、定向生成和重点分析复用，因此必须保持幂等：同一题源按 ID 或题干更新，
    不能重复插入。标准资产仍是只读题库来源，管理员编辑只应落到手工题，不应反向覆盖仓库资产文件。

    @param db: 当前请求、启动流程或导入流程复用的数据库会话。
    @return: 本次新增和更新的题目数量。
    @raises: JSON 读取、解析或数据库提交异常会沿调用栈上抛。
    """
    if not CURATED_QUESTION_DIR.exists():
        return {"synced": 0, "updated": 0}

    synced = 0
    updated = 0
    changed = False
    by_id, by_stem = _build_existing_question_indexes(db)

    for path in sorted(CURATED_QUESTION_DIR.rglob("*.json")):
        if path.name.lower() == "readme.md":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        normalized_items = _normalize_json_payload(
            payload,
            source_kind="local_asset",
            source_name=path.name,
            asset_path=str(path.relative_to(REPO_ROOT)),
        )
        for item in normalized_items:
            stem_key = _normalize_stem_key(item.get("stem"))
            existing = by_id.get(_pick_question_id(item.get("id"))) or by_stem.get(stem_key)
            if existing:
                updated += 1
            else:
                synced += 1
            _upsert_normalized_question(db, item, by_id=by_id, by_stem=by_stem)
            changed = True

    if changed:
        db.commit()
    return {"synced": synced, "updated": updated}


def _sync_curated_question_assets_if_stale(db: Session) -> dict:
    """
    给生成题目的热路径加资产同步节流。

    标准题库同步会扫本地 JSON 并比对数据库，适合启动和导入后执行；用户连续点击专项/定向生成时不应每次都触发全量扫描。
    这里保留“短时间内至少同步过一次”的保证，降低延迟，同时不改同步函数本身，避免影响导入链路。

    @param db: 当前请求复用的数据库会话。
    @return: 同步结果；节流命中时返回 skipped 标记。
    @raises: 同步函数内部异常会沿调用栈抛出。
    """
    global _last_curated_sync_at
    now = time.monotonic()
    if now - _last_curated_sync_at < CURATED_SYNC_GATE_SECONDS:
        return {"synced": 0, "updated": 0, "skipped": True}
    result = sync_curated_question_assets(db)
    _last_curated_sync_at = now
    return result


def _persist_generated_questions(
    db: Session,
    items: list[dict],
    *,
    province: str,
    default_dimension: str,
    default_scoring_points: list[dict],
    source_kind: str = "ai_generated",
    position: str = "",
) -> list[dict]:
    persisted: list[Question] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stem = str(item.get("stem", "")).strip()
        stem = re.sub(r"^[：:]\s*", "", stem)
        stem = re.sub(r"[（(]\s*\d+(?:\.\d+)?\s*分\s*[）)]\s*$", "", stem)
        if not stem:
            continue
        meta = _build_question_meta(
            item,
            source_kind=source_kind,
            source_name="",
            asset_path="",
            source_question_id=str(item.get("id") or "").strip(),
        )
        if position:
            meta["positionTags"] = _unique_preserve_order(
                list(meta.get("positionTags", [])) + [position]
            )
        question = Question(
            id=_pick_question_id(item.get("id")),
            stem=stem,
            dimension=str(item.get("dimension") or default_dimension).strip() or default_dimension,
            province=str(item.get("province") or province).strip() or province,
            prep_time=int(item.get("prepTime") or 90),
            answer_time=int(item.get("answerTime") or 180),
            scoring_points=item.get("scoringPoints") if isinstance(item.get("scoringPoints"), list) else default_scoring_points,
            keywords=_normalize_keywords(item.get("keywords"), meta),
        )
        db.add(question)
        persisted.append(question)

    if not persisted:
        return []

    db.commit()
    for question in persisted:
        db.refresh(question)
    return [_q_to_dict(question) for question in persisted]


def _build_generated_question_payloads(
    items: list[dict],
    *,
    province: str,
    default_dimension: str,
    default_scoring_points: list[dict],
    source_kind: str = "ai_generated",
    position: str = "",
) -> list[dict]:
    questions: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stem = str(item.get("stem", "")).strip()
        stem = re.sub(r"^[：:]\s*", "", stem)
        stem = re.sub(r"[（(]\s*\d+(?:\.\d+)?\s*分\s*[）)]\s*$", "", stem)
        if not stem:
            continue
        meta = _build_question_meta(
            item,
            source_kind=source_kind,
            source_name="",
            asset_path="",
            source_question_id=str(item.get("id") or "").strip(),
        )
        if position:
            meta["positionTags"] = _unique_preserve_order(
                list(meta.get("positionTags", [])) + [position]
            )
        questions.append({
            "id": f"generated_{uuid.uuid4().hex[:8]}",
            "stem": stem,
            "dimension": str(item.get("dimension") or default_dimension).strip() or default_dimension,
            "province": str(item.get("province") or province).strip() or province,
            "prepTime": int(item.get("prepTime") or 90),
            "answerTime": int(item.get("answerTime") or 180),
            "scoringPoints": item.get("scoringPoints") if isinstance(item.get("scoringPoints"), list) else default_scoring_points,
            "keywords": _normalize_keywords(item.get("keywords"), meta),
            "questionSource": source_kind,
            "questionSourceLabel": _question_source_label(source_kind),
            "positionTags": meta.get("positionTags", []),
            "tags": meta.get("tags", []),
        })
    return questions


def _question_matches_position(question: Question, position: str) -> bool:
    if not position:
        return True
    meta = _question_meta_from_keywords(question.keywords)
    position_tags = meta.get("positionTags") if isinstance(meta.get("positionTags"), list) else []
    if position in position_tags:
        return True
    exam_category = str(meta.get("examCategory") or "")
    if position == "medical" and "医疗卫生面试" in exam_category:
        return True
    if position == "bank" and "银行招考面试" in exam_category:
        return True
    if position in {"court", "procurate"} and "法检书记员面试" in exam_category:
        return True
    if position.startswith("jiangsu_") and any(str(tag).startswith("jiangsu_") for tag in position_tags):
        return False
    if position.startswith("jiangsu_"):
        return False

    haystack = " ".join(
        [
            question.stem,
            meta.get("sourceDocument", ""),
            meta.get("suiteName", ""),
            meta.get("examCategory", ""),
            meta.get("examSubcategory", ""),
            meta.get("subcategory", ""),
            meta.get("subcategory2", ""),
            meta.get("jobLevel", ""),
            " ".join(meta.get("tags", []) if isinstance(meta.get("tags"), list) else []),
            meta.get("questionType", ""),
            meta.get("questionTypeCategory", ""),
        ]
    )
    return any(alias in haystack for alias in POSITION_ALIASES.get(position, ()))


def _question_matches_target_filters(question: Question, target_filters: dict | None = None) -> bool:
    if not target_filters:
        return True
    meta = _question_meta_from_keywords(question.keywords)

    def clean(value) -> str:
        return str(value or "").strip()

    def values_match(a: str, b: str) -> bool:
        """Loose match: exact equality or one contains the other for category aliases."""
        if not a or not b:
            return True
        if a == b:
            return True
        # Bidirectional containment for alias matching (e.g. "法检书记员" contains "书记员")
        return a in b or b in a

    for field in ("examCategory", "examSubcategory", "subcategory", "subcategory2"):
        expected = clean(target_filters.get(field))
        actual = clean(meta.get(field))
        if expected and actual and not values_match(expected, actual):
            return False

    year_filter = target_filters.get("year")
    if year_filter:
        year_values = set(str(y).strip() for y in (year_filter if isinstance(year_filter, list) else [year_filter]) if str(y).strip())
        if year_values:
            meta_years = set(_question_years_from_meta(meta))
            if meta_years and not (year_values & meta_years):
                return False
    return True


def _apply_target_filters(questions: list[Question], target_filters: dict | None = None) -> list[Question]:
    if not target_filters:
        return questions
    return [question for question in questions if _question_matches_target_filters(question, target_filters)]


def _apply_position_filter(questions: list[Question], position: str) -> list[Question]:
    if not position:
        return questions
    return [question for question in questions if _question_matches_position(question, position)]


def _question_base_query(db: Session, province: str = "", dimension: str = ""):
    query = db.query(Question)
    if province and province != "all":
        query = query.filter(Question.province.in_([province, "national"]))
    if dimension:
        dimensions = [item.strip() for item in str(dimension).split(",") if item.strip()]
        if dimensions:
            query = query.filter(Question.dimension.in_(dimensions))
    return query


def _position_prefilter_query(query, position: str = ""):
    if not position:
        return query
    aliases = POSITION_ALIASES.get(position, ())
    keywords_text = Question.keywords.cast(String)
    filters = [keywords_text.contains(position)]
    if position.startswith("jiangsu_"):
        filters.append(keywords_text.contains("jiangsu_"))
    for alias in aliases:
        filters.append(Question.stem.contains(alias))
        filters.append(keywords_text.contains(alias))
    return query.filter(or_(*filters))


def _fetch_position_candidates(
    db: Session,
    *,
    province: str = "",
    dimension: str = "",
    position: str = "",
    limit: int | None = None,
) -> list[Question]:
    query = _question_base_query(db, province=province, dimension=dimension)
    prefiltered = _position_prefilter_query(query, position)
    if limit:
        prefiltered = prefiltered.limit(limit)
    rows = prefiltered.all()
    if position:
        rows = _apply_position_filter(rows, position)
    return rows


def _question_matches_province(question: Question, province: str) -> bool:
    if not province or province == "all":
        return True
    return question.province in {province, "national"}


def _question_prefers_local_source(question: Question) -> bool:
    meta = _question_meta_from_keywords(question.keywords)
    return meta.get("source") in {"local_asset", "imported_file", "manual", "seed"}


def _choose_targeted_bank_questions(
    db: Session,
    province: str,
    position: str,
    count: int,
    target_filters: dict | None = None,
) -> list[dict]:
    cache_key = _cache_key(
        "targeted_bank",
        {
            "province": province,
            "position": position,
            "count": count,
            "targetFilters": target_filters or {},
        },
    )
    cached = _get_cached_list(_question_pick_cache, cache_key, QUESTION_PICK_CACHE_SECONDS)
    if cached is not None:
        random.shuffle(cached)
        return cached[:count]

    if position:
        matched = _fetch_position_candidates(db, province=province, position=position)
    else:
        matched = _question_base_query(db, province=province).limit(max(count * 20, 200)).all()
    matched = _apply_target_filters(matched, target_filters)

    local_items = [question for question in matched if _question_prefers_local_source(question)]
    other_items = [question for question in matched if question not in local_items]

    for bucket in (local_items, other_items):
        random.shuffle(bucket)

    picked = (local_items + other_items)[:count]

    result = [
        {
            **_q_to_dict(question),
            "generationSource": "local_bank",
        }
        for question in picked[:count]
    ]
    _set_cached_list(_question_pick_cache, cache_key, result)
    return result


def _choose_training_bank_questions(
    db: Session, dimension: str, count: int,
    province: str = "national",
    target_filters: dict | None = None,
) -> list[dict]:
    cache_key = _cache_key(
        "training_bank",
        {
            "dimension": dimension,
            "count": count,
            "province": province,
            "targetFilters": target_filters or {},
        },
    )
    cached = _get_cached_list(_question_pick_cache, cache_key, QUESTION_PICK_CACHE_SECONDS)
    if cached is not None:
        random.shuffle(cached)
        return cached[:count]

    preferred = _question_base_query(db, dimension=dimension, province=province).all()
    fallback = db.query(Question).limit(max(count * 4, 50)).all() if not preferred else []
    pool = preferred or fallback
    if not pool:
        return []

    if target_filters:
        pool = _apply_target_filters(pool, target_filters)

    local_pool = [question for question in pool if _question_prefers_local_source(question)]
    other_pool = [question for question in pool if question not in local_pool]
    for bucket in (local_pool, other_pool):
        random.shuffle(bucket)

    picked = (local_pool + other_pool)[: min(count, len(pool))]
    result = [
        {
            **_q_to_dict(question),
            "dimension": dimension or question.dimension,
            "generationSource": "local_bank",
        }
        for question in picked
    ]
    _set_cached_list(_question_pick_cache, cache_key, result)
    return result


async def _generate_targeted_questions_with_llm(
    db: Session,
    province: str,
    position: str,
    count: int,
) -> list[dict]:
    province_name = PROVINCE_NAMES.get(province, province)
    position_name = POSITION_NAMES.get(position, position)
    prompt = f"""请生成{count}道更贴近"{province_name}"、"{position_name}"岗位场景的公务员结构化面试题。
每道题以JSON对象表示，放在一个JSON数组中返回。
每道题必须包含字段：
- stem: 题目内容(字符串)
- dimension: 六维之一 analysis/practical/emergency/legal/logic/expression
- scoringPoints: 采分点数组，每项含 content 和 score
- keywords: 含 scoring/deducting/bonus 三个字符串数组
要求：
- 题干尽量贴近真实公考表达，不要写成练习提示语
- 优先体现岗位职责、群众工作、依法履职、现场处置等真实场景
- 返回纯JSON数组，不要输出其他说明。"""
    result = await call_llm_api_async(
        prompt,
        system_msg="你是公务员面试命题专家，请只输出JSON数组。",
        max_tokens=3000,
    )
    if not result or not isinstance(result, list):
        return []

    generated = _build_generated_question_payloads(
        result[:count],
        province=province or "national",
        default_dimension="analysis",
        default_scoring_points=[
            {"content": f"贴合{position_name}岗位职责展开分析", "score": 10},
            {"content": "提出可执行的工作举措", "score": 10},
            {"content": "逻辑清晰、表达规范", "score": 10},
        ],
        source_kind="ai_generated",
        position=position,
    )
    return [{**item, "generationSource": "llm"} for item in generated]


def list_questions(
    db: Session,
    keyword: str = "",
    dimension: str = "",
    province: str = "",
    position: str = "",
    subcategory: str = "",
    subcategory2: str = "",
    examCategory: str = "",
    year: str = "",
    current: int = 1,
    page_size: int = 10,
) -> dict:
    """
    按题干、地区、真实考试体系、岗位方向和年份筛选题库。

    历史参数仍保留 `dimension/subcategory/subcategory2`，但筛选解释集中在服务端完成。
    这样 PC、小程序和管理员页面不会因为各自解析 `_meta` 而把“题型维度”误当成“考试分类”。

    @param db: 当前请求复用的数据库会话。
    @param keyword: 题干关键词。
    @param dimension: 训练题型维度筛选。
    @param province: 地区筛选，只表示地域。
    @param position: 岗位或方向筛选，空值表示不限。
    @param subcategory: 旧版二级分类筛选。
    @param subcategory2: 旧版三级分类筛选。
    @param examCategory: 真实考试体系筛选。
    @param year: 年份筛选，可用逗号传多个年份。
    @param current: 当前页码。
    @param page_size: 每页条数。
    @return: 分页题目列表。
    @raises: 不主动包装数据库异常，查询失败会沿调用栈上抛。
    """
    current = max(1, int(current or 1))
    page_size = max(1, min(int(page_size or 10), 1000))
    query = db.query(Question)
    if keyword:
        query = query.filter(Question.stem.contains(keyword))
    if dimension:
        query = query.filter(Question.dimension == dimension)
    if province and province != "all":
        query = query.filter(Question.province == province)
    need_meta_filter = bool(subcategory or subcategory2 or examCategory or year or position)
    if need_meta_filter:
        if position:
            rows = _apply_position_filter(_position_prefilter_query(query, position).all(), position)
        else:
            rows = query.all()
        if subcategory:
            rows = [q for q in rows if _question_meta_from_keywords(q.keywords).get("subcategory") == subcategory]
        if subcategory2:
            rows = [q for q in rows if _question_meta_from_keywords(q.keywords).get("subcategory2") == subcategory2]
        if examCategory:
            rows = [q for q in rows if _question_meta_from_keywords(q.keywords).get("examCategory") == examCategory]
        if year:
            year_set = set(str(y).strip() for y in year.split(",") if str(y).strip())
            if year_set:
                rows = [
                    q for q in rows
                    if year_set & set(_question_years_from_meta(_question_meta_from_keywords(q.keywords)))
                ]
        total = len(rows)
        start = (current - 1) * page_size
        rows = rows[start:start + page_size]
    else:
        total = query.count()
        rows = query.offset((current - 1) * page_size).limit(page_size).all()
    return {
        "list": [_q_to_dict(q) for q in rows],
        "total": total,
        "current": current,
        "pageSize": page_size,
    }


def get_random_questions(db: Session, province: str = "national", count: int = 5, dimension: str = "", position: str = "") -> List[dict]:
    """
    从题库中随机抽取练习题。

    随机抽题在服务端完成，是为了避免前端拿到过大的题库列表，也避免“方向不限”时各端随机规则不一致。
    当指定岗位方向时先做预筛再随机，保证定向练习不会被无关题目稀释。

    @param db: 当前请求复用的数据库会话。
    @param province: 地区筛选。
    @param count: 请求题量，服务端会限制最大值。
    @param dimension: 训练题型维度筛选。
    @param position: 岗位或方向筛选，空值表示不限。
    @return: 随机题目列表。
    @raises: 不主动包装数据库异常，查询失败会沿调用栈上抛。
    """
    count = max(1, min(int(count or 5), 100))
    query = _question_base_query(db, province=province, dimension=dimension)

    if position:
        all_qs = _apply_position_filter(_position_prefilter_query(query, position).all(), position)
    else:
        total = query.count()
        if total <= count:
            all_qs = query.all()
        else:
            sample_limit = min(total, max(count * 6, 80))
            max_offset = max(total - sample_limit, 0)
            offset = random.randint(0, max_offset) if max_offset else 0
            all_qs = query.order_by(Question.id).offset(offset).limit(sample_limit).all()

    count = min(count, len(all_qs))
    return [_q_to_dict(q) for q in random.sample(all_qs, count)] if all_qs else []


def _encode_full_suite_id(province: str, suite_key: str) -> str:
    """
    生成 URL 安全的套题 ID。

    套题真实 key 可能包含中文、空格或日期片段，直接放路由容易被不同端编码成不同形式；base64url 只作为传输 ID，
    不改变题库内部 suiteKey。

    @param province: 套题所属省份代码。
    @param suite_key: 题库元数据中的真实套题 key。
    @return: 可放进 `/exam/full-suites/{suiteId}/questions` 的短 ID。
    @raises: 编码异常会沿调用栈暴露。
    """
    raw = f"{province}|{suite_key}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_full_suite_id(suite_id: str) -> tuple[str, str]:
    """
    解析全真套题路由 ID。

    解析失败时返回空值，调用方再统一转成 404；这样前端传旧 ID 或手动篡改不会落到模糊查询。

    @param suite_id: `_encode_full_suite_id` 生成的 ID。
    @return: `(province, suite_key)` 二元组；解析失败返回 `("", "")`。
    @raises: 不主动抛出解析异常。
    """
    try:
        normalized = str(suite_id or "").strip()
        padded = normalized + "=" * (-len(normalized) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception:
        return "", ""
    if "|" not in raw:
        return "", ""
    province, suite_key = raw.split("|", 1)
    return province.strip(), suite_key.strip()


def _first_text(*values) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _first_number(*values) -> float:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return 0.0


def _boolean_meta(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "有", "是"}


def _suite_question_order(question: Question) -> int:
    meta = _question_meta_from_keywords(question.keywords)
    explicit = _first_number(meta.get("questionNo"), meta.get("fullExamQuestionNumber"))
    if explicit > 0:
        return int(explicit)
    match = re.search(r"[-_](\d{1,3})$", str(question.id or ""))
    return int(match.group(1)) if match else 999999


def _is_complete_suite(questions: list[Question]) -> bool:
    if len(questions) < 2:
        return False
    orders = [_suite_question_order(question) for question in questions]
    if any(order <= 0 or order == 999999 for order in orders):
        return False
    ordered = sorted(orders)
    return ordered == list(range(1, len(ordered) + 1))


def _suite_sort_key(suite_key: str, exam_date: str) -> str:
    date_digits = re.sub(r"\D", "", str(exam_date or ""))
    if re.match(r"^20\d{6}$", date_digits):
        return date_digits
    match = re.search(r"20\d{2}(?:\d{2})?(?:\d{2})?", str(suite_key or ""))
    return match.group(0) if match else str(suite_key or "")


def _question_matches_full_suite_filters(question: Question, filters: dict | None = None) -> bool:
    if not filters:
        return True
    meta = _question_meta_from_keywords(question.keywords)

    province = str(filters.get("province") or "").strip()
    if province and province != "all" and question.province != province:
        return False

    for field in ("examCategory", "examSubcategory", "subcategory", "subcategory2"):
        expected = str(filters.get(field) or "").strip()
        if not expected:
            continue
        actual = str(meta.get(field) or "").strip()
        if actual and expected != actual and expected not in actual and actual not in expected:
            return False

    year = str(filters.get("year") or "").strip()
    if year:
        year_set = {item.strip() for item in re.split(r"[、，,；;/\s]+", year) if item.strip()}
        if year_set and not (year_set & set(_question_years_from_meta(meta))):
            return False
    return True


def _build_full_exam_suites(db: Session, filters: dict | None = None, include_questions: bool = False) -> list[dict]:
    """
    从题库元数据构造真实套题索引。

    全真模拟需要按套题一次加载，不能让小程序拉全量题库再端侧聚合；服务端构造索引可以同时保留真实题序、年份和计时规则。

    @param db: 当前请求复用的数据库会话。
    @param filters: 考试体系、省份、子类和年份筛选。
    @param include_questions: True 时返回完整题目快照；False 时只返回轻量索引。
    @return: 套题列表，按年份/套题 key 倒序排列。
    @raises: 数据库异常会沿调用栈上抛。
    """
    filters = filters or {}
    cache_key = _cache_key("full_exam_suites", {**filters, "includeQuestions": include_questions})
    cached = _get_cached_list(_full_exam_suite_cache, cache_key, FULL_EXAM_CACHE_SECONDS)
    if cached is not None:
        return cached

    province = str(filters.get("province") or "").strip()
    query = db.query(Question)
    if province and province != "all":
        query = query.filter(Question.province == province)
    rows = [question for question in query.all() if _question_matches_full_suite_filters(question, filters)]

    groups: dict[tuple[str, str], list[Question]] = {}
    for question in rows:
        meta = _question_meta_from_keywords(question.keywords)
        suite_key = _first_text(meta.get("suiteKey"), meta.get("fullExamSuiteKey"), meta.get("suiteId"))
        if not suite_key:
            continue
        groups.setdefault((question.province or "national", suite_key), []).append(question)

    suites: list[dict] = []
    for (suite_province, suite_key), questions in groups.items():
        ordered = sorted(questions, key=lambda item: (_suite_question_order(item), item.id))
        if not _is_complete_suite(ordered):
            continue

        first_meta = _question_meta_from_keywords(ordered[0].keywords)
        answer_score_total = _first_number(first_meta.get("answerScoreTotal"))
        calculated_answer_total = sum(_first_number(_question_meta_from_keywords(q.keywords).get("questionScore")) for q in ordered)
        answer_score_total = answer_score_total or calculated_answer_total
        total_score = _first_number(first_meta.get("suiteTotalScore"), first_meta.get("totalScore")) or answer_score_total
        appearance_score = _first_number(first_meta.get("appearanceScore"))
        has_appearance_flag = first_meta.get("hasAppearanceScore") not in ("", None, [])
        has_appearance_score = _boolean_meta(first_meta.get("hasAppearanceScore")) if has_appearance_flag else appearance_score > 0
        if not appearance_score and has_appearance_score and total_score > answer_score_total:
            appearance_score = max(total_score - answer_score_total, 0)

        exam_date = _first_text(first_meta.get("examDate"))
        suite_name = _first_text(first_meta.get("suiteName"), first_meta.get("sourceTitleRaw"))
        suite = {
            "id": _encode_full_suite_id(suite_province, suite_key),
            "suiteKey": suite_key,
            "province": suite_province,
            "title": suite_name or f"{PROVINCE_NAMES.get(suite_province, _normalize_province_label(suite_province))}真题套卷 {suite_key}",
            "suiteName": suite_name,
            "examDate": exam_date,
            "examCategory": _first_text(first_meta.get("examCategory")),
            "examSubcategory": _first_text(first_meta.get("examSubcategory")),
            "subcategory": _first_text(first_meta.get("subcategory")),
            "subcategory2": _first_text(first_meta.get("subcategory2")),
            "system": _first_text(first_meta.get("system")),
            "positionType": _first_text(first_meta.get("positionType"), first_meta.get("position")),
            "interviewFormat": _first_text(first_meta.get("interviewFormat")),
            "sourceDocument": _first_text(first_meta.get("sourceDocument")),
            "timingMode": _first_text(first_meta.get("timingMode")) or ("jiangsu_5_15" if suite_province == "jiangsu" else ""),
            "questionCount": len(ordered),
            "questionIds": [question.id for question in ordered],
            "answerScoreTotal": answer_score_total,
            "totalScore": total_score,
            "appearanceScore": appearance_score,
            "hasAppearanceScore": has_appearance_score,
            "sortKey": _suite_sort_key(suite_key, exam_date),
        }
        if include_questions:
            suite["questions"] = [_q_to_dict(question) for question in ordered]
        else:
            suite["questions"] = [
                {"id": question.id, "questionNo": _suite_question_order(question)}
                for question in ordered
            ]
        suites.append(suite)

    suites.sort(key=lambda item: (str(item.get("sortKey") or ""), str(item.get("title") or "")), reverse=True)
    _set_cached_list(_full_exam_suite_cache, cache_key, suites)
    return suites


def list_full_exam_suites(
    db: Session,
    examCategory: str = "",
    province: str = "",
    examSubcategory: str = "",
    subcategory: str = "",
    subcategory2: str = "",
    year: str = "",
) -> dict:
    """
    返回全真模拟可选套题的轻量索引。

    小程序只需要先展示套题名、题数和时间规则；完整题干在用户选中套题后再一次性获取，减少首屏加载和端侧聚合成本。

    @param db: 当前请求复用的数据库会话。
    @param examCategory: 真实考试体系筛选。
    @param province: 地区筛选，可为空表示不限。
    @param examSubcategory: 二级真实分类筛选。
    @param subcategory: 三级分类筛选。
    @param subcategory2: 四级分类筛选。
    @param year: 年份筛选。
    @return: `list/total` 结构的套题索引。
    @raises: 数据库异常会沿调用栈上抛。
    """
    filters = {
        "examCategory": examCategory,
        "province": province,
        "examSubcategory": examSubcategory,
        "subcategory": subcategory,
        "subcategory2": subcategory2,
        "year": year,
    }
    suites = _build_full_exam_suites(
        db,
        {key: value for key, value in filters.items() if str(value or "").strip()},
        include_questions=False,
    )
    return {"list": suites, "total": len(suites)}


def get_full_exam_suite_questions(db: Session, suite_id: str) -> dict:
    """
    返回用户选中套题的完整题目快照。

    选中后一次性返回整套题，可以避免小程序逐题请求详情，也保证进入考场时的题序和计时规则不会被端侧缓存打乱。

    @param db: 当前请求复用的数据库会话。
    @param suite_id: `list_full_exam_suites` 返回的套题 ID。
    @return: 套题元数据和完整题目列表。
    @raises HTTPException: 套题不存在或题目不完整时抛出 404。
    """
    province, suite_key = _decode_full_suite_id(suite_id)
    if not province or not suite_key:
        raise HTTPException(status_code=404, detail="套题未找到")
    suites = _build_full_exam_suites(
        db,
        {"province": province},
        include_questions=True,
    )
    suite = next((item for item in suites if item.get("suiteKey") == suite_key and item.get("province") == province), None)
    if not suite:
        raise HTTPException(status_code=404, detail="套题未找到")
    questions = suite.get("questions") if isinstance(suite.get("questions"), list) else []
    if len(questions) != int(suite.get("questionCount") or 0):
        raise HTTPException(status_code=404, detail="套题题目不完整")
    return {"suite": suite, "questions": questions}


def get_question(db: Session, question_id: str) -> dict:
    """
    读取单道题目详情。

    题目详情会被评分、历史复盘和后台编辑共用，所以返回前统一走 `_q_to_dict`，
    保证元数据、题型维度和计时字段格式稳定。

    @param db: 当前请求复用的数据库会话。
    @param question_id: 题目 ID。
    @return: 单题详情。
    @raises HTTPException: 题目不存在时抛出 404。
    """
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目未找到")
    return _q_to_dict(q)


def create_question(db: Session, data: QuestionCreate) -> dict:
    """
    创建管理员手工题目。

    手工题用 `source=manual` 标记，和标准资产、导入题区分开；这样后续管理员可以编辑，
    但不会把标准题库 JSON 的同步行为变成双向写入。

    @param db: 当前请求复用的数据库会话。
    @param data: 题目创建请求。
    @return: 新建题目详情。
    @raises: 不主动包装数据库异常，保存失败会沿调用栈上抛。
    """
    q = Question(
        id=f"q_{uuid.uuid4().hex[:8]}",
        stem=data.stem,
        dimension=data.dimension,
        province=data.province,
        prep_time=data.prepTime,
        answer_time=data.answerTime,
        scoring_points=data.scoringPoints,
        keywords=_normalize_keywords(
            data.keywords,
            {
                "source": "manual",
                "sourceLabel": _question_source_label("manual"),
                **_question_input_meta(data),
            },
        ),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)


def update_question(db: Session, question_id: str, data: QuestionUpdate) -> dict:
    """
    更新管理员可编辑题目。

    标准资产和种子题保持只读，是为了防止后台误改后又被启动同步覆盖，造成管理员以为已保存但线上回滚。
    需要修正标准题库时，应修改源资产并重新同步。

    @param db: 当前请求复用的数据库会话。
    @param question_id: 需要更新的题目 ID。
    @param data: 题目更新请求。
    @return: 更新后的题目详情。
    @raises HTTPException: 题目不存在，或题目来源为只读资产/种子题时抛出。
    """
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目未找到")
    source = _question_meta_from_keywords(q.keywords).get("source", "")
    if source in {"local_asset", "seed"}:
        raise HTTPException(status_code=403, detail="标准题库为只读模式，不支持编辑")
    q.stem = data.stem
    q.dimension = data.dimension
    q.province = data.province
    q.prep_time = data.prepTime
    q.answer_time = data.answerTime
    q.scoring_points = data.scoringPoints
    q.keywords = _normalize_keywords(
        data.keywords,
        {
            **_question_meta_from_keywords(q.keywords),
            **_question_input_meta(data),
        },
    )
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)


def delete_question(db: Session, question_id: str) -> dict:
    """
    删除管理员可编辑题目。

    标准资产和种子题不允许从后台删除，原因和编辑一致：它们会被源资产同步恢复。
    当前删除是硬删除，调用方需要确认不会破坏仍可访问的历史复盘。

    @param db: 当前请求复用的数据库会话。
    @param question_id: 需要删除的题目 ID。
    @return: 删除成功标记。
    @raises HTTPException: 题目不存在，或题目来源为只读资产/种子题时抛出。
    """
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目未找到")
    source = _question_meta_from_keywords(q.keywords).get("source", "")
    if source in {"local_asset", "seed"}:
        raise HTTPException(status_code=403, detail="标准题库为只读模式，不支持删除")
    db.delete(q)
    db.commit()
    return {"success": True}


def import_questions(db: Session, content: bytes, filename: str) -> dict:
    """
    从 JSON 或 Excel 文件导入题目。

    该入口服务后台批量维护，导入时会统一归一化关键词、采分点和 `_meta`。
    真实题源分类仍优先使用文件内容和显式字段，不能靠前端展示入口反推考试体系。

    @param db: 当前请求复用的数据库会话。
    @param content: 上传文件内容。
    @param filename: 原始文件名，用于判断格式和记录来源。
    @return: 成功导入数量和失败数量。
    @raises HTTPException: 文件格式不支持、解析不到有效题目或导入失败时抛出。
    """
    imported, failed = 0, 0
    fname = filename.lower() if filename else ""

    try:
        if fname.endswith(".json"):
            data = json.loads(content.decode("utf-8-sig"))
            normalized_items = _normalize_json_payload(
                data,
                source_kind="imported_file",
                source_name=filename,
            )
            if not normalized_items:
                raise HTTPException(status_code=400, detail="JSON 未解析到有效题目，请检查字段格式")
            for item in normalized_items:
                try:
                    _upsert_normalized_question(db, item)
                    imported += 1
                except Exception:
                    failed += 1
            db.commit()

        elif fname.endswith((".xlsx", ".xls")):
            import io
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                raise HTTPException(status_code=400, detail="Excel 文件为空")
            headers = [str(h).strip().lower() if h else "" for h in rows[0]]
            col = {}
            mapping = {
                "id": ["id", "题目id", "题号"],
                "suiteId": ["suiteid", "套题id"],
                "suiteKey": ["suitekey", "套题key"],
                "suiteName": ["suitename", "套题名称"],
                "examDate": ["examdate", "考试日期"],
                "batch": ["batch", "批次"],
                "stem": ["题干", "stem"],
                "question": ["question", "题目"],
                "type": ["type", "题型"],
                "dimension": ["所属维度", "dimension"],
                "province": ["省份", "province"],
                "position": ["position", "岗位", "岗位/类别"],
                "questionNo": ["questionno", "题序"],
                "questionScore": ["questionscore", "题目分值", "单题分值"],
                "fullScore": ["fullscore", "满分"],
                "answerScoreTotal": ["answerscoretotal", "答题总分"],
                "appearanceScore": ["appearancescore", "仪态分"],
                "suiteTotalScore": ["suitetotalscore", "套题总分"],
                "totalScore": ["totalscore", "总分"],
                "hasAppearanceScore": ["hasappearancescore", "是否有仪态分"],
                "examCategory": ["examcategory", "考试大类"],
                "examSubcategory": ["examsubcategory", "二级分类"],
                "subcategory": ["subcategory", "三级分类"],
                "subcategory2": ["subcategory2", "四级分类"],
                "interviewFormat": ["interviewformat", "面试形式"],
                "questionTypeCategory": ["questiontypecategory", "题型维度"],
                "jobLevel": ["joblevel", "招录层级"],
                "year": ["year", "年份"],
                "timingMode": ["timingmode", "计时模式"],
                "questionCount": ["questioncount", "套题数量"],
                "classificationConfidence": ["classificationconfidence", "分类置信度"],
                "reviewStatus": ["reviewstatus", "复核状态"],
                "reviewReason": ["reviewreason", "复核原因"],
                "prepTime": ["准备时间", "preptime"],
                "answerTime": ["作答时间", "answertime"],
                "dimensions": ["dimensions_json", "dimensions", "评分维度"],
                "scoringPoints": ["采分点", "scoringpoints"],
                "scoringKeywords": ["得分关键词", "scoringkeywords"],
                "coreKeywords": ["corekeywords", "核心关键词"],
                "strongKeywords": ["strongkeywords", "强关联关键词"],
                "weakKeywords": ["weakkeywords", "弱关联关键词"],
                "deductingKeywords": ["扣分关键词", "deductingkeywords"],
                "bonusKeywords": ["加分关键词", "bonuskeywords"],
                "penaltyKeywords": ["penaltykeywords", "扣分关键词"],
                "tags": ["tags", "标签"],
                "sourceDocument": ["sourcedocument", "来源文档"],
                "sourceTitleRaw": ["sourcetitleraw", "原始标题"],
            }
            for field, aliases in mapping.items():
                for i, h in enumerate(headers):
                    if h in aliases:
                        col[field] = i
                        break
            if "stem" not in col and "question" not in col:
                raise HTTPException(status_code=400, detail="Excel 缺少题干/题目列")
            for row in rows[1:]:
                try:
                    def row_value(field: str, default: str = ""):
                        if field not in col:
                            return default
                        value = row[col[field]]
                        return default if value is None else value

                    stem = str(row_value("stem", "") or row_value("question", "")).strip()
                    if not stem:
                        failed += 1
                        continue

                    def split_cell_list(value):
                        if value in ("", None):
                            return []
                        text = str(value).strip()
                        if not text:
                            return []
                        if text.startswith("["):
                            try:
                                parsed = json.loads(text)
                                return parsed if isinstance(parsed, list) else []
                            except Exception:
                                return []
                        return [item.strip() for item in re.split(r"[；;，,、\n]+", text) if item.strip()]

                    def parse_json_cell(value, fallback):
                        if value in ("", None):
                            return fallback
                        text = str(value).strip()
                        if not text:
                            return fallback
                        if text.startswith("[") or text.startswith("{"):
                            try:
                                return json.loads(text)
                            except Exception:
                                return fallback
                        return fallback

                    def numeric_cell(field: str, default=0):
                        value = row_value(field, "")
                        if value in ("", None):
                            return default
                        try:
                            number = float(value)
                            return int(number) if number.is_integer() else number
                        except Exception:
                            return default

                    def bool_cell(field: str):
                        value = str(row_value(field, "")).strip().lower()
                        if not value:
                            return None
                        return value in {"1", "true", "yes", "y", "有", "是"}

                    kw = {"scoring": [], "deducting": [], "bonus": []}
                    for ktype, kcol in [("scoring", "scoringKeywords"), ("deducting", "deductingKeywords"), ("bonus", "bonusKeywords")]:
                        kw[ktype] = split_cell_list(row_value(kcol, ""))
                    kw["scoring"] = _unique_preserve_order(
                        kw["scoring"]
                        + split_cell_list(row_value("coreKeywords", ""))
                        + split_cell_list(row_value("strongKeywords", ""))
                        + split_cell_list(row_value("weakKeywords", ""))
                    )
                    kw["deducting"] = _unique_preserve_order(
                        kw["deducting"] + split_cell_list(row_value("penaltyKeywords", ""))
                    )
                    sp = []
                    if "scoringPoints" in col and row_value("scoringPoints", ""):
                        sp = parse_json_cell(row_value("scoringPoints"), [])
                    dimensions = parse_json_cell(row_value("dimensions", ""), [])
                    stem_value = stem or str(row_value("question", "")).strip()
                    has_appearance = bool_cell("hasAppearanceScore")
                    meta = {
                        "source": "imported_file",
                        "sourceLabel": _question_source_label("imported_file"),
                        "originFile": filename,
                        "tags": split_cell_list(row_value("tags", "")),
                        "sourceDocument": str(row_value("sourceDocument", filename)).strip(),
                        "sourceTitleRaw": str(row_value("sourceTitleRaw", "")).strip(),
                    }
                    for field in (
                        "suiteId", "suiteKey", "suiteName", "examDate", "batch", "position",
                        "examCategory", "examSubcategory", "subcategory", "subcategory2",
                        "interviewFormat", "questionTypeCategory", "jobLevel",
                        "timingMode", "questionCount",
                        "classificationConfidence", "reviewStatus", "reviewReason",
                    ):
                        value = str(row_value(field, "")).strip()
                        if value:
                            meta[field] = value
                    year_raw = row_value("year", "")
                    if year_raw:
                        meta["year"] = split_cell_list(year_raw)
                    for field in (
                        "questionNo", "questionScore", "answerScoreTotal", "appearanceScore",
                        "suiteTotalScore", "totalScore",
                    ):
                        value = numeric_cell(field, None)
                        if value is not None:
                            meta[field] = value
                    if has_appearance is not None:
                        meta["hasAppearanceScore"] = has_appearance
                    imported_item = {
                        "id": str(row_value("id", "")).strip(),
                        "stem": stem_value,
                        "type": str(row_value("type", "")).strip(),
                        "dimension": _normalize_dimension(str(row_value("dimension", "analysis")).strip(), str(row_value("type", "")).strip(), stem_value),
                        "province": _normalize_province(str(row_value("province", "national")).strip()),
                        "prepTime": int(numeric_cell("prepTime", 90) or 90),
                        "answerTime": int(numeric_cell("answerTime", 180) or 180),
                        "scoringPoints": sp or _normalize_scoring_points([], dimensions, None),
                        "dimensions": dimensions,
                        "keywords": _normalize_keywords(kw, meta),
                    }
                    # Parse timingMode/interviewFormat for prepTime/answerTime fallback
                    if imported_item["prepTime"] == 90 and imported_item["answerTime"] == 180:
                        timing_text = str(row_value("timingMode", "") or row_value("interviewFormat", "")).strip()
                        if timing_text:
                            parsed = _parse_timing_format(timing_text)
                            if parsed:
                                imported_item["prepTime"] = parsed[0]
                                imported_item["answerTime"] = parsed[1]
                    _upsert_normalized_question(db, imported_item)
                    imported += 1
                except Exception:
                    failed += 1
            db.commit()
            wb.close()
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 .json 或 .xlsx")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")

    return {"imported": imported, "failed": failed}


def import_from_docx(db: Session, file_content: bytes, filename: str, province: str) -> dict:
    """
    调用题库脚本解析 Word 真题并同步生成资产。

    Word 解析依赖独立导入脚本，是为了复用题库源文档的章节、套题标题和分类纠偏逻辑。
    `province` 只是旧上传入口的兜底地区，不能覆盖脚本从真实套题标题识别出的考试体系。

    @param db: 当前请求复用的数据库会话。
    @param file_content: 上传的 Word 文件内容。
    @param filename: 原始文件名。
    @param province: 旧入口传入的默认地区兜底。
    @return: 导入数量、套题名和临时 profile 名。
    @raises HTTPException: 脚本缺失、格式不支持或脚本执行失败时抛出。
    """
    import subprocess
    import tempfile
    import uuid as _uuid

    profile_name = f"web_import_{_uuid.uuid4().hex[:8]}"
    script_path = REPO_ROOT / "ai_gongwu_backend" / "scripts" / "import_question_bank.py"

    if not script_path.exists():
        raise HTTPException(status_code=500, detail="导入脚本未找到，请联系管理员")

    suffix = Path(filename).suffix.lower()
    if suffix not in (".docx", ".doc"):
        raise HTTPException(status_code=400, detail="仅支持 .docx / .doc 格式")

    tmp_path = Path(tempfile.gettempdir()) / f"{profile_name}{suffix}"
    tmp_path.write_bytes(file_content)

    try:
        result = subprocess.run(
            [
                "python", str(script_path),
                "--profile-name", profile_name,
                "--province", province,
                "--source-file", str(tmp_path),
            ],
            capture_output=True, text=True, timeout=300,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise HTTPException(status_code=500, detail=f"导入脚本执行失败: {stderr}")

        # Sync generated JSON files to DB
        sync_result = sync_curated_question_assets(db)
        db.commit()

        # Collect suite info from generated files
        output_dir = CURATED_QUESTION_DIR / f"generated_{profile_name}"
        imported = 0
        suites: set[str] = set()
        if output_dir.exists():
            for qf in sorted(output_dir.glob("*.json")):
                try:
                    data = json.loads(qf.read_text(encoding="utf-8"))
                    imported += 1
                    meta = data.get("_meta") or data.get("keywords", {}).get("_meta") or {}
                    suite_name = str(meta.get("suiteName") or "").strip()
                    if suite_name:
                        suites.add(suite_name)
                except Exception:
                    pass

        return {
            "imported": imported or sync_result.get("synced", 0),
            "failed": 0,
            "suites": sorted(suites),
            "profileName": profile_name,
        }
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


async def generate_questions_by_position(
    db: Session,
    province: str,
    position: str,
    count: int = 5,
    source_mode: str = "local",
    target_filters: dict | None = None,
) -> List[dict]:
    """
    为定向备面按真实题库或 AI 兜底生成题目。

    默认优先本地题库，只有明确要求 AI 或混合模式时才调用 LLM。
    这能保证没有真实题库数据的地区不会被“通用模板”伪装成真实重点或真题来源。

    @param db: 当前请求复用的数据库会话。
    @param province: 地区筛选。
    @param position: 岗位或方向筛选，空值表示不限。
    @param count: 请求题量，服务端最多生成 10 道。
    @param source_mode: `local`、`ai` 或 `hybrid`。
    @param target_filters: 定向分类树传入的考试体系、地区、系统等筛选条件。
    @return: 定向题目列表，并标注来源或 AI 回退原因。
    @raises: LLM、数据库或资产同步异常会沿调用栈上抛。
    """
    count = min(count, 10)
    _sync_curated_question_assets_if_stale(db)
    normalized_mode = str(source_mode or "local").strip().lower()

    if normalized_mode == "ai":
        generated = await _generate_targeted_questions_with_llm(db, province, position, count)
        if generated:
            return generated
        fallback_reason = (
            "AI 定向题服务未配置，已回退为本地真题/题库题"
            if not settings.llm_api_key
            else "AI 定向题服务返回异常，已回退为本地真题/题库题"
        )
        return [
            {
                **item,
                "generationSource": "fallback_bank",
                "generationFallbackReason": fallback_reason,
            }
            for item in _choose_targeted_bank_questions(db, province, position, count, target_filters)
        ]

    if normalized_mode == "hybrid":
        local_items = _choose_targeted_bank_questions(db, province, position, count, target_filters)
        if len(local_items) >= count:
            return local_items[:count]
        generated = await _generate_targeted_questions_with_llm(
            db,
            province,
            position,
            count - len(local_items),
        )
        return local_items + generated

    return _choose_targeted_bank_questions(db, province, position, count, target_filters)


async def generate_training_questions(
    db: Session,
    dimension: str,
    count: int = 3,
    source_mode: str = "local",
    province: str = "national",
    target_filters: dict | None = None,
) -> List[dict]:
    """
    为专项训练按题型维度生成题目。

    这里的 `dimension` 是训练题型分类，不是评分能力维度；保持这条边界可以避免“行政思维”等能力项
    被错误用于专项题型筛选。

    @param db: 当前请求复用的数据库会话。
    @param dimension: 训练题型分类。
    @param count: 请求题量，服务端最多生成 10 道。
    @param source_mode: `local`、`ai` 或其他兜底模式。
    @param province: 地区筛选。
    @param target_filters: 定向分类筛选条件，可为空。
    @return: 专项训练题目列表。
    @raises: LLM、数据库或资产同步异常会沿调用栈上抛。
    """
    count = min(count, 10)
    _sync_curated_question_assets_if_stale(db)
    normalized_mode = str(source_mode or "local").strip().lower()

    if normalized_mode == "local":
        return _choose_training_bank_questions(db, dimension, count, province=province, target_filters=target_filters)

    dim_name = DIMENSION_NAMES.get(dimension, dimension)
    prompt = f"""请生成{count}道考察"{dim_name}"能力的公务员面试题目。
每道题以JSON对象表示，放在一个JSON数组中返回。
每道题包含字段：
- stem: 题目内容(字符串)
- scoringPoints: 采分点数组，每项含 content 和 score
- keywords: 含 scoring/deducting/bonus 三个字符串数组
返回纯JSON数组，不要有其他内容。"""
    result = await call_llm_api_async(prompt, system_msg="你是公务员面试命题专家，请只输出JSON数组。", max_tokens=3000)
    if result and isinstance(result, list):
        generated = _build_generated_question_payloads(
            result[:count],
            province="national",
            default_dimension=dimension,
            default_scoring_points=[
                {"content": f"对{dim_name}有清晰理解", "score": 7},
                {"content": "结合实际提出措施", "score": 8},
                {"content": "逻辑清晰表达规范", "score": 5},
            ],
            source_kind="ai_generated",
        )
        if generated:
            return [{**item, "generationSource": "llm"} for item in generated]

    fallback_reason = (
        "AI 训练题服务未配置，已回退为本地题库题"
        if not settings.llm_api_key
        else "AI 训练题服务返回异常，已回退为本地题库题"
    )
    return [
        {
            **item,
            "generationSource": "fallback_bank",
            "generationFallbackReason": fallback_reason,
        }
        for item in _choose_training_bank_questions(db, dimension, count, province=province, target_filters=target_filters)
    ]
