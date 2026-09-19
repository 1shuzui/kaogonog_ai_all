"""统一已保存成绩的量纲；不调用模型、不改写原文或历史评分 JSON。"""
import math

DIM_DEFS = [
    {"name": "综合分析", "maxScore": 20}, {"name": "实务落地", "maxScore": 20},
    {"name": "应急应变", "maxScore": 15}, {"name": "行政思维", "maxScore": 15},
    {"name": "逻辑结构", "maxScore": 15}, {"name": "语言表达", "maxScore": 15},
]


def number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def normalized_dimensions(result):
    raw = result.get("dimensions")
    dimensions = [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
    defaults = {item["name"]: item["maxScore"] for item in DIM_DEFS}
    for dim in dimensions:
        if dim.get("name") == "法治思维":
            dim["name"] = "行政思维"
        dim["maxScore"] = number(dim.get("maxScore"), defaults.get(dim.get("name"), 100)) or 100
    # 兼容旧仪态题：旧版把维度得分缩到内容赋分，却保留了百分制的维度上限。
    if result.get("contentScore") is not None and result.get("appearanceScore") is not None:
        content_max = number(result.get("contentMaxScore")) or number(result.get("maxScore"), 100) - number(result.get("appearanceScoreMax"))
        total = sum(number(dim.get("score")) for dim in dimensions)
        weights = sum(dim["maxScore"] for dim in dimensions)
        factor = number(result.get("contentScore")) / content_max * weights / total if total > 0 and content_max > 0 else 0
        for dim in dimensions:
            dim["score"] = round(min(dim["maxScore"], max(0, number(dim.get("score")) * factor)), 2)
    return dimensions


def summarize_answers(answers, questions=None):
    questions = questions or {}
    earned = possible = 0.0
    count = 0
    appearance_groups = {}
    ability = {}
    for answer in answers:
        score = answer.score_result if isinstance(answer.score_result, dict) else {}
        if score.get("totalScore") is None:
            continue
        count += 1
        maximum = number(score.get("maxScore"), 100) or 100
        if score.get("contentScore") is not None and score.get("appearanceScore") is not None:
            appearance_max = number(score.get("appearanceScoreMax"))
            content_max = number(score.get("contentMaxScore")) or max(0, maximum - appearance_max)
            earned += min(content_max, max(0, number(score.get("contentScore"))))
            possible += content_max
            question = questions.get(answer.question_id)
            meta = (question.keywords or {}).get('_meta', {}) if question else {}
            group = ('suite', meta.get('suiteKey') or meta.get('suiteId') or answer.question_id) if score.get('appearanceScoreScope') == 'suite' else ('question', answer.question_id)
            item = (min(appearance_max, max(0, number(score.get('appearanceScore')))), appearance_max)
            if group not in appearance_groups or score.get('appearanceScoreSource') == 'actual':
                appearance_groups[group] = item
        else:
            points = number(score.get('totalScore'))
            if score.get('questionScore') is not None and number(score.get('questionMaxScore')) > 0:
                points, maximum = number(score['questionScore']), number(score['questionMaxScore'])
            earned += min(maximum, max(0, points))
            possible += maximum
        for dim in normalized_dimensions(score):
            name = dim.get('name')
            if name:
                ability.setdefault(name, []).append(number(dim.get('score')) / dim['maxScore'])
    for points, maximum in appearance_groups.values():
        earned += points
        possible += maximum
    dimensions = [{**dim, 'score': round(sum(ability[dim['name']]) / len(ability[dim['name']]) * dim['maxScore'], 2)} for dim in DIM_DEFS if dim['name'] in ability]
    return {'totalScore': round(earned / possible * 100, 2) if possible else 0.0,
            'maxScore': 100, 'questionCount': count, 'dimensions': dimensions,
            'earnedPoints': round(earned, 2), 'possiblePoints': round(possible, 2)}
