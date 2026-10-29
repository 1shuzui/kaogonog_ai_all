"""Select within a fixed scope, then revalidate the same IDs before exam creation."""
import random

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.targeted_performance import TargetedPracticeContext
from app.services.targeted_performance_rules import RULES, question_type
from app.services.targeted_performance_service import collect


def candidates(data, request):
    available = {key for key, question in data["bank"].items()
                 if question_type(question) == request.questionType}
    if request.mode == "new":
        return sorted(available - data["practiced"])
    if request.mode == "review":
        return sorted(available & data["practiced"])
    low = sorted((row for row in data["records"] if row["questionId"] in available
                  and row["contentPercent"] < RULES["lowThreshold"]),
                 key=lambda row: (row["contentPercent"], row["recordedAt"], row["questionId"]))
    return [row["questionId"] for row in low]


def select_practice(db, username, request):
    data = collect(db, username, request.target, request.period)
    ids = candidates(data, request)
    if request.mode != "low_score":
        random.SystemRandom().shuffle(ids)
    chosen = ids[:request.count]
    context = TargetedPracticeContext(**request.model_dump()).model_dump()
    context["target"] = data["target"]
    return {"questionIds": chosen, "requestedCount": request.count, "actualCount": len(chosen),
            "availableCount": len(ids), "scopeKey": data["scopeKey"], "targetedContext": context,
            "reason": "empty" if not chosen else "insufficient" if len(chosen) < request.count else "",
            "analysisRevision": data["revision"]}


def validate_practice(db, username, question_ids, context):
    try:
        request = TargetedPracticeContext.model_validate(context)
    except ValidationError:
        raise HTTPException(422, "针对练习条件无效，请返回分析页重新选择")
    if not question_ids or len(question_ids) > request.count or len(set(question_ids)) != len(question_ids):
        raise HTTPException(422, "针对练习题量不完整，请重新选题")
    data = collect(db, username, request.target, request.period)
    eligible = set(candidates(data, request))
    if not set(question_ids).issubset(eligible):
        raise HTTPException(409, "题目范围或作答记录已变化，请重新选题后开始练习")
