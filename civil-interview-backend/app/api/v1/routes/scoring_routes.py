import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import ExamAnswer, Question
from app.schemas.common import AuthUser, EvaluateRequest
from app.services.scoring_service import transcribe, evaluate_answer, get_scoring_result

router = APIRouter(prefix="/scoring", tags=["scoring"])

LOW_VALUE_FILLER_TOKENS = (
    "阿巴",
    "呃",
    "额",
    "嗯",
    "啊",
    "诶",
    "唉",
    "这个",
    "那个",
    "就是",
    "然后",
    "吧",
    "嘛",
)


def _compact_transcript(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", str(text or "").strip())


def _is_low_value_transcript(text: str) -> bool:
    compact = _compact_transcript(text)
    if not compact:
        return True
    if len(compact) == 1:
        return True
    if len(compact) <= 4 and len(set(compact)) == 1:
        return True

    stripped = compact
    for token in sorted(LOW_VALUE_FILLER_TOKENS, key=len, reverse=True):
        stripped = stripped.replace(token, "")
    return not stripped


def _build_zero_score_result() -> dict:
    dimensions = [
        {"name": "综合分析", "key": "analysis", "score": 0.0, "maxScore": 20, "lostReasons": []},
        {"name": "实务落地", "key": "practical", "score": 0.0, "maxScore": 20, "lostReasons": []},
        {"name": "应急应变", "key": "emergency", "score": 0.0, "maxScore": 15, "lostReasons": []},
        {"name": "法治思维", "key": "legal", "score": 0.0, "maxScore": 15, "lostReasons": []},
        {"name": "逻辑结构", "key": "logic", "score": 0.0, "maxScore": 15, "lostReasons": []},
        {"name": "语言表达", "key": "expression", "score": 0.0, "maxScore": 15, "lostReasons": []},
    ]
    return {
        "totalScore": 0.0,
        "maxScore": 100,
        "grade": "D",
        "dimensions": dimensions,
        "aiComment": "系统判定本次作答仅包含语气词或无有效内容，按无效作答记 0 分。",
        "scoringMode": "screened_zero",
    }


def _persist_result(db: Session, exam_id: str | None, question_id: str, transcript: str, result: dict) -> dict:
    if not exam_id:
        return result

    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer:
        answer = ExamAnswer(exam_id=exam_id, question_id=question_id)
        db.add(answer)
    answer.transcript = transcript
    answer.score_result = result
    answer.answered_at = datetime.now(timezone.utc)
    db.commit()
    return result


@router.post("/transcribe")
async def scoring_transcribe(audio: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    audio_bytes = await audio.read()
    return await transcribe(audio_bytes, filename=audio.filename or "answer.webm")


@router.post("/evaluate")
async def scoring_evaluate(data: EvaluateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Question.id).filter(Question.id == data.questionId).first():
        raise HTTPException(status_code=404, detail="Question not found")

    transcript = str(data.transcript or "").strip()
    if _is_low_value_transcript(transcript):
        return _persist_result(db, data.examId, data.questionId, transcript, _build_zero_score_result())

    return await evaluate_answer(db, data.questionId, data.transcript, data.examId)


@router.get("/result/{exam_id}/{question_id}")
def scoring_result(exam_id: str, question_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_scoring_result(db, exam_id, question_id)
