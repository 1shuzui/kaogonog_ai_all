import importlib.util
import re
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.ai import _resolve_asr_model
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Question
from app.schemas.common import AuthUser, EvaluateRequest
from app.services.scoring_service import _build_zero_score_result, _persist_result, transcribe, evaluate_answer, get_scoring_result

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


@router.post("/transcribe")
async def scoring_transcribe(audio: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    audio_bytes = await audio.read()
    return await transcribe(audio_bytes, filename=audio.filename or "answer.webm")


@router.get("/asr-status")
def scoring_asr_status(current_user: AuthUser = Depends(get_current_user)):
    asr_model = _resolve_asr_model()
    remote_ready = bool(settings.llm_api_key and asr_model)
    ffmpeg_ready = shutil.which("ffmpeg") is not None
    local_whisper_ready = importlib.util.find_spec("whisper") is not None and ffmpeg_ready

    ready = remote_ready or local_whisper_ready
    mode = "remote_asr" if remote_ready else "local_whisper" if local_whisper_ready else "unavailable"
    model = asr_model if remote_ready else "whisper" if local_whisper_ready else ""
    message = "语音转写服务已就绪" if ready else "语音转写服务未就绪，请检查 ASR 模型配置、Whisper 依赖和 ffmpeg。"
    return {
        "ready": ready,
        "mode": mode,
        "provider": settings.llm_provider,
        "model": model,
        "remoteAsrReady": remote_ready,
        "localWhisperReady": local_whisper_ready,
        "ffmpegReady": ffmpeg_ready,
        "message": message,
    }


@router.post("/evaluate")
async def scoring_evaluate(data: EvaluateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Question.id).filter(Question.id == data.questionId).first():
        raise HTTPException(status_code=404, detail="Question not found")

    transcript = str(data.transcript or "").strip()
    if _is_low_value_transcript(transcript):
        return _persist_result(
            db,
            data.examId,
            data.questionId,
            transcript,
            _build_zero_score_result("系统判定本次作答仅包含语气词或无有效内容，按无效作答记 0 分。"),
        )

    return await evaluate_answer(db, data.questionId, data.transcript, data.examId)


@router.get("/result/{exam_id}/{question_id}")
def scoring_result(exam_id: str, question_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_scoring_result(db, exam_id, question_id)
