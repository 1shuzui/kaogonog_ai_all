"""Exam service: start, upload, complete"""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.schemas.common import ExamStartRequest
from app.services.media_storage import (
    media_download_url,
    media_playback_url,
    save_media_upload,
)


def _sanitize_upload_name(raw_name: str) -> str:
    safe_name = "".join(ch for ch in str(raw_name or "") if ch.isalnum() or ch in {"-", "_", "."})
    return safe_name or "recording.webm"


def assert_exam_access(db: Session, exam_id: str, username: str, is_admin: bool = False) -> Exam:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")
    if not is_admin and exam.user_id != username:
        raise HTTPException(status_code=403, detail="无权访问该考试记录")
    return exam


def _iso_utc(value: datetime | None) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def start_exam(db: Session, data: ExamStartRequest, username: str) -> dict:
    question_ids = list(dict.fromkeys(data.questionIds))
    existing_ids = {
        row[0]
        for row in db.query(Question.id).filter(Question.id.in_(question_ids)).all()
    }
    missing_ids = [question_id for question_id in question_ids if question_id not in existing_ids]
    if missing_ids:
        preview = "、".join(missing_ids[:3])
        raise HTTPException(status_code=404, detail=f"题目不存在，无法开始考试: {preview}")

    exam_id = f"exam_{uuid.uuid4().hex[:8]}"
    exam = Exam(
        id=exam_id,
        user_id=username,
        question_ids=question_ids,
        status="in_progress",
        start_time=datetime.now(timezone.utc),
    )
    db.add(exam)
    db.commit()
    return {
        "examId": exam_id,
        "questionIds": question_ids,
        "startTime": _iso_utc(exam.start_time),
    }


def upload_recording(
    db: Session,
    exam_id: str,
    question_id: str,
    filename: str,
    content: bytes,
    username: str,
    is_admin: bool = False,
    media_type: str = "",
    source: str = "live_recording",
) -> dict:
    assert_exam_access(db, exam_id, username, is_admin=is_admin)

    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer:
        answer = ExamAnswer(exam_id=exam_id, question_id=question_id)
        db.add(answer)

    media_record = {
        **save_media_upload(content, filename, media_type=media_type, source=source),
        "playbackUrl": media_playback_url(exam_id, question_id),
        "downloadUrl": media_download_url(exam_id, question_id),
        "uploadedBy": username,
        "source": source or "live_recording",
        "uploadedAt": _iso_utc(datetime.now(timezone.utc)),
    }
    answer.media_record = media_record
    existing_result = answer.score_result if isinstance(answer.score_result, dict) else {}
    if "totalScore" not in existing_result:
        answer.score_result = {**existing_result, "mediaRecord": media_record}
    answer.answered_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, **media_record}


def complete_exam(db: Session, exam_id: str) -> dict:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")
    exam.status = "completed"
    exam.end_time = datetime.now(timezone.utc)

    answers = db.query(ExamAnswer).filter(ExamAnswer.exam_id == exam_id).all()
    total_score, question_count, dimensions = 0.0, 0, []
    for ans in answers:
        sr = ans.score_result or {}
        if "totalScore" not in sr:
            continue
        total_score += sr.get("totalScore", 0)
        question_count += 1
        if sr.get("dimensions"):
            dimensions = sr["dimensions"]

    avg = round(total_score / question_count, 2) if question_count else 0
    max_score = 100
    grade = "A" if avg / max_score > 0.85 else "B" if avg / max_score >= 0.75 else "C" if avg / max_score >= 0.60 else "D"

    # Upsert history record
    record = db.query(HistoryRecord).filter(HistoryRecord.exam_id == exam_id).first()
    if not record:
        record = HistoryRecord(exam_id=exam_id, username=exam.user_id)
        db.add(record)
    province = "national"
    if isinstance(exam.question_ids, list) and exam.question_ids:
        first_question = db.query(Question).filter(Question.id == exam.question_ids[0]).first()
        if first_question and first_question.province:
            province = first_question.province
    record.question_count = question_count
    record.total_score = avg
    record.max_score = max_score
    record.grade = grade
    record.province = province
    record.dimensions = dimensions
    record.completed_at = exam.end_time
    db.commit()

    return {
        "success": True,
        "status": exam.status,
        "questionCount": question_count,
        "finalScore": avg,
        "completedAt": _iso_utc(exam.end_time),
    }


def complete_exam_for_user(db: Session, exam_id: str, username: str, is_admin: bool = False) -> dict:
    assert_exam_access(db, exam_id, username, is_admin=is_admin)
    return complete_exam(db, exam_id)


def get_exam_media_record(db: Session, exam_id: str, question_id: str, username: str, is_admin: bool = False) -> dict:
    assert_exam_access(db, exam_id, username, is_admin=is_admin)
    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer:
        raise HTTPException(status_code=404, detail="媒体记录未找到")
    media_record = answer.media_record if isinstance(answer.media_record, dict) else {}
    if not media_record and isinstance(answer.score_result, dict):
        media_record = answer.score_result.get("mediaRecord") if isinstance(answer.score_result.get("mediaRecord"), dict) else {}
    if not media_record:
        raise HTTPException(status_code=404, detail="媒体记录未找到")
    return media_record
