"""Personal score projections over owned persisted answers; no model calls or writes."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from types import SimpleNamespace

from sqlalchemy.orm import load_only

from app.models.entities import Exam, ExamAnswer, Question
from app.services.question_filters import filter_bank_rows, normalize_province
from app.services.question_scope import values
from app.services.scoring_service import _is_placeholder_transcript
from app.services.targeted_performance_rules import (
    QUESTION_TYPES, RULES, classification, content_pair, dimension_rates,
    original_pair, percent_text, question_type, utc, window,
)

SCOPE_FIELDS = ("province", "position", "examTrack", "examCategory", "examSubcategory",
                "subcategory", "subcategory2", "city", "district", "areaLevel", "system",
                "portalTag", "displayPortal", "positionType", "positionTag", "positionTags", "year")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def normalize_target(target):
    raw = target.model_dump() if hasattr(target, "model_dump") else dict(target)
    result = {key: value for key, value in raw.items() if value not in (None, "", [])}
    for key in ("year", "positionTags"):
        result[key] = sorted(set(values(raw.get(key))))
    result["province"] = normalize_province(raw.get("province"))
    return result


def scope_identity(target):
    return digest({key: target.get(key) for key in SCOPE_FIELDS if target.get(key)})


def matches_target(question, target):
    province = target.get("province")
    if province and province != "all" and question.province != province:
        return False
    keywords = question.keywords if isinstance(question.keywords, dict) else {}
    meta = keywords.get("_meta") if isinstance(keywords.get("_meta"), dict) else {}
    # Explicit category filters cannot accept missing metadata or infer a job
    # from incidental words in an answer prompt.
    source_question = SimpleNamespace(stem="", keywords={"_meta": meta})
    role_fields = ("positionType", "positionTag", "positionTags")
    filters = {key: target[key] for key in SCOPE_FIELDS if key != "province" and key not in role_fields and target.get(key)}
    if not filter_bank_rows([source_question], **filters):
        return False
    for key in role_fields:
        if target.get(key) and not filter_bank_rows([source_question], **{key: target[key]}):
            return False
    role = str(target.get("positionType") or "").strip()
    title = str(meta.get("sourceTitleRaw") or meta.get("suiteName") or "")
    return not (role and re.search(r"(?:非|不含|不包括|不包含)\s*" + re.escape(role), title))


def bank_for_target(db, target):
    query = db.query(Question).options(load_only(Question.id, Question.stem, Question.dimension,
                                                Question.province, Question.keywords))
    if target.get("province") not in (None, "", "all"):
        query = query.filter(Question.province == target["province"])
    result, cursor = {}, None
    while True:
        page = query.filter(Question.id > cursor) if cursor is not None else query
        rows = page.order_by(Question.id).limit(500).all()
        for question in rows:
            if matches_target(question, target):
                result[question.id] = question
        if len(rows) < 500:
            return result
        cursor = rows[-1].id


def owned_answers(db, username):
    query = db.query(ExamAnswer, Exam).join(Exam, Exam.id == ExamAnswer.exam_id).filter(Exam.user_id == username)
    cursor = 0
    while True:
        rows = query.filter(ExamAnswer.id > cursor).order_by(ExamAnswer.id).limit(250).all()
        for answer, exam in rows:
            if answer.question_id in (exam.question_ids or []):
                yield answer
        if len(rows) < 250:
            return
        cursor = rows[-1][0].id


def submitted(answer):
    result = answer.score_result if isinstance(answer.score_result, dict) else {}
    media = answer.media_record or result.get("mediaRecord") or {}
    return (not _is_placeholder_transcript(str(answer.transcript or ""))
            or bool(isinstance(media, dict) and any(media.get(key) for key in
                    ("assetId", "mediaId", "fileUrl", "storedFilename", "contentSha256"))))


def invalid_reason(answer):
    result = answer.score_result if isinstance(answer.score_result, dict) else {}
    trace = result.get("scoringTrace")
    mode = result.get("scoringMode") or (trace.get("scoringMode") if isinstance(trace, dict) else None)
    if result.get("skipReason"):
        return "skipped"
    if mode in {"conservative", "rule_based", "fallback"} or result.get("needsRetry") or result.get("error"):
        return "technical_failure"
    if _is_placeholder_transcript(str(answer.transcript or "")):
        return "pending" if submitted(answer) and not result.get("totalScore") else "unreliable_transcript"
    if not any(result.get(key) is not None for key in ("contentScore", "questionScore", "totalScore")):
        return "pending"
    return None if content_pair(result) else "invalid_score"


def collect(db, username, target, period, now=None):
    target = normalize_target(target)
    start, end = window(period, now)
    bank = bank_for_target(db, target)
    selected, practiced, excluded, outside = {}, set(), Counter(), Counter()
    for answer in owned_answers(db, username):
        if submitted(answer):
            practiced.add(answer.question_id)
        date = utc(answer.answered_at)
        if date is None or date > end or (start and date < start):
            continue
        if answer.question_id not in bank:
            outside[answer.question_id] += 1
            continue
        kind = question_type(bank[answer.question_id])
        if not kind:
            excluded["unclassified"] += 1
            continue
        reason = invalid_reason(answer)
        if reason:
            excluded[reason] += 1
            continue
        previous = selected.get(answer.question_id)
        if previous is None or (date, answer.id) > (utc(previous.answered_at), previous.id):
            selected[answer.question_id] = answer
    records = []
    for question_id, answer in selected.items():
        question = bank[question_id]
        result = answer.score_result
        points, maximum = content_pair(result)
        raw_points, raw_max = original_pair(result)
        rate = points / maximum * 100
        records.append({"questionId": question_id, "examId": answer.exam_id,
                        "answerId": answer.id, "questionType": question_type(question),
                        "stem": question.stem[:180], "recordedAt": utc(answer.answered_at).isoformat(),
                        "score": raw_points, "maxScore": raw_max, "contentScore": points,
                        "contentMaxScore": maximum, "contentPercent": rate,
                        "percentText": percent_text(rate), "canPractice": True,
                        "scoringSource": result.get("scoringMode", "legacy"),
                        "dimensionRates": dimension_rates(result)})
    records.sort(key=lambda row: (row["recordedAt"], row["answerId"]), reverse=True)
    # Missing questions cannot be assigned to this direction. Count them separately
    # from excluded, in-scope records, without inventing historical metadata.
    outside_ids, existing = list(outside), set()
    for offset in range(0, len(outside_ids), 500):
        existing.update(row[0] for row in db.query(Question.id).filter(Question.id.in_(outside_ids[offset:offset + 500])).all())
    unattributed = sum(count for key, count in outside.items() if key not in existing)
    return {"target": target, "scopeKey": scope_identity(target), "period": period,
            "windowStart": start.isoformat() if start else None, "windowEnd": end.isoformat(),
            "bank": bank, "practiced": practiced, "records": records, "excluded": dict(excluded), "unattributed": unattributed,
            "revision": digest([RULES, username, scope_identity(target), period, str(start), records,
                                sorted((key, question_type(q)) for key, q in bank.items()), dict(excluded), unattributed])}


def report(data):
    groups, inventory, abilities = defaultdict(list), Counter(), defaultdict(lambda: defaultdict(list))
    for question in data["bank"].values():
        if kind := question_type(question):
            inventory[kind] += 1
    for record in data["records"]:
        kind = record["questionType"]
        groups[kind].append(record["contentPercent"])
        for name, rate in record["dimensionRates"].items():
            abilities[kind][name].append(rate)
    types = []
    for kind in QUESTION_TYPES:
        scores = groups[kind]
        average = sum(scores) / len(scores) if scores else None
        status, label = classification(average, len(scores))
        dims = []
        for name, rates in abilities[kind].items():
            mean = sum(rates) / len(rates)
            dim_status, dim_label = classification(mean, len(rates))
            dims.append({"name": name, "averagePercent": mean, "percentText": percent_text(mean),
                         "sampleCount": len(rates), "status": dim_status, "label": dim_label})
        types.append({"questionType": kind, "averagePercent": average, "percentText": percent_text(average),
                      "sampleCount": len(scores), "status": status, "label": label,
                      "availableCount": inventory[kind], "abilities": dims})
    types.sort(key=lambda row: (row["sampleCount"] < RULES["minSamples"],
                               row["averagePercent"] if row["sampleCount"] >= RULES["minSamples"] else 101,
                               QUESTION_TYPES.index(row["questionType"])))
    eligible = [row for row in types if row["sampleCount"] >= RULES["minSamples"]]
    conclusion = (f'{eligible[0]["questionType"]}建议优先提升' if eligible and eligible[0]["status"] == "weak"
                  else "当前有足够样本的题型均达到巩固标准" if eligible
                  else "继续练习不同题目，积累足够样本后判断题型表现")
    return {key: data[key] for key in ("target", "scopeKey", "period", "windowStart", "windowEnd")} | {
        "rules": RULES, "rulesVersion": RULES["version"], "analysisRevision": data["revision"],
        "updatedAt": data["windowEnd"], "questionTypes": types, "conclusion": conclusion,
        "summary": {"sampleCount": len(data["records"]), "judgedTypeCount": len(eligible),
                    "pendingCount": data["excluded"].get("pending", 0), "excluded": data["excluded"],
                    "unattributedCount": data["unattributed"]}}


def performance(db, username, request):
    return report(collect(db, username, request.target, request.period))


def performance_answers(db, username, request):
    data = collect(db, username, request.target, request.period)
    records = [row for row in data["records"] if row["questionType"] == request.questionType
               and (request.recordFilter != "low_score" or row["contentPercent"] < RULES["lowThreshold"])]
    offset = (request.current - 1) * request.pageSize
    return {"report": report(data), "list": records[offset:offset + request.pageSize],
            "total": len(records), "current": request.current, "pageSize": request.pageSize,
            "dataChanged": bool(request.analysisRevision and request.analysisRevision != data["revision"])}
