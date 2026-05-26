"""Question service: CRUD, random, import, generate"""
import json
import random
import re
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

SYSTEM_RULES = (
    ("税务系统", ("税务", "税收", "纳税")),
    ("海关系统", ("海关",)),
    ("公安系统", ("公安", "民警", "交警", "铁路公安")),
    ("法院系统", ("法院", "法官")),
    ("检察系统", ("检察院", "检察官", "检察")),
    ("市场监管", ("市场监管", "市监")),
    ("监狱系统", ("监狱", "狱警")),
    ("金融监管系统", ("金融监管", "银保监", "证监")),
    ("银行系统", ("银行", "农商行", "城商行")),
    ("医疗卫生系统", ("医疗", "卫生", "护理", "医师", "药师", "医技")),
)

POSITION_TYPE_RULES = (
    ("A类综合管理岗", ("A类", "A 类")),
    ("B类社会科学专技岗", ("B类", "B 类")),
    ("C类自然科学专技岗", ("C类", "C 类")),
    ("D类中小学教师岗", ("D类", "D 类")),
    ("E类医疗卫生岗", ("E类", "E 类")),
    ("综合管理岗", ("综合管理", "通用岗", "普通岗")),
    ("乡镇岗", ("乡镇岗", "乡镇")),
    ("遴选岗", ("遴选",)),
    ("监狱岗", ("监狱岗", "省直监狱")),
    ("税务系统补录", ("税务系统补录", "补录")),
    ("书记员", ("书记员",)),
    ("医师岗", ("医师",)),
    ("护理岗", ("护理",)),
    ("医技岗", ("医技", "检验", "影像")),
    ("药师岗", ("药师",)),
    ("银行岗", ("银行", "柜面", "客户经理")),
)

PORTAL_TAG_RULES = (
    ("银行招考面试", ("银行招考", "银行面试", "银行", "农商行", "城商行", "柜面", "客户经理")),
    ("医疗卫生面试", ("医疗卫生", "医疗", "卫生", "护理", "医师", "药师", "医技", "医院", "医患")),
    ("法检书记员面试", ("法检", "书记员", "法院书记员", "检察院书记员")),
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
    "city",
    "district",
    "system",
    "agency",
    "positionType",
    "jobLevel",
    "interviewFormat",
    "questionTypeCategory",
    "portalTags",
    "displayPortals",
    "classificationSource",
    "classificationConfidence",
    "reviewStatus",
    "reviewReason",
    "hasCompleteSuiteLevel",
    "hasAppearanceScore",
)


def _normalize_stem_key(text: str | None) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _split_tags(value) -> list[str]:
    if isinstance(value, list):
        return _unique_preserve_order([str(item).strip() for item in value if str(item).strip()])
    if isinstance(value, str):
        return _unique_preserve_order(
            [item.strip() for item in re.split(r"[、，,；;/\s]+", value) if item.strip()]
        )
    return []


def _question_meta_from_keywords(keywords: dict | None) -> dict:
    if not isinstance(keywords, dict):
        return {}
    meta = keywords.get("_meta")
    return meta if isinstance(meta, dict) else {}


def _question_source_label(source: str) -> str:
    return QUESTION_SOURCE_LABELS.get(source, source or "未知来源")


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


def _is_jiangsu_civil_service_category(position_type: str) -> bool:
    return str(position_type or "").startswith(("A类", "B类", "C类", "D类", "E类"))


def _infer_position_type(text: str, exam_category: str, province: str, fallback: str = "") -> str:
    matched = _first_rule_match(text, POSITION_TYPE_RULES)
    if _is_jiangsu_civil_service_category(matched):
        if exam_category == "省级公务员考试" and _normalize_province_label(province) == "江苏省":
            return matched
        return fallback if fallback and fallback not in {"省考", "事业单位"} else ""
    return matched or (fallback if fallback not in {"省考", "事业单位"} else "")


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


def _infer_region_parts(text: str, province: str) -> tuple[str, str]:
    value = re.sub(r"\s+", "", str(text or ""))
    province_name = _normalize_province_label(province)
    city = ""
    district = ""
    if province_name:
        match = re.search(
            rf"{re.escape(province_name)}(?P<city>[\u4e00-\u9fff]{{2,12}}市)?(?P<district>[\u4e00-\u9fff]{{2,12}}(?:区|县|市))?",
            value,
        )
        if match:
            city = match.group("city") or ""
            district = match.group("district") or ""
    if not city:
        match = re.search(r"([\u4e00-\u9fff]{2,12}市)", value)
        city = match.group(1) if match else ""
    if not district:
        match = re.search(r"([\u4e00-\u9fff]{2,12}(?:区|县))", value)
        district = match.group(1) if match else ""
    return city, district


def _infer_agency(text: str) -> str:
    value = re.sub(r"\s+", "", str(text or ""))
    for pattern in (
        r"([\u4e00-\u9fff]{2,20}(?:厅|局|委|办|院|行|中心|学校|医院))",
        r"(中央[\u4e00-\u9fff]{2,20}(?:机关|部门))",
    ):
        match = re.search(pattern, value)
        if match:
            agency = match.group(1)
            if agency not in {"事业单位", "公务员考试"}:
                return agency
    return ""


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
    city, district = _infer_region_parts(text, province_label)
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
        "city": city,
        "district": district,
        "system": _first_rule_match(text, SYSTEM_RULES),
        "agency": _infer_agency(text),
        "positionType": _infer_position_type(text, exam_category, province_label, str(existing.get("position") or "")),
        "jobLevel": _infer_job_level(text),
        "interviewFormat": _first_rule_match(text, INTERVIEW_FORMAT_RULES),
        "questionTypeCategory": _infer_question_type_category(str(item.get("type") or existing.get("questionType") or ""), str(item.get("stem") or item.get("question") or "")),
        "portalTags": _all_rule_matches(text, PORTAL_TAG_RULES),
        "displayPortals": _all_rule_matches(text, PORTAL_TAG_RULES),
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
            "city": meta.get("city", ""),
            "district": meta.get("district", ""),
            "system": meta.get("system", ""),
            "agency": meta.get("agency", ""),
            "positionType": meta.get("positionType", ""),
            "jobLevel": meta.get("jobLevel", ""),
            "interviewFormat": meta.get("interviewFormat", ""),
            "questionTypeCategory": meta.get("questionTypeCategory", ""),
            "portalTags": meta.get("portalTags", []),
            "displayPortals": meta.get("displayPortals", meta.get("portalTags", [])),
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
    portal_tags = meta.get("portalTags") if isinstance(meta.get("portalTags"), list) else []
    display_portals = meta.get("displayPortals") if isinstance(meta.get("displayPortals"), list) else []
    if position in position_tags:
        return True
    if position == "medical" and "医疗卫生面试" in {*portal_tags, *display_portals}:
        return True
    if position == "bank" and "银行招考面试" in {*portal_tags, *display_portals}:
        return True
    if position in {"court", "procurate"} and "法检书记员面试" in {*portal_tags, *display_portals}:
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
            meta.get("system", ""),
            meta.get("agency", ""),
            meta.get("positionType", ""),
            meta.get("jobLevel", ""),
            " ".join(meta.get("tags", []) if isinstance(meta.get("tags"), list) else []),
            meta.get("questionType", ""),
            meta.get("questionTypeCategory", ""),
            " ".join(portal_tags),
            " ".join(display_portals),
        ]
    )
    return any(alias in haystack for alias in POSITION_ALIASES.get(position, ()))


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


def _choose_targeted_bank_questions(db: Session, province: str, position: str, count: int) -> list[dict]:
    questions = _question_base_query(db, province=province).all()
    exact = _fetch_position_candidates(db, province=province, position=position)
    exact_ids = {question.id for question in exact}
    fallback = [question for question in questions if question.id not in exact_ids]

    exact_local = [question for question in exact if _question_prefers_local_source(question)]
    exact_other = [question for question in exact if question not in exact_local]
    fallback_local = [question for question in fallback if _question_prefers_local_source(question)]
    fallback_other = [question for question in fallback if question not in fallback_local]

    for bucket in (exact_local, exact_other, fallback_local, fallback_other):
        random.shuffle(bucket)

    picked = exact_local + exact_other
    if len(picked) < count:
        picked.extend(fallback_local[: count - len(picked)])
    if len(picked) < count:
        picked.extend(fallback_other[: count - len(picked)])

    return [
        {
            **_q_to_dict(question),
            "generationSource": "local_bank",
        }
        for question in picked[:count]
    ]


def _choose_training_bank_questions(db: Session, dimension: str, count: int) -> list[dict]:
    preferred = _question_base_query(db, dimension=dimension).all()
    fallback = db.query(Question).limit(max(count * 4, 50)).all() if not preferred else []
    pool = preferred or fallback
    if not pool:
        return []

    local_pool = [question for question in pool if _question_prefers_local_source(question)]
    other_pool = [question for question in pool if question not in local_pool]
    for bucket in (local_pool, other_pool):
        random.shuffle(bucket)

    picked = (local_pool + other_pool)[: min(count, len(pool))]
    return [
        {
            **_q_to_dict(question),
            "dimension": dimension or question.dimension,
            "generationSource": "local_bank",
        }
        for question in picked
    ]


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
    current: int = 1,
    page_size: int = 10,
) -> dict:
    current = max(1, int(current or 1))
    page_size = max(1, min(int(page_size or 10), 1000))
    query = db.query(Question)
    if keyword:
        query = query.filter(Question.stem.contains(keyword))
    if dimension:
        query = query.filter(Question.dimension == dimension)
    if province and province != "all":
        query = query.filter(Question.province == province)
    if position:
        rows = _apply_position_filter(_position_prefilter_query(query, position).all(), position)
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


def get_question(db: Session, question_id: str) -> dict:
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目未找到")
    return _q_to_dict(q)


def create_question(db: Session, data: QuestionCreate) -> dict:
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
                "city": ["city", "城市"],
                "district": ["district", "区县"],
                "system": ["system", "系统"],
                "agency": ["agency", "单位"],
                "positionType": ["positiontype", "岗位类别"],
                "jobLevel": ["joblevel", "招录层级"],
                "interviewFormat": ["interviewformat", "面试形式"],
                "questionTypeCategory": ["questiontypecategory", "题型维度"],
                "classificationConfidence": ["classificationconfidence", "分类置信度"],
                "reviewStatus": ["reviewstatus", "复核状态"],
                "reviewReason": ["reviewreason", "复核原因"],
                "portalTags": ["portaltags", "特色入口", "展示入口"],
                "displayPortals": ["displayportals", "展示入口"],
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
                        "examCategory", "examSubcategory", "city", "district", "system", "agency",
                        "positionType", "jobLevel", "interviewFormat", "questionTypeCategory",
                        "classificationConfidence", "reviewStatus", "reviewReason",
                    ):
                        value = str(row_value(field, "")).strip()
                        if value:
                            meta[field] = value
                    portal_tags = split_cell_list(row_value("portalTags", "")) or split_cell_list(row_value("displayPortals", ""))
                    if portal_tags:
                        meta["portalTags"] = portal_tags
                        meta["displayPortals"] = portal_tags
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


async def generate_questions_by_position(
    db: Session,
    province: str,
    position: str,
    count: int = 5,
    source_mode: str = "local",
) -> List[dict]:
    count = min(count, 10)
    sync_curated_question_assets(db)
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
            for item in _choose_targeted_bank_questions(db, province, position, count)
        ]

    if normalized_mode == "hybrid":
        local_items = _choose_targeted_bank_questions(db, province, position, count)
        if len(local_items) >= count:
            return local_items[:count]
        generated = await _generate_targeted_questions_with_llm(
            db,
            province,
            position,
            count - len(local_items),
        )
        return local_items + generated

    return _choose_targeted_bank_questions(db, province, position, count)


async def generate_training_questions(
    db: Session,
    dimension: str,
    count: int = 3,
    source_mode: str = "local",
) -> List[dict]:
    count = min(count, 10)
    sync_curated_question_assets(db)
    normalized_mode = str(source_mode or "local").strip().lower()

    if normalized_mode == "local":
        return _choose_training_bank_questions(db, dimension, count)

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
        for item in _choose_training_bank_questions(db, dimension, count)
    ]
