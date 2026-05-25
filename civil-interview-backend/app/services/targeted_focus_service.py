"""Targeted focus analysis from real question bank data."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ai import DIMENSION_NAMES, POSITION_NAMES, PROVINCE_NAMES
from app.models.entities import Question, TargetedFocusConfig
from app.services.question_service import (
    _fetch_position_candidates,
    _question_base_query,
    _question_meta_from_keywords,
)

MIN_FOCUS_QUESTION_COUNT = 1
PRIORITY_BY_RATIO = ((0.34, "high"), (0.18, "medium"), (0.0, "low"))
FREQUENCY_BY_RATIO = ((0.34, "高"), (0.18, "中"), (0.0, "低"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_province(province: str) -> str:
    return PROVINCE_NAMES.get(province, province or "national")


def _display_position(position: str) -> str:
    return POSITION_NAMES.get(position, position or "general")


def _priority(ratio: float) -> str:
    for threshold, value in PRIORITY_BY_RATIO:
        if ratio >= threshold:
            return value
    return "low"


def _frequency(ratio: float) -> str:
    for threshold, value in FREQUENCY_BY_RATIO:
        if ratio >= threshold:
            return value
    return "低"


def _normalize_focus_result(result: dict[str, Any] | None, *, province: str, position: str) -> dict[str, Any]:
    raw = result if isinstance(result, dict) else {}
    core_focus = raw.get("coreFocus") if isinstance(raw.get("coreFocus"), list) else []
    high_freq_types = raw.get("highFreqTypes") if isinstance(raw.get("highFreqTypes"), list) else []
    hot_topics = raw.get("hotTopics") if isinstance(raw.get("hotTopics"), list) else []
    strategy = raw.get("strategy") if isinstance(raw.get("strategy"), list) else []
    focus_areas = raw.get("focusAreas") if isinstance(raw.get("focusAreas"), list) else []

    return {
        "province": province,
        "provinceName": raw.get("provinceName") or _display_province(province),
        "position": position,
        "positionName": raw.get("positionName") or _display_position(position),
        "focusAreas": focus_areas,
        "coreFocus": core_focus,
        "highFreqTypes": high_freq_types,
        "hotTopics": [str(item).strip() for item in hot_topics if str(item).strip()][:12],
        "strategy": [str(item).strip() for item in strategy if str(item).strip()][:8],
        "questionCount": int(raw.get("questionCount") or 0),
        "dataSource": raw.get("dataSource") or "question_bank",
        "isFallback": bool(raw.get("isFallback", False)),
        "message": str(raw.get("message") or "").strip(),
        "updatedAt": raw.get("updatedAt") or _now_iso(),
    }


def _empty_focus_result(province: str, position: str, message: str = "暂无足够题库数据") -> dict[str, Any]:
    return _normalize_focus_result(
        {
            "coreFocus": [],
            "highFreqTypes": [],
            "hotTopics": [],
            "strategy": [],
            "questionCount": 0,
            "dataSource": "question_bank",
            "isFallback": False,
            "message": message,
            "updatedAt": _now_iso(),
        },
        province=province,
        position=position,
    )


def _question_tags(question: Question) -> list[str]:
    meta = _question_meta_from_keywords(question.keywords)
    values: list[str] = []
    for key in ("tags", "coreKeywords", "strongKeywords", "weakKeywords"):
        raw = meta.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip() for item in raw if str(item).strip())
    if isinstance(question.keywords, dict):
        for key in ("scoring", "bonus"):
            raw = question.keywords.get(key)
            if isinstance(raw, list):
                values.extend(str(item).strip() for item in raw if str(item).strip())
    return values


def _compact_topic(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 18:
        text = text[:18]
    return text


def build_focus_analysis_from_questions(db: Session, province: str, position: str) -> dict[str, Any]:
    province = (province or "national").strip()
    position = (position or "general").strip()

    if position:
        questions = _fetch_position_candidates(db, province=province, position=position)
    else:
        questions = _question_base_query(db, province=province).all()

    questions = [item for item in questions if item.province == province]
    total = len(questions)
    if total < MIN_FOCUS_QUESTION_COUNT:
        return _empty_focus_result(province, position)

    dimension_counts = Counter(str(item.dimension or "analysis") for item in questions)
    tag_counts: Counter[str] = Counter()
    type_examples: dict[str, str] = {}
    for question in questions:
        dim = str(question.dimension or "analysis")
        type_examples.setdefault(dim, question.stem[:80])
        for tag in _question_tags(question):
            topic = _compact_topic(tag)
            if topic and topic not in {"local_asset", "manual", "seed"}:
                tag_counts[topic] += 1

    core_focus = []
    focus_areas = []
    for dimension, count in dimension_counts.most_common(6):
        ratio = count / total if total else 0
        name = DIMENSION_NAMES.get(dimension, dimension)
        weight = max(8, round(ratio * 100))
        description = f"当前题库中该类题约 {count}/{total} 道，建议结合{_display_position(position)}场景重点训练。"
        core_focus.append({"name": name, "weight": weight, "desc": description})
        focus_areas.append({
            "type": dimension,
            "label": name,
            "description": description,
            "priority": _priority(ratio),
        })

    high_freq_types = []
    for dimension, count in dimension_counts.most_common(6):
        ratio = count / total if total else 0
        name = DIMENSION_NAMES.get(dimension, dimension)
        high_freq_types.append({
            "type": name,
            "frequency": _frequency(ratio),
            "example": type_examples.get(dimension) or f"{name}类题目出现 {count} 次",
        })

    hot_topics = [topic for topic, _ in tag_counts.most_common(12)]
    if not hot_topics:
        hot_topics = [DIMENSION_NAMES.get(dimension, dimension) for dimension, _ in dimension_counts.most_common(6)]

    province_name = _display_province(province)
    position_name = _display_position(position)
    strategy = [
        f"先按{province_name}{position_name}现有真题高频题型安排训练，优先覆盖 {core_focus[0]['name'] if core_focus else '综合分析'}。",
        "每次练习后对照采分点复盘关键词命中、逻辑结构和落地举措。",
        "若该方向题量较少，请结合相邻岗位或同省份通用题补充练习，避免只背固定模板。",
    ]

    return _normalize_focus_result(
        {
            "focusAreas": focus_areas,
            "coreFocus": core_focus,
            "highFreqTypes": high_freq_types,
            "hotTopics": hot_topics,
            "strategy": strategy,
            "questionCount": total,
            "dataSource": "question_bank",
            "isFallback": False,
            "updatedAt": _now_iso(),
        },
        province=province,
        position=position,
    )


def _config_to_dict(config: TargetedFocusConfig) -> dict[str, Any]:
    return {
        "id": config.id,
        "province": config.province,
        "provinceName": _display_province(config.province),
        "position": config.position,
        "positionName": _display_position(config.position),
        "autoResult": _normalize_focus_result(config.auto_result, province=config.province, position=config.position),
        "publishedResult": _normalize_focus_result(config.published_result, province=config.province, position=config.position) if config.published_result else {},
        "publishMode": config.publish_mode,
        "isActive": bool(config.is_active),
        "updatedBy": config.updated_by or "",
        "createdAt": config.created_at.isoformat() if config.created_at else "",
        "updatedAt": config.updated_at.isoformat() if config.updated_at else "",
    }


def get_or_create_focus_config(db: Session, province: str, position: str) -> TargetedFocusConfig:
    province = (province or "national").strip()
    position = (position or "general").strip()
    config = db.query(TargetedFocusConfig).filter(
        TargetedFocusConfig.province == province,
        TargetedFocusConfig.position == position,
    ).first()
    if config:
        return config
    auto_result = build_focus_analysis_from_questions(db, province, position)
    config = TargetedFocusConfig(
        province=province,
        position=position,
        auto_result=auto_result,
        published_result=auto_result,
        publish_mode="auto",
        is_active=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_focus_analysis(db: Session, province: str, position: str) -> dict[str, Any]:
    province = (province or "national").strip()
    position = (position or "general").strip()
    config = db.query(TargetedFocusConfig).filter(
        TargetedFocusConfig.province == province,
        TargetedFocusConfig.position == position,
        TargetedFocusConfig.is_active.is_(True),
    ).first()
    if config:
        if config.publish_mode == "manual" and config.published_result:
            result = _normalize_focus_result(config.published_result, province=province, position=position)
            result["dataSource"] = "admin_manual"
            return result
        if config.published_result:
            result = _normalize_focus_result(config.published_result, province=province, position=position)
            result["dataSource"] = "admin_auto"
            return result
        if config.auto_result:
            return _normalize_focus_result(config.auto_result, province=province, position=position)
    return build_focus_analysis_from_questions(db, province, position)


def list_focus_configs(db: Session, province: str = "", position: str = "") -> list[dict[str, Any]]:
    query = db.query(TargetedFocusConfig)
    if province:
        query = query.filter(TargetedFocusConfig.province == province)
    if position:
        query = query.filter(TargetedFocusConfig.position == position)
    rows = query.order_by(TargetedFocusConfig.updated_at.desc(), TargetedFocusConfig.id.desc()).all()
    return [_config_to_dict(row) for row in rows]


def get_focus_config(db: Session, province: str, position: str) -> dict[str, Any]:
    return _config_to_dict(get_or_create_focus_config(db, province, position))


def analyze_focus_config(db: Session, province: str, position: str, username: str = "") -> dict[str, Any]:
    config = get_or_create_focus_config(db, province, position)
    config.auto_result = build_focus_analysis_from_questions(db, province, position)
    if config.publish_mode == "auto":
        config.published_result = config.auto_result
    config.updated_by = username or config.updated_by
    db.commit()
    db.refresh(config)
    return _config_to_dict(config)


def update_focus_config(
    db: Session,
    config_id: int,
    *,
    published_result: dict[str, Any],
    publish_mode: str,
    is_active: bool,
    username: str = "",
) -> dict[str, Any]:
    config = db.query(TargetedFocusConfig).filter(TargetedFocusConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="重点分析配置不存在")
    if publish_mode not in {"auto", "manual"}:
        raise HTTPException(status_code=400, detail="publishMode 只能是 auto 或 manual")
    normalized = _normalize_focus_result(published_result, province=config.province, position=config.position)
    config.published_result = normalized
    config.publish_mode = publish_mode
    config.is_active = bool(is_active)
    config.updated_by = username or config.updated_by
    db.commit()
    db.refresh(config)
    return _config_to_dict(config)


def publish_focus_config(db: Session, config_id: int, username: str = "") -> dict[str, Any]:
    config = db.query(TargetedFocusConfig).filter(TargetedFocusConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="重点分析配置不存在")
    if not config.published_result:
        config.published_result = config.auto_result or build_focus_analysis_from_questions(db, config.province, config.position)
    config.is_active = True
    config.updated_by = username or config.updated_by
    db.commit()
    db.refresh(config)
    return _config_to_dict(config)


def disable_focus_config(db: Session, config_id: int, username: str = "") -> dict[str, Any]:
    config = db.query(TargetedFocusConfig).filter(TargetedFocusConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="重点分析配置不存在")
    config.is_active = False
    config.updated_by = username or config.updated_by
    db.commit()
    db.refresh(config)
    return _config_to_dict(config)
