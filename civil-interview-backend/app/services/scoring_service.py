"""Scoring service: transcribe, evaluate (two-stage), get result"""
import logging
from pathlib import Path
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ai import call_llm_api_async, transcribe_audio_file
from app.core.config import settings
from app.core.video_analysis import analyze_video_behavior
from app.models.entities import Question, Exam, ExamAnswer

# Import two-stage scoring utilities (same directory as before)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from two_stage_scoring import (
    build_evidence_extraction_prompt,
    build_evidence_based_scoring_prompt,
    validate_evidence,
    validate_scoring_result,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_TRANSCRIPT_MARKERS = (
    "未能识别出有效语音",
    "未配置真实语音转写服务",
    "无法生成可靠文字稿",
)

DIM_MAPPING = {
    "analysis": "综合分析",
    "practical": "实务落地",
    "emergency": "应急应变",
    "legal": "法治思维",
    "logic": "逻辑结构",
    "expression": "语言表达",
}

STRUCTURE_MARKERS = (
    "首先",
    "其次",
    "再次",
    "最后",
    "第一",
    "第二",
    "第三",
    "第四",
    "一是",
    "二是",
    "三是",
    "四是",
)

ACTION_MARKERS = (
    "及时",
    "立即",
    "主动",
    "沟通",
    "协调",
    "解释",
    "落实",
    "推进",
    "跟进",
    "整改",
    "复盘",
    "总结",
    "优化",
    "完善",
    "回应",
    "安抚",
)

POLICY_MARKERS = (
    "政策",
    "规定",
    "依据",
    "制度",
    "机制",
    "流程",
    "程序",
    "依法",
    "法治",
    "条例",
    "文件",
)

GENERIC_NOISE_MARKERS = (
    "你好",
    "谢谢",
    "喂",
    "哈哈",
    "呵呵",
    "123",
    "321",
)

FILLER_WORD_MARKERS = (
    "呃",
    "嗯",
    "啊",
    "哦",
    "额",
    "这个",
    "那个",
    "就是",
    "然后",
)

NON_SUBSTANTIVE_MARKERS = (
    *GENERIC_NOISE_MARKERS,
    *FILLER_WORD_MARKERS,
    *STRUCTURE_MARKERS,
)


async def transcribe(audio_bytes: bytes, filename: str = "answer.webm") -> dict:
    transcript = await transcribe_audio_file(audio_bytes, filename=filename)
    return {"transcript": transcript, "duration": round(len(transcript) / 10, 1)}


def _effective_transcript_length(transcript: str) -> int:
    return len("".join(ch for ch in transcript if not ch.isspace() and ch not in "（）()【】[]，,。.!！？；;：:-_"))


def _is_placeholder_transcript(transcript: str) -> bool:
    normalized = (transcript or "").strip()
    if not normalized:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_TRANSCRIPT_MARKERS)


def _build_frontend_result(frontend_dims: list[dict], rationale: str) -> dict:
    total = round(sum(dim["score"] for dim in frontend_dims), 2)
    max_score = 100
    grade = "A" if total / max_score > 0.85 else "B" if total / max_score >= 0.75 else "C" if total / max_score >= 0.60 else "D"
    return {
        "totalScore": total,
        "maxScore": max_score,
        "grade": grade,
        "dimensions": frontend_dims,
        "aiComment": rationale or "评分完成",
    }


def _question_max_score(question: Question) -> float:
    scoring_points = question.scoring_points if isinstance(question.scoring_points, list) else []
    total = 0.0
    for item in scoring_points:
        if isinstance(item, dict):
            try:
                total += float(item.get("score") or 0)
            except (TypeError, ValueError):
                continue
    return round(total, 2) if total > 0 else 30.0


def _build_zero_score_result(reason: str) -> dict:
    frontend_dims = []
    for key, display_name in DIM_MAPPING.items():
        frontend_dims.append({
            "name": display_name,
            "key": key,
            "score": 0.0,
            "maxScore": 20 if key in ["analysis", "practical"] else 15,
            "lostReasons": [],
        })
    result = _build_frontend_result(frontend_dims, reason)
    result["scoringMode"] = "screened_zero"
    return result


def _build_conservative_result(reason: str, effective_length: int) -> dict:
    if effective_length < 8:
        scores = {
            "综合分析": 1.0,
            "实务落地": 1.0,
            "应急应变": 0.5,
            "法治思维": 0.5,
            "逻辑结构": 1.0,
            "语言表达": 1.0,
        }
    else:
        scores = {
            "综合分析": 2.0,
            "实务落地": 2.0,
            "应急应变": 1.0,
            "法治思维": 1.0,
            "逻辑结构": 2.0,
            "语言表达": 2.0,
        }

    frontend_dims = []
    for key, display_name in DIM_MAPPING.items():
        frontend_dims.append({
            "name": display_name,
            "key": key,
            "score": round(scores.get(display_name, 0.0), 2),
            "maxScore": 20 if key in ["analysis", "practical"] else 15,
            "lostReasons": [],
        })
    return _build_frontend_result(frontend_dims, reason)


def _normalize_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", str(text or "").lower())


def _split_sentences(text: str) -> list[str]:
    return [
        fragment.strip()
        for fragment in re.split(r"[。！？!?；;\n\r]+", str(text or ""))
        if fragment.strip()
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _ratio(hit_count: int, total_count: int) -> float:
    return hit_count / total_count if total_count > 0 else 0.0


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


def _marker_hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker in text]


def _expand_scoring_point_keywords(scoring_points) -> list[str]:
    expanded: list[str] = []
    if not isinstance(scoring_points, list):
        return expanded
    for item in scoring_points:
        if isinstance(item, dict):
            content = str(item.get("content") or item.get("name") or "").strip()
        else:
            content = str(item or "").strip()
        if not content:
            continue
        if len(content) <= 18:
            expanded.append(content)
        for fragment in re.split(r"[，,、；;：:/（）()\s]+", content):
            fragment = fragment.strip()
            if 2 <= len(fragment) <= 12:
                expanded.append(fragment)
    return _dedupe(expanded)


def _keyword_hits(raw_text: str, compact_text: str, keywords) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for keyword in keywords or []:
        raw_keyword = str(keyword or "").strip()
        if not raw_keyword:
            continue
        compact_keyword = _normalize_text(raw_keyword)
        if not compact_keyword or compact_keyword in seen:
            continue
        if raw_keyword in raw_text or compact_keyword in compact_text:
            hits.append(raw_keyword)
            seen.add(compact_keyword)
    return hits


def _reference_similarity(answer_text: str, reference_text: str) -> float:
    compact_answer = _normalize_text(answer_text)
    compact_reference = _normalize_text(reference_text)
    if not compact_answer or not compact_reference:
        return 0.0
    return SequenceMatcher(None, compact_answer[:1600], compact_reference[:2000]).ratio()


def _repetition_metrics(compact_text: str) -> tuple[float, float, float]:
    if len(compact_text) < 8:
        return 0.0, 1.0, 0.0
    unique_char_ratio = len(set(compact_text)) / len(compact_text)
    bigrams = [compact_text[i : i + 2] for i in range(len(compact_text) - 1)]
    repeated_bigram_ratio = 1.0 - (_ratio(len(set(bigrams)), len(bigrams)) if bigrams else 1.0)
    penalty = max(0.0, repeated_bigram_ratio - 0.35) * 0.9
    if len(compact_text) >= 24 and unique_char_ratio < 0.22:
        penalty += (0.22 - unique_char_ratio) * 1.2
    return _clip(penalty, 0.0, 0.8), unique_char_ratio, repeated_bigram_ratio


def _strip_non_substantive_content(text: str) -> str:
    reduced = _normalize_text(text)
    for marker in NON_SUBSTANTIVE_MARKERS:
        compact_marker = _normalize_text(marker)
        if compact_marker:
            reduced = reduced.replace(compact_marker, "")
    return re.sub(r"\d+", "", reduced)


def _coerce_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_dimension_scores(raw_scores, max_scores: dict[str, float]) -> dict[str, float]:
    if not isinstance(raw_scores, dict):
        return {}

    display_to_key = {display_name: key for key, display_name in DIM_MAPPING.items()}
    extracted: dict[str, float] = {}
    for display_name, max_score in max_scores.items():
        raw_value = None
        for candidate in (display_name, display_to_key.get(display_name, "")):
            if candidate and candidate in raw_scores:
                raw_value = raw_scores.get(candidate)
                break
        score = _coerce_float(raw_value)
        if score is None:
            continue
        extracted[display_name] = round(max(0.0, min(score, float(max_score))), 2)
    return extracted


def _build_direct_llm_scoring_prompt(transcript: str, question_data: dict) -> str:
    dim_requirements = "\n".join(
        f"- {item.get('name', '')}：0 到 {item.get('score', 0)} 分"
        for item in question_data.get("dimensions", [])
    )
    scoring_points = question_data.get("scoringPoints", []) or []
    scoring_points_text = "\n".join(f"- {item}" for item in scoring_points[:8]) or "- 观点明确、逻辑清晰、措施可行"
    keywords = question_data.get("keywords", {}) or {}
    keyword_lines = []
    for label, values in (("采分关键词", keywords.get("scoring", [])), ("扣分关键词", keywords.get("penalty", [])), ("加分关键词", keywords.get("bonus", []))):
        if values:
            keyword_lines.append(f"{label}：{'、'.join(str(value) for value in values[:12])}")

    sample_scores = ", ".join(
        f"\"{item.get('name', '')}\": 0"
        for item in question_data.get("dimensions", [])
    )
    keyword_text = "\n".join(keyword_lines) or "关键词参考：无"
    visual_observation = str(question_data.get("visualObservation") or "").strip()
    visual_block = visual_observation or "未提供视频动作与表情观察信息。"
    return f"""你是一位资深公务员面试考官，请直接对以下答案评分。

【题目】
{question_data.get('question', '')}

【题型】
{question_data.get('type', '综合分析')}

【评分维度】
{dim_requirements}

【参考采分点】
{scoring_points_text}

【关键词参考】
{keyword_text}

【视频动作与表情观察】
{visual_block}

【考生答案】
{transcript}

【要求】
1. 只输出一个 JSON 对象，不要输出 Markdown。
2. 维度分可以为整数或一位小数，总分不用单独输出。
3. 如果答案主要是寒暄、语气词、重复词、纯数字、歌词、纯音乐转写或无实质内容，维度分应极低或 0 分。
4. 必须严格贴合题目，不要凭空补充考生没说的内容。
5. 视频观察只能影响语言表达、仪态稳定性和表情管理，不能替代内容事实判断。

【输出格式】
{{
  "dimension_scores": {{
    {sample_scores}
  }},
  "overall_rationale": "总体评价，指出主要优缺点",
  "keyword_analysis": {{
    "hit": ["命中的关键词"],
    "miss": ["缺失的关键点"]
  }}
}}"""


def _question_meta(question: Question) -> dict:
    raw_keywords = question.keywords if isinstance(question.keywords, dict) else {}
    meta = raw_keywords.get("_meta") if isinstance(raw_keywords.get("_meta"), dict) else {}
    scoring_keywords = _dedupe(
        list(raw_keywords.get("scoring", [])) + _expand_scoring_point_keywords(question.scoring_points)
    )
    penalty_keywords = _dedupe(
        list(raw_keywords.get("deducting", []))
        + list(raw_keywords.get("penalty", []))
        + list(meta.get("penaltyKeywords", []))
    )
    weak_keywords = _dedupe(list(meta.get("weakKeywords", [])) + list(meta.get("tags", [])))
    return {
        "raw_keywords": raw_keywords,
        "source": meta.get("source", ""),
        "source_label": meta.get("sourceLabel", ""),
        "reference_answer": str(meta.get("referenceAnswer") or "").strip(),
        "scoring_keywords": scoring_keywords,
        "core_keywords": list(meta.get("coreKeywords", [])),
        "strong_keywords": list(meta.get("strongKeywords", [])),
        "weak_keywords": weak_keywords,
        "bonus_keywords": list(meta.get("bonusKeywords", [])),
        "penalty_keywords": penalty_keywords,
    }


def _build_keyword_payload(question: Question, transcript: str) -> dict:
    meta = _question_meta(question)
    raw_text = str(transcript or "").strip()
    compact_text = _normalize_text(raw_text)
    scoring_hits = set(_keyword_hits(raw_text, compact_text, meta["scoring_keywords"] + meta["core_keywords"] + meta["strong_keywords"]))
    penalty_hits = set(_keyword_hits(raw_text, compact_text, meta["penalty_keywords"]))
    bonus_hits = set(_keyword_hits(raw_text, compact_text, meta["bonus_keywords"]))

    scoring_keywords = _dedupe(meta["scoring_keywords"] + meta["core_keywords"] + meta["strong_keywords"])
    return {
        "scoring": [
            {"word": word, "score": 1, "inTranscript": word in scoring_hits}
            for word in scoring_keywords[:20]
        ],
        "deducting": [
            {"word": word, "penalty": 1, "inTranscript": word in penalty_hits}
            for word in meta["penalty_keywords"][:12]
        ],
        "bonus": [
            {"word": word, "bonus": 1, "inTranscript": word in bonus_hits}
            for word in meta["bonus_keywords"][:12]
        ],
    }


def _media_record_for_exam(db: Session, exam_id: Optional[str], question_id: str) -> dict:
    if not exam_id:
        return {}
    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer or not isinstance(answer.score_result, dict):
        return {}
    media_record = answer.score_result.get("mediaRecord")
    return media_record if isinstance(media_record, dict) else {}


def _video_media_path(media_record: dict) -> Path | None:
    stored_filename = str(media_record.get("storedFilename") or "").strip()
    if not stored_filename:
        file_url = str(media_record.get("fileUrl") or "").strip()
        stored_filename = Path(file_url).name if file_url else ""
    if not stored_filename:
        return None
    uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
    candidate = uploads_dir / stored_filename
    return candidate if candidate.exists() else None


def _visual_observation_for_media(db: Session, exam_id: Optional[str], question_id: str) -> str:
    media_record = _media_record_for_exam(db, exam_id, question_id)
    if not media_record:
        return ""

    media_type = str(media_record.get("mediaType") or "").lower()
    original_filename = str(media_record.get("originalFilename") or "")
    if "video" not in media_type and Path(original_filename).suffix.lower() not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        return ""

    video_path = _video_media_path(media_record)
    if not video_path:
        return "视频文件定位失败，无法完成动作与表情观察。"
    return analyze_video_behavior(str(video_path))


def _build_scoring_trace(
    *,
    model_name: str,
    scoring_mode: str,
    evidence_prompt: str = "",
    evidence_raw=None,
    scoring_prompt: str = "",
    scoring_raw=None,
    direct_prompt: str = "",
    direct_raw=None,
    visual_observation: str = "",
) -> dict:
    trace = {
        "model": model_name,
        "scoringMode": scoring_mode,
        "visualObservation": visual_observation,
    }
    if evidence_prompt:
        trace["stageOnePrompt"] = evidence_prompt
    if evidence_raw is not None:
        trace["stageOneResult"] = evidence_raw
    if scoring_prompt:
        trace["stageTwoPrompt"] = scoring_prompt
    if scoring_raw is not None:
        trace["stageTwoResult"] = scoring_raw
    if direct_prompt:
        trace["directPrompt"] = direct_prompt
    if direct_raw is not None:
        trace["directResult"] = direct_raw
    return trace


def _decorate_result(question: Question, transcript: str, result: dict, visual_observation: str = "", scoring_trace: dict | None = None) -> dict:
    payload = dict(result or {})
    total_score = float(payload.get("totalScore", 0) or 0)
    normalized_max = float(payload.get("maxScore", 100) or 100)
    question_max_score = _question_max_score(question)
    question_score = round((total_score / normalized_max) * question_max_score, 2) if normalized_max > 0 else 0.0
    payload["questionScore"] = question_score
    payload["questionMaxScore"] = question_max_score
    payload["matchedKeywords"] = _build_keyword_payload(question, transcript)
    payload["highlightedTranscript"] = transcript or ""
    if visual_observation:
        payload["visualObservation"] = visual_observation
    if scoring_trace:
        payload["scoringTrace"] = scoring_trace
    return payload


def _is_gibberish_answer(question: Question, transcript: str) -> bool:
    raw_text = str(transcript or "").strip()
    compact_text = _normalize_text(raw_text)
    effective_length = len(compact_text)

    meta = _question_meta(question)
    keyword_signal_count = sum(
        len(_keyword_hits(raw_text, compact_text, keywords))
        for keywords in (
            meta["scoring_keywords"],
            meta["core_keywords"],
            meta["strong_keywords"],
            meta["bonus_keywords"],
        )
    )
    marker_signal_count = (
        len(_marker_hits(raw_text, STRUCTURE_MARKERS))
        + len(_marker_hits(raw_text, ACTION_MARKERS))
        + len(_marker_hits(raw_text, POLICY_MARKERS))
    )
    generic_noise_count = sum(1 for marker in GENERIC_NOISE_MARKERS if marker in raw_text)
    repetition_penalty, unique_char_ratio, repeated_bigram_ratio = _repetition_metrics(compact_text)
    digit_ratio = _ratio(sum(ch.isdigit() for ch in compact_text), effective_length)
    stripped_signal_length = len(_strip_non_substantive_content(raw_text))
    no_meaningful_signal = keyword_signal_count == 0 and marker_signal_count == 0

    if effective_length <= 3 and stripped_signal_length == 0:
        return True

    if effective_length < 8:
        if stripped_signal_length == 0:
            return True
        return no_meaningful_signal and (
            generic_noise_count >= 1
            or repetition_penalty >= 0.18
            or repeated_bigram_ratio >= 0.40
        )

    if keyword_signal_count == 0 and stripped_signal_length == 0 and effective_length < 40:
        return True

    if no_meaningful_signal and effective_length < 80:
        if generic_noise_count >= 2:
            return True
        if stripped_signal_length <= max(2, effective_length // 5) and generic_noise_count >= 1:
            return True
        if repetition_penalty >= 0.45:
            return True
        if repeated_bigram_ratio >= 0.62:
            return True
        if unique_char_ratio <= 0.32 and digit_ratio >= 0.08:
            return True
    return False


def _build_rule_based_result(question: Question, transcript: str, reason: str) -> dict:
    meta = _question_meta(question)
    raw_text = str(transcript or "").strip()
    compact_text = _normalize_text(raw_text)
    effective_length = len(compact_text)
    sentence_count = len(_split_sentences(raw_text))

    structure_hits = _marker_hits(raw_text, STRUCTURE_MARKERS)
    action_hits = _marker_hits(raw_text, ACTION_MARKERS)
    policy_hits = _marker_hits(raw_text, POLICY_MARKERS)

    scoring_hits = _keyword_hits(raw_text, compact_text, meta["scoring_keywords"])
    core_hits = _keyword_hits(raw_text, compact_text, meta["core_keywords"])
    strong_hits = _keyword_hits(raw_text, compact_text, meta["strong_keywords"])
    weak_hits = _keyword_hits(raw_text, compact_text, meta["weak_keywords"])
    bonus_hits = _keyword_hits(raw_text, compact_text, meta["bonus_keywords"])
    penalty_hits = _keyword_hits(raw_text, compact_text, meta["penalty_keywords"])
    reference_similarity = _reference_similarity(raw_text, meta["reference_answer"])
    repetition_penalty, unique_char_ratio, repeated_bigram_ratio = _repetition_metrics(compact_text)
    stripped_signal_length = len(_strip_non_substantive_content(raw_text))

    keyword_signal_count = (
        len(scoring_hits)
        + len(core_hits)
        + len(strong_hits)
        + len(weak_hits)
        + len(bonus_hits)
    )
    signal_count = keyword_signal_count + len(structure_hits) + len(action_hits) + len(policy_hits)

    content_ratio = (
        0.24 * _ratio(len(scoring_hits), len(meta["scoring_keywords"]))
        + 0.30 * _ratio(len(core_hits), len(meta["core_keywords"]))
        + 0.22 * _ratio(len(strong_hits), len(meta["strong_keywords"]))
        + 0.12 * _ratio(len(weak_hits), len(meta["weak_keywords"]))
        + 0.12 * _ratio(len(bonus_hits), len(meta["bonus_keywords"]))
    )
    if not (
        meta["scoring_keywords"]
        or meta["core_keywords"]
        or meta["strong_keywords"]
        or meta["weak_keywords"]
        or meta["bonus_keywords"]
    ):
        content_ratio = min(reference_similarity * 0.7 + _ratio(len(structure_hits), 4) * 0.3, 1.0)

    structure_ratio = _clip(
        0.45 * _ratio(len(structure_hits), 4)
        + 0.35 * _ratio(sentence_count, 5)
        + 0.20 * _ratio(len(action_hits), 4)
    )
    action_ratio = _clip(
        0.65 * _ratio(len(action_hits), 5)
        + 0.35 * _ratio(len(structure_hits), 3)
    )
    policy_ratio = _clip(_ratio(len(policy_hits), 4))
    expression_ratio = _clip(
        0.35 * _ratio(effective_length, 260)
        + 0.20 * _ratio(sentence_count, 5)
        + 0.25 * _clip(unique_char_ratio / 0.42)
        + 0.20 * _clip(1.0 - repeated_bigram_ratio * 1.1)
    )
    penalty_ratio = _clip(
        0.55 * _ratio(len(penalty_hits), len(meta["penalty_keywords"]))
        + 0.45 * repetition_penalty
    )

    quality_ratio = _clip(
        0.04
        + 0.50 * content_ratio
        + 0.20 * reference_similarity
        + 0.12 * structure_ratio
        + 0.10 * expression_ratio
        + 0.04 * action_ratio
        + 0.04 * policy_ratio
        - 0.32 * penalty_ratio
    , 0.0, 0.92)

    if effective_length < 25:
        quality_ratio = min(quality_ratio, 0.22)
    if signal_count == 0 and reference_similarity < 0.08:
        quality_ratio = min(quality_ratio, 0.08 if effective_length < 120 else 0.14)
    if keyword_signal_count == 0 and effective_length < 60:
        quality_ratio = min(quality_ratio, 0.12)
    if keyword_signal_count == 0 and reference_similarity < 0.05 and stripped_signal_length <= max(4, effective_length // 5):
        quality_ratio = min(quality_ratio, 0.02 if effective_length < 80 else 0.05)
    if keyword_signal_count == 0 and not action_hits and not policy_hits and reference_similarity < 0.04 and effective_length < 40:
        quality_ratio = min(quality_ratio, 0.02)
    if repeated_bigram_ratio > 0.72 or (effective_length >= 30 and unique_char_ratio < 0.15):
        quality_ratio = min(quality_ratio, 0.08)

    dimension_ratios = {
        "analysis": _clip(0.55 * content_ratio + 0.25 * reference_similarity + 0.10 * structure_ratio + 0.10 * expression_ratio - 0.35 * penalty_ratio),
        "practical": _clip(0.45 * content_ratio + 0.15 * reference_similarity + 0.20 * structure_ratio + 0.20 * action_ratio + 0.05 * expression_ratio - 0.35 * penalty_ratio),
        "emergency": _clip(0.30 * content_ratio + 0.15 * reference_similarity + 0.20 * structure_ratio + 0.25 * action_ratio + 0.10 * expression_ratio - 0.30 * penalty_ratio),
        "legal": _clip(0.30 * content_ratio + 0.20 * reference_similarity + 0.25 * policy_ratio + 0.15 * structure_ratio + 0.10 * expression_ratio - 0.35 * penalty_ratio),
        "logic": _clip(0.20 * content_ratio + 0.15 * reference_similarity + 0.45 * structure_ratio + 0.20 * expression_ratio - 0.30 * penalty_ratio),
        "expression": _clip(0.10 * content_ratio + 0.05 * reference_similarity + 0.15 * structure_ratio + 0.70 * expression_ratio - 0.25 * penalty_ratio),
    }

    if question.dimension in dimension_ratios:
        dimension_ratios[question.dimension] = _clip(dimension_ratios[question.dimension] + 0.08)

    frontend_dims = []
    total_cap = quality_ratio * 100.0
    raw_total = 0.0
    for key, display_name in DIM_MAPPING.items():
        max_score = 20 if key in ["analysis", "practical"] else 15
        dim_ratio = min(dimension_ratios.get(key, 0.0), quality_ratio + 0.18)
        score = round(max_score * dim_ratio, 2)
        raw_total += score
        frontend_dims.append({
            "name": display_name,
            "key": key,
            "score": score,
            "maxScore": max_score,
            "lostReasons": [],
        })

    if raw_total > total_cap and raw_total > 0:
        scale = total_cap / raw_total
        adjusted_total = 0.0
        for dim in frontend_dims:
            dim["score"] = round(dim["score"] * scale, 2)
            adjusted_total += dim["score"]
        raw_total = adjusted_total

    result = _build_frontend_result(
        frontend_dims,
        (
            f"{reason}本次按题库规则保守评分；"
            f"核心词命中 {len(core_hits)}/{len(meta['core_keywords']) or 0}，"
            f"强关联词命中 {len(strong_hits)}/{len(meta['strong_keywords']) or 0}，"
            f"结构标记 {len(structure_hits)} 处，"
            f"参考答案相似度 {reference_similarity:.2f}。"
        ),
    )
    result["scoringMode"] = "rule_based"
    result["scoringDiagnostics"] = {
        "effectiveLength": effective_length,
        "signalCount": signal_count,
        "keywordHits": {
            "scoring": len(scoring_hits),
            "core": len(core_hits),
            "strong": len(strong_hits),
            "weak": len(weak_hits),
            "bonus": len(bonus_hits),
            "penalty": len(penalty_hits),
        },
        "referenceSimilarity": round(reference_similarity, 3),
        "repetitionPenalty": round(repetition_penalty, 3),
        "strippedSignalLength": stripped_signal_length,
    }
    return _decorate_result(question, transcript, result)


def _apply_short_answer_cap(result: dict, transcript: str) -> dict:
    effective_length = _effective_transcript_length(transcript)
    if effective_length >= 40:
        return result

    if effective_length < 12:
        cap = 6.0
    elif effective_length < 25:
        cap = 12.0
    else:
        cap = 22.0

    total = float(result.get("totalScore", 0) or 0)
    if total <= cap or total <= 0:
        return result

    ratio = cap / total
    adjusted_total = 0.0
    for dim in result.get("dimensions", []):
        dim["score"] = round(float(dim.get("score", 0) or 0) * ratio, 2)
        adjusted_total += dim["score"]

    result["totalScore"] = round(adjusted_total, 2)
    if result.get("questionMaxScore"):
        question_max_score = float(result.get("questionMaxScore") or 0)
        normalized_max_score = float(result.get("maxScore", 100) or 100)
        if question_max_score > 0 and normalized_max_score > 0:
            result["questionScore"] = round(result["totalScore"] / normalized_max_score * question_max_score, 2)
    comment = result.get("aiComment", "") or "评分完成"
    result["aiComment"] = f"{comment}【系统收敛】有效作答字数较少，分数已按短答规则保守收敛。"
    total = result["totalScore"]
    max_score = float(result.get("maxScore", 100) or 100)
    result["grade"] = "A" if total / max_score > 0.85 else "B" if total / max_score >= 0.75 else "C" if total / max_score >= 0.60 else "D"
    return result


async def evaluate_answer(db: Session, question_id: str, transcript: str, exam_id: Optional[str]) -> dict:
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    effective_length = _effective_transcript_length(transcript)
    visual_observation = _visual_observation_for_media(db, exam_id, question_id)

    # Build question dict compatible with two_stage_scoring
    raw_keywords = question.keywords or {}
    q_dict = {
        "question": question.stem,
        "type": DIM_MAPPING.get(question.dimension, "综合分析"),
        "stem": question.stem,
        "scoringPoints": [sp.get("content", "") for sp in (question.scoring_points or [])],
        "keywords": {
            "scoring": raw_keywords.get("scoring", []),
            "penalty": raw_keywords.get("deducting", raw_keywords.get("penalty", [])),
            "bonus": raw_keywords.get("bonus", []),
        },
        "dimensions": [
            {"name": "综合分析", "score": 20},
            {"name": "实务落地", "score": 20},
            {"name": "应急应变", "score": 15},
            {"name": "法治思维", "score": 15},
            {"name": "逻辑结构", "score": 15},
            {"name": "语言表达", "score": 15},
        ],
        "visualObservation": visual_observation,
    }

    if _is_placeholder_transcript(transcript):
        result = _build_conservative_result(
            "未获取到可靠语音转写结果，本次评分已按保守规则处理。请配置真实 ASR 或使用浏览器语音识别后重试。",
            effective_length,
        )
        result = _decorate_result(
            question,
            transcript,
            result,
            visual_observation=visual_observation,
            scoring_trace=_build_scoring_trace(
                model_name=settings.llm_model,
                scoring_mode=result.get("scoringMode", "conservative"),
                visual_observation=visual_observation,
            ),
        )
        return _persist_result(db, exam_id, question_id, transcript, result)

    if _is_gibberish_answer(question, transcript):
        result = _build_zero_score_result("系统判定本次作答主要为重复寒暄、数字或无意义表达，按无效作答记 0 分。")
        result = _decorate_result(
            question,
            transcript,
            result,
            visual_observation=visual_observation,
            scoring_trace=_build_scoring_trace(
                model_name=settings.llm_model,
                scoring_mode=result.get("scoringMode", "screened_zero"),
                visual_observation=visual_observation,
            ),
        )
        return _persist_result(db, exam_id, question_id, transcript, result)

    if not settings.llm_api_key:
        result = _build_rule_based_result(
            question,
            transcript,
            "当前未配置 AI 评分模型，",
        )
        result = _apply_short_answer_cap(result, transcript)
        result = _decorate_result(
            question,
            transcript,
            result,
            visual_observation=visual_observation,
            scoring_trace=_build_scoring_trace(
                model_name=settings.llm_model,
                scoring_mode=result.get("scoringMode", "rule_based"),
                visual_observation=visual_observation,
            ),
        )
        return _persist_result(db, exam_id, question_id, transcript, result)

    # Stage 1: Evidence extraction
    logger.info("Stage 1: Evidence extraction")
    evidence_prompt = build_evidence_extraction_prompt(transcript, q_dict)
    evidence_raw = await call_llm_api_async(evidence_prompt)
    evidence = {"present": [], "absent": [], "penalty": [], "bonus": []}
    if evidence_raw and isinstance(evidence_raw, dict):
        evidence = evidence_raw.get("evidence", evidence)
        evidence = validate_evidence(evidence, transcript)

    # Stage 2: Evidence-based scoring
    logger.info("Stage 2: Evidence-based scoring")
    scoring_prompt = build_evidence_based_scoring_prompt(evidence, q_dict)
    scoring_raw = await call_llm_api_async(scoring_prompt)
    dim_scores, rationale = {}, ""
    max_scores = {d["name"]: d["score"] for d in q_dict["dimensions"]}
    direct_prompt = ""
    direct_raw = None

    if scoring_raw and isinstance(scoring_raw, dict):
        is_valid, errors, scoring_result = validate_scoring_result(scoring_raw, evidence, max_scores)
        dim_scores = _extract_dimension_scores(scoring_result.get("dimension_scores", {}), max_scores)
        rationale = str(scoring_result.get("overall_rationale") or "").strip()
        if errors and dim_scores:
            logger.warning("Recoverable scoring validation errors: %s", "; ".join(errors))

    if not dim_scores:
        logger.warning("Two-stage scoring failed, attempting direct llm scoring")
        direct_prompt = _build_direct_llm_scoring_prompt(transcript, q_dict)
        direct_raw = await call_llm_api_async(
            direct_prompt,
            system_msg="你是公务员面试考官，请只输出 JSON。",
            temperature=0.05,
            max_tokens=1800,
        )
        if direct_raw and isinstance(direct_raw, dict):
            dim_scores = _extract_dimension_scores(direct_raw.get("dimension_scores", {}), max_scores)
            rationale = str(direct_raw.get("overall_rationale") or rationale or "").strip()

    if not dim_scores:
        logger.warning("LLM scoring failed, using deterministic rule scorer")
        result = _build_rule_based_result(
            question,
            transcript,
            "AI 评分结果异常，已回退为题库规则评分，",
        )
        result = _apply_short_answer_cap(result, transcript)
        result = _decorate_result(
            question,
            transcript,
            result,
            visual_observation=visual_observation,
            scoring_trace=_build_scoring_trace(
                model_name=settings.llm_model,
                scoring_mode=result.get("scoringMode", "rule_based"),
                evidence_prompt=evidence_prompt,
                evidence_raw=evidence_raw,
                scoring_prompt=scoring_prompt,
                scoring_raw=scoring_raw,
                direct_prompt=direct_prompt,
                direct_raw=direct_raw,
                visual_observation=visual_observation,
            ),
        )
        return _persist_result(db, exam_id, question_id, transcript, result)

    frontend_dims = []
    for key, display_name in DIM_MAPPING.items():
        score = dim_scores.get(display_name, dim_scores.get(key, 0))
        capped = max(0, min(score, 20 if key in ["analysis", "practical"] else 15))
        frontend_dims.append({
            "name": display_name,
            "key": key,
            "score": round(capped, 2),
            "maxScore": 20 if key in ["analysis", "practical"] else 15,
            "lostReasons": [],
        })
    result = _build_frontend_result(frontend_dims, rationale or "评分完成")
    result["scoringMode"] = "llm"
    result = _apply_short_answer_cap(result, transcript)
    result = _decorate_result(
        question,
        transcript,
        result,
        visual_observation=visual_observation,
        scoring_trace=_build_scoring_trace(
            model_name=settings.llm_model,
            scoring_mode=result.get("scoringMode", "llm"),
            evidence_prompt=evidence_prompt,
            evidence_raw=evidence_raw,
            scoring_prompt=scoring_prompt,
            scoring_raw=scoring_raw,
            direct_prompt=direct_prompt,
            direct_raw=direct_raw,
            visual_observation=visual_observation,
        ),
    )
    return _persist_result(db, exam_id, question_id, transcript, result)


def _persist_result(db: Session, exam_id: Optional[str], question_id: str, transcript: str, result: dict) -> dict:
    if not exam_id:
        return result

    ans = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not ans:
        ans = ExamAnswer(exam_id=exam_id, question_id=question_id)
        db.add(ans)
    existing_result = ans.score_result if isinstance(ans.score_result, dict) else {}
    media_record = existing_result.get("mediaRecord") if isinstance(existing_result, dict) else None
    if media_record and "mediaRecord" not in result:
        result = {**result, "mediaRecord": media_record}
    visual_observation = existing_result.get("visualObservation") if isinstance(existing_result, dict) else None
    if visual_observation and "visualObservation" not in result:
        result = {**result, "visualObservation": visual_observation}
    ans.transcript = transcript
    ans.score_result = result
    ans.answered_at = datetime.now(timezone.utc)
    db.commit()
    return result


def get_scoring_result(db: Session, exam_id: str, question_id: str) -> dict:
    ans = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not ans or not ans.score_result:
        raise HTTPException(status_code=404, detail="评分结果未找到")
    return ans.score_result
