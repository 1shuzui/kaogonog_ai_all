"""Exam service: start, upload, complete"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.schemas.common import ExamStartRequest

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_upload_name(raw_name: str) -> str:
    safe_name = "".join(ch for ch in str(raw_name or "") if ch.isalnum() or ch in {"-", "_", "."})
    return safe_name or "recording.webm"


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
        "startTime": exam.start_time.isoformat(),
    }


def upload_recording(
    db: Session,
    exam_id: str,
    question_id: str,
    filename: str,
    content: bytes,
    media_type: str = "",
    source: str = "live_recording",
) -> dict:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")

    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer:
        answer = ExamAnswer(exam_id=exam_id, question_id=question_id)
        db.add(answer)

    original_name = _sanitize_upload_name(filename)
    extension = Path(original_name).suffix or ".webm"
    stored_name = f"{exam_id}_{question_id}_{uuid.uuid4().hex[:8]}{extension}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(content)

    media_record = {
        "fileUrl": f"/uploads/{stored_name}",
        "storedFilename": stored_name,
        "originalFilename": original_name,
        "mediaType": media_type or "application/octet-stream",
        "source": source or "live_recording",
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }
    existing_result = answer.score_result if isinstance(answer.score_result, dict) else {}
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
        "completedAt": exam.end_time.isoformat() if exam.end_time else "",
    }
