"""Question service: CRUD, random, import, generate"""
import json
import random
import re
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import HTTPException
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
}


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
    }
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


def _upsert_normalized_question(db: Session, item: dict, *, allow_update: bool = True) -> Question:
    preferred_id = _pick_question_id(item.get("id"))
    stem_key = _normalize_stem_key(item.get("stem"))
    question = db.query(Question).filter(Question.id == preferred_id).first()

    if not question and stem_key:
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
    elif not allow_update:
        return question

    question.stem = item["stem"]
    question.dimension = item.get("dimension", "analysis")
    question.province = item.get("province", "national")
    question.prep_time = item.get("prepTime", 90)
    question.answer_time = item.get("answerTime", 180)
    question.scoring_points = item.get("scoringPoints", [])
    question.keywords = _normalize_keywords(item.get("keywords"))
    return question


def sync_curated_question_assets(db: Session) -> dict:
    if not CURATED_QUESTION_DIR.exists():
        return {"synced": 0, "updated": 0}

    synced = 0
    updated = 0
    changed = False

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
            existing = next(
                (
                    row for row in db.query(Question).all()
                    if row.id == _pick_question_id(item.get("id"))
                    or _normalize_stem_key(row.stem) == stem_key
                ),
                None,
            )
            if existing:
                updated += 1
            else:
                synced += 1
            _upsert_normalized_question(db, item)
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


def _question_matches_position(question: Question, position: str) -> bool:
    if not position:
        return True
    meta = _question_meta_from_keywords(question.keywords)
    position_tags = meta.get("positionTags") if isinstance(meta.get("positionTags"), list) else []
    if position in position_tags:
        return True

    haystack = " ".join(
        [
            question.stem,
            meta.get("sourceDocument", ""),
            " ".join(meta.get("tags", []) if isinstance(meta.get("tags"), list) else []),
            meta.get("questionType", ""),
        ]
    )
    return any(alias in haystack for alias in POSITION_ALIASES.get(position, ()))


def _question_matches_province(question: Question, province: str) -> bool:
    if not province or province == "all":
        return True
    return question.province in {province, "national"}


def _question_prefers_local_source(question: Question) -> bool:
    meta = _question_meta_from_keywords(question.keywords)
    return meta.get("source") in {"local_asset", "imported_file", "manual", "seed"}


def _choose_targeted_bank_questions(db: Session, province: str, position: str, count: int) -> list[dict]:
    questions = [
        question for question in db.query(Question).all()
        if _question_matches_province(question, province)
    ]
    exact = [question for question in questions if _question_matches_position(question, position)]
    fallback = [question for question in questions if question not in exact]

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
    preferred = db.query(Question).filter(Question.dimension == dimension).all()
    fallback = db.query(Question).all() if not preferred else []
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

    generated = _persist_generated_questions(
        db,
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
    current: int = 1,
    page_size: int = 10,
) -> dict:
    query = db.query(Question)
    if keyword:
        query = query.filter(Question.stem.contains(keyword))
    if dimension:
        query = query.filter(Question.dimension == dimension)
    if province and province != "all":
        query = query.filter(Question.province == province)
    total = query.count()
    rows = query.offset((current - 1) * page_size).limit(page_size).all()
    return {
        "list": [_q_to_dict(q) for q in rows],
        "total": total,
        "current": current,
        "pageSize": page_size,
    }


def get_random_questions(db: Session, province: str = "national", count: int = 5) -> List[dict]:
    query = db.query(Question)
    if province and province != "all":
        query = query.filter(Question.province.in_([province, "national"]))
    all_qs = query.all()
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
            {"source": "manual", "sourceLabel": _question_source_label("manual")},
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
    q.keywords = _normalize_keywords(data.keywords, _question_meta_from_keywords(q.keywords))
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
                "stem": ["题干", "stem"],
                "dimension": ["所属维度", "dimension"],
                "province": ["省份", "province"],
                "prepTime": ["准备时间", "preptime"],
                "answerTime": ["作答时间", "answertime"],
                "scoringPoints": ["采分点", "scoringpoints"],
                "scoringKeywords": ["得分关键词", "scoringkeywords"],
                "deductingKeywords": ["扣分关键词", "deductingkeywords"],
                "bonusKeywords": ["加分关键词", "bonuskeywords"],
            }
            for field, aliases in mapping.items():
                for i, h in enumerate(headers):
                    if h in aliases:
                        col[field] = i
                        break
            if "stem" not in col:
                raise HTTPException(status_code=400, detail="Excel 缺少题干列")
            for row in rows[1:]:
                try:
                    stem = str(row[col["stem"]]).strip() if row[col["stem"]] else ""
                    if not stem:
                        failed += 1
                        continue
                    kw = {"scoring": [], "deducting": [], "bonus": []}
                    for ktype, kcol in [("scoring", "scoringKeywords"), ("deducting", "deductingKeywords"), ("bonus", "bonusKeywords")]:
                        if kcol in col and row[col[kcol]]:
                            val = str(row[col[kcol]]).strip()
                            kw[ktype] = json.loads(val) if val.startswith("[") else [w.strip() for w in val.split(",") if w.strip()]
                    sp = []
                    if "scoringPoints" in col and row[col["scoringPoints"]]:
                        val = str(row[col["scoringPoints"]]).strip()
                        if val.startswith("["):
                            sp = json.loads(val)
                    imported_item = {
                        "id": "",
                        "stem": stem,
                        "dimension": _normalize_dimension(str(row[col["dimension"]]).strip() if "dimension" in col and row[col["dimension"]] else "analysis"),
                        "province": _normalize_province(str(row[col["province"]]).strip() if "province" in col and row[col["province"]] else "national"),
                        "prepTime": int(row[col["prepTime"]]) if "prepTime" in col and row[col["prepTime"]] else 90,
                        "answerTime": int(row[col["answerTime"]]) if "answerTime" in col and row[col["answerTime"]] else 180,
                        "scoringPoints": sp,
                        "keywords": _normalize_keywords(
                            kw,
                            {
                                "source": "imported_file",
                                "sourceLabel": _question_source_label("imported_file"),
                                "originFile": filename,
                            },
                        ),
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
            if not settings.qwen_api_key
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
        generated = _persist_generated_questions(
            db,
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
        if not settings.qwen_api_key
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
