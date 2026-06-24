"""
历史成绩服务层，负责读取已完成考试的成绩列表、趋势、统计卡片和单场复盘详情。

结果页、历史页和“我的”页都需要复用同一份历史数据，所以这里只消费已经保存的 `HistoryRecord`、
`ExamAnswer` 和题目元数据，不重新调用评分模型。能力维度名称在这里做兼容归一，例如旧数据里的“法治思维”映射为“行政思维”，
避免前端薄弱维度展示和当前评分维度不一致。

@param: 服务函数接收数据库 Session、当前用户、分页参数或考试 ID。
@return: 返回历史列表、趋势点、统计摘要或复盘详情。
@raises HTTPException: 历史记录不存在、用户无权查看或考试结果缺失时抛出 HTTP 错误。
"""
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question

DIMENSION_NAME_ALIASES = {
    "法治思维": "行政思维",
}

DIM_DEFS = [
    {"name": "行政思维", "maxScore": 20},
    {"name": "实务落地", "maxScore": 20},
    {"name": "逻辑结构", "maxScore": 15},
    {"name": "语言表达", "maxScore": 15},
    {"name": "综合分析", "maxScore": 15},
    {"name": "应急应变", "maxScore": 15},
]


def _normalize_dimension_name(name: str) -> str:
    normalized = str(name or "").strip()
    return DIMENSION_NAME_ALIASES.get(normalized, normalized)


def _normalize_dimensions(dimensions) -> list:
    if not isinstance(dimensions, list):
        return []
    normalized = []
    for item in dimensions:
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        next_item["name"] = _normalize_dimension_name(next_item.get("name"))
        normalized.append(next_item)
    return normalized


def _has_final_score(answer: ExamAnswer) -> bool:
    return isinstance(answer.score_result, dict) and "totalScore" in answer.score_result


def _record_to_dict(r: HistoryRecord) -> dict:
    completed_at = r.completed_at.isoformat() if r.completed_at else ""
    question_count = r.question_count or 0
    return {
        "examId": r.exam_id,
        "username": r.username,
        "questionCount": question_count,
        "totalScore": float(r.total_score or 0),
        "maxScore": float(r.max_score or 100),
        "grade": r.grade,
        "province": r.province or "national",
        "dimensions": _normalize_dimensions(r.dimensions),
        "completedAt": completed_at,
        "date": completed_at,
        "questionSummary": f"{question_count}题模拟练习" if question_count else "模拟练习记录",
    }


def _grade_for_score(score: float, max_score: float = 100.0) -> str:
    ratio = score / max_score if max_score else 0
    if ratio > 0.85:
        return "A"
    if ratio >= 0.75:
        return "B"
    if ratio >= 0.60:
        return "C"
    return "D"


def _load_exam_context(db: Session, exam: Exam) -> tuple[list[str], list[ExamAnswer], dict[str, Question]]:
    question_ids = exam.question_ids if isinstance(exam.question_ids, list) else []
    answers = db.query(ExamAnswer).filter(ExamAnswer.exam_id == exam.id).all()

    lookup_ids = list(question_ids)
    for answer in answers:
        if answer.question_id not in lookup_ids:
            lookup_ids.append(answer.question_id)

    question_lookup: dict[str, Question] = {}
    if lookup_ids:
        questions = db.query(Question).filter(Question.id.in_(lookup_ids)).all()
        question_lookup = {question.id: question for question in questions}

    order_map = {question_id: index for index, question_id in enumerate(lookup_ids)}
    answers.sort(
        key=lambda answer: (
            order_map.get(answer.question_id, len(order_map)),
            answer.answered_at or datetime.min.replace(tzinfo=timezone.utc),
        )
    )
    return lookup_ids, answers, question_lookup


def _resolve_exam_province(exam: Exam | None, record: HistoryRecord | None, question_lookup: dict[str, Question], question_ids: list[str]) -> str:
    if record and record.province:
        return record.province
    for question_id in question_ids:
        question = question_lookup.get(question_id)
        if question and question.province:
            return question.province
    return "national"


def _parse_filter_datetime(value: str, end_of_day: bool = False) -> datetime | None:
    normalized = (value or "").strip()
    if not normalized:
        return None

    try:
        if len(normalized) == 10:
            dt = datetime.fromisoformat(normalized)
            if end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="历史日期筛选格式无效") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _in_date_range(row: dict, start_at: datetime | None, end_at: datetime | None) -> bool:
    if not start_at and not end_at:
        return True

    raw = row.get("sortAt") or row.get("date") or row.get("completedAt")
    if not raw:
        return False

    try:
        current = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)

    if start_at and current < start_at:
        return False
    if end_at and current > end_at:
        return False
    return True


def _build_exam_summary(exam: Exam, answers: list[ExamAnswer], question_lookup: dict[str, Question], question_ids: list[str], record: HistoryRecord | None = None) -> dict:
    scored_answers = [answer for answer in answers if answer.score_result]
    question_count = int(record.question_count or 0) if record else len(scored_answers)
    total_score = float(record.total_score or 0) if record else 0.0
    max_score = float(record.max_score or 100) if record else 100.0
    grade = record.grade if record and record.grade else ""
    dimensions = _normalize_dimensions(record.dimensions) if record else []

    if not record:
        for answer in scored_answers:
            sr = answer.score_result or {}
            total_score += float(sr.get("totalScore", 0) or 0)
            if sr.get("dimensions"):
                dimensions = _normalize_dimensions(sr["dimensions"])
        total_score = round(total_score / question_count, 2) if question_count else 0.0
        grade = _grade_for_score(total_score, max_score)

    latest_answered_at = max((answer.answered_at for answer in answers if answer.answered_at), default=None)
    if record and record.completed_at:
        sort_dt = record.completed_at
    elif exam.end_time:
        sort_dt = exam.end_time
    elif latest_answered_at:
        sort_dt = latest_answered_at
    else:
        sort_dt = exam.start_time
    sort_at = sort_dt.isoformat() if sort_dt else ""
    total_questions = len(question_ids) or question_count
    status = exam.status or ("completed" if record else "in_progress")
    question_summary = (
        f"{question_count}题模拟练习"
        if status == "completed"
        else f"已答{question_count}/{total_questions or question_count}题（未完成）"
    )

    return {
        "examId": exam.id,
        "username": exam.user_id,
        "questionCount": question_count,
        "totalQuestions": total_questions or question_count,
        "totalScore": total_score,
        "maxScore": max_score,
        "grade": grade or _grade_for_score(total_score, max_score),
        "province": _resolve_exam_province(exam, record, question_lookup, question_ids),
        "dimensions": dimensions,
        "completedAt": record.completed_at.isoformat() if record and record.completed_at else sort_at,
        "date": sort_at,
        "status": status,
        "questionSummary": question_summary,
        "sortAt": sort_at,
    }


def _answer_to_dict(ans: ExamAnswer, question: Question | None, usage_record=None) -> dict:
    score_result = ans.score_result or {}
    media_record = score_result.get("mediaRecord", {}) if isinstance(score_result, dict) else {}
    answer_timing = score_result.get("answerTiming") if isinstance(score_result.get("answerTiming"), dict) else {}
    if not answer_timing and isinstance(media_record.get("answerTiming"), dict):
        answer_timing = media_record.get("answerTiming") or {}
    actual_seconds = int(answer_timing.get("actualSeconds") or getattr(usage_record, "usage_seconds", 0) or 0)
    standard_seconds = int(
        answer_timing.get("standardSeconds")
        or ((question.prep_time + question.answer_time) if question else 0)
        or 0
    )
    overtime_seconds = int(answer_timing.get("overtimeSeconds") or max(actual_seconds - standard_seconds, 0))
    has_persisted_timing = bool(answer_timing)
    normalized_timing = {
        "actualSeconds": actual_seconds,
        "standardSeconds": standard_seconds,
        "overtimeSeconds": max(overtime_seconds, 0),
    } if actual_seconds or has_persisted_timing else {}
    return {
        "questionId": ans.question_id,
        "questionStem": question.stem if question else "",
        "dimension": question.dimension if question else "",
        "province": question.province if question else "national",
        "prepTime": question.prep_time if question else 90,
        "answerTime": question.answer_time if question else 180,
        "transcript": ans.transcript or "",
        "scoringResult": score_result,
        "mediaUrl": media_record.get("fileUrl", ""),
        "mediaType": media_record.get("mediaType", ""),
        "mediaFilename": media_record.get("originalFilename", ""),
        "mediaSource": media_record.get("source", ""),
        "usageSeconds": actual_seconds,
        "answerTiming": normalized_timing,
        "answeredAt": ans.answered_at.isoformat() if ans.answered_at else "",
    }


def get_history_list(
    db: Session,
    username: str,
    current: int = 1,
    page_size: int = 10,
    province: str = "",
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """
    合并正式历史记录和已评分但未写入历史表的考试，避免用户刚交卷后列表短暂缺数据。

    省份和日期筛选放在这里，是为了 PC 和小程序看到同一套分页结果。

    @param db: 当前请求复用的数据库会话。
    @param username: 历史记录归属用户名。
    @param current: 当前页码。
    @param page_size: 每页条数。
    @param province: 地区筛选，只用于历史列表过滤。
    @param start_date: 起始日期字符串。
    @param end_date: 结束日期字符串。
    @return: 分页历史列表。
    @raises: 不主动包装数据库异常，查询失败会沿调用栈上抛。
    """
    records = (
        db.query(HistoryRecord)
        .filter(HistoryRecord.username == username)
        .order_by(HistoryRecord.completed_at.desc())
        .all()
    )
    exams = (
        db.query(Exam)
        .filter(Exam.user_id == username)
        .order_by(Exam.start_time.desc())
        .all()
    )

    exam_map = {exam.id: exam for exam in exams}
    merged_rows = []
    recorded_exam_ids = set()

    for record in records:
        recorded_exam_ids.add(record.exam_id)
        exam = exam_map.get(record.exam_id)
        if exam:
            question_ids, answers, question_lookup = _load_exam_context(db, exam)
            row = _build_exam_summary(exam, answers, question_lookup, question_ids, record=record)
        else:
            row = _record_to_dict(record)
            row.update({
                "totalQuestions": row["questionCount"],
                "status": "completed",
                "sortAt": row["completedAt"],
            })
        merged_rows.append(row)

    for exam in exams:
        if exam.id in recorded_exam_ids:
            continue
        question_ids, answers, question_lookup = _load_exam_context(db, exam)
        scored_answers = [answer for answer in answers if _has_final_score(answer)]
        if not scored_answers:
            continue
        merged_rows.append(_build_exam_summary(exam, answers, question_lookup, question_ids))

    if province and province != "all":
        merged_rows = [row for row in merged_rows if row.get("province") == province]

    start_at = _parse_filter_datetime(start_date)
    end_at = _parse_filter_datetime(end_date, end_of_day=True)
    merged_rows = [row for row in merged_rows if _in_date_range(row, start_at, end_at)]

    merged_rows.sort(key=lambda row: row.get("sortAt") or "", reverse=True)
    total = len(merged_rows)
    rows = merged_rows[(current - 1) * page_size: current * page_size]

    return {
        "list": [{k: v for k, v in row.items() if k != "sortAt"} for row in rows],
        "total": total,
        "current": current,
        "pageSize": page_size,
    }


def get_history_detail(db: Session, exam_id: str) -> dict:
    """
    返回单次考试的题目、答案、媒体和评分详情，给结果页和历史详情页共用。

    这里允许没有 HistoryRecord 但已有评分答案的考试展示，是为了兼容异步写历史的场景。

    @param db: 当前请求复用的数据库会话。
    @param exam_id: 考试记录 ID。
    @return: 单次考试详情、题目序列、答案、媒体和评分结果。
    @raises HTTPException: 考试和历史记录都不存在，或考试尚无评分答案时抛出 404。
    """
    r = db.query(HistoryRecord).filter(HistoryRecord.exam_id == exam_id).first()
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam and not r:
        raise HTTPException(status_code=404, detail="历史记录未找到")
    if not exam:
        detail = _record_to_dict(r)
        detail.update({
            "status": "completed",
            "startTime": "",
            "endTime": detail["completedAt"],
            "questionIds": [],
            "answers": [],
        })
        return detail

    question_ids, answers, question_lookup = _load_exam_context(db, exam)
    scored_answers = [answer for answer in answers if _has_final_score(answer)]
    if not r and not scored_answers:
        raise HTTPException(status_code=404, detail="历史记录未找到")

    detail = _build_exam_summary(exam, answers, question_lookup, question_ids, record=r)
    usage_lookup = {}
    for record in getattr(exam, "usage_records", []) or []:
        question_id = str(getattr(record, "question_id", "") or "")
        if not question_id:
            continue
        existing = usage_lookup.get(question_id)
        record_at = getattr(record, "reported_at", None)
        existing_at = getattr(existing, "reported_at", None) if existing else None
        record_ts = record_at.timestamp() if record_at else 0
        existing_ts = existing_at.timestamp() if existing_at else 0
        if not existing or record_ts >= existing_ts:
            usage_lookup[question_id] = record

    detail.update({
        "startTime": exam.start_time.isoformat() if exam.start_time else "",
        "endTime": exam.end_time.isoformat() if exam.end_time else detail["date"],
        "questionIds": question_ids,
        "answers": [
            _answer_to_dict(answer, question_lookup.get(answer.question_id), usage_lookup.get(answer.question_id))
            for answer in answers
        ],
    })
    detail.pop("sortAt", None)
    return detail


def get_history_stats(db: Session, username: str) -> dict:
    """
    汇总用户练习次数、均分、最高分和薄弱能力维度，供首页和个人页展示。

    能力维度固定使用评分维度，不能把题型分类混进来凑雷达或薄弱项。

    @param db: 当前请求复用的数据库会话。
    @param username: 需要统计的用户名。
    @return: 练习次数、均分、最高分、薄弱能力维度和能力平均分。
    @raises: 不主动包装数据库异常，查询失败会沿调用栈上抛。
    """
    rows = db.query(HistoryRecord).filter(HistoryRecord.username == username).all()
    empty = {
        "totalExams": 0, "avgScore": 0, "bestScore": 0,
        "weakestDimension": "",
        "dimensionAverages": [{"name": d["name"], "avg": 0, "maxScore": d["maxScore"]} for d in DIM_DEFS],
    }
    if not rows:
        return empty
    scores = [float(r.total_score or 0) for r in rows]
    totals = {d["name"]: [] for d in DIM_DEFS}
    for r in rows:
        for dim in (r.dimensions or []):
            name = _normalize_dimension_name(dim.get("name"))
            if name in totals:
                totals[name].append(dim.get("score", 0))
    avgs = []
    for d in DIM_DEFS:
        vals = totals[d["name"]]
        avgs.append({"name": d["name"], "avg": round(sum(vals) / len(vals), 2) if vals else 0, "maxScore": d["maxScore"]})
    weakest, lowest = "", 100
    for a in avgs:
        if a["avg"] > 0:
            pct = a["avg"] / a["maxScore"] * 100
            if pct < lowest:
                lowest, weakest = pct, a["name"]
    return {
        "totalExams": len(rows),
        "avgScore": round(sum(scores) / len(scores), 2),
        "bestScore": max(scores),
        "weakestDimension": weakest,
        "dimensionAverages": avgs,
    }


def get_history_trend(db: Session, username: str, days: int = 30) -> list:
    """
    按时间返回成绩趋势点，让双端用同一份折线数据。

    只取已完成历史记录，是为了避免正在评分中的考试把趋势线拉低。

    @param db: 当前请求复用的数据库会话。
    @param username: 需要查询趋势的用户名。
    @param days: 向前统计的天数，最少按 1 天处理。
    @return: 按完成时间升序排列的趋势点。
    @raises: 不主动包装数据库异常，查询失败会沿调用栈上抛。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    rows = (
        db.query(HistoryRecord)
        .filter(HistoryRecord.username == username, HistoryRecord.completed_at >= cutoff)
        .order_by(HistoryRecord.completed_at.asc())
        .all()
    )
    return [
        {
            "index": i + 1,
            "label": f"第{i + 1}次",
            "score": float(r.total_score or 0),
            "date": r.completed_at.strftime("%Y-%m-%d") if r.completed_at else "",
        }
        for i, r in enumerate(rows)
    ]
