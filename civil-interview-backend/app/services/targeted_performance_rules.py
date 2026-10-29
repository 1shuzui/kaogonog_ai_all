"""Read-only interpretation of saved scores; never changes the scoring contract."""
import math
from datetime import datetime, timedelta, timezone

RULES = {"version": "targeted-performance-v1", "lowThreshold": 60,
         "highThreshold": 80, "minSamples": 5, "scoreBasis": "content_percent"}
QUESTION_TYPES = ("综合分析", "组织管理", "应急应变", "人际沟通", "情景模拟", "岗位认知")
TYPE_CODES = dict(zip(("analysis", "organization", "emergency", "interpersonal", "simulation", "career"), QUESTION_TYPES))
BEIJING = timezone(timedelta(hours=8))


def number(value):
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def pair(points, maximum):
    points, maximum = number(points), number(maximum)
    if points is None or maximum is None or maximum <= 0 or not 0 <= points <= maximum:
        return None
    return points, maximum


def content_pair(result):
    if not isinstance(result, dict):
        return None
    if result.get("contentScore") is not None:
        maximum = number(result.get("contentMaxScore"))
        if maximum is None:
            total, appearance = number(result.get("maxScore")), number(result.get("appearanceScoreMax"))
            if total is not None and appearance is not None and appearance >= 0:
                maximum = total - appearance
        return pair(result["contentScore"], maximum)
    if (result.get("appearanceScore") is not None or result.get("hasAppearanceScore") is True
            or number(result.get("appearanceScoreMax")) not in (None, 0)):
        return None
    if result.get("questionScore") is not None:
        return pair(result["questionScore"], result.get("questionMaxScore"))
    return pair(result.get("totalScore"), result.get("maxScore"))


def original_pair(result):
    return pair(result.get("totalScore"), result.get("maxScore")) or content_pair(result)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def window(period, now=None):
    end = utc(now or datetime.now(timezone.utc))
    start = (end.astimezone(BEIJING).replace(hour=0, minute=0, second=0, microsecond=0)
             - timedelta(days=29)).astimezone(timezone.utc) if period == "recent30" else None
    return start, end


def question_type(question):
    keywords = question.keywords if isinstance(question.keywords, dict) else {}
    meta = keywords.get("_meta") if isinstance(keywords.get("_meta"), dict) else {}
    raw = str(meta.get("questionTypeCategory") or meta.get("questionType") or "").strip()
    if raw:
        return TYPE_CODES.get(raw, raw) if raw in QUESTION_TYPES or raw in TYPE_CODES else None
    # Only unambiguous legacy type codes; practical/expression are ability codes.
    return TYPE_CODES.get(question.dimension)


def classification(average, count):
    if count == 0:
        return "unpracticed", "尚未练习"
    if count < RULES["minSamples"]:
        return "insufficient", "样本不足"
    if average < RULES["lowThreshold"]:
        return "weak", "优先提升"
    if average < RULES["highThreshold"]:
        return "developing", "需巩固"
    return "strong", "较擅长"


def percent_text(value):
    if value is None:
        return "—"
    # Do not round a score across a classification boundary.
    for threshold in (RULES["lowThreshold"], RULES["highThreshold"]):
        if value < threshold and round(value, 1) >= threshold:
            return f"<{threshold}%"
    return f"{value:.1f}%"


def dimension_rates(result):
    """Only dimensions whose own denominator is saved and interpretable."""
    dimensions = result.get("dimensions")
    if not isinstance(dimensions, list):
        return {}
    valid = {}
    for item in dimensions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        score = pair(item.get("score"), item.get("maxScore"))
        if name and score:
            valid["行政思维" if name == "法治思维" else name] = score[0] / score[1] * 100
    # Older appearance scores scaled numerators but kept percentage denominators.
    # Without a proven per-dimension basis, omit these rather than invent weaknesses.
    if result.get("appearanceScore") is not None:
        return {}
    return valid
