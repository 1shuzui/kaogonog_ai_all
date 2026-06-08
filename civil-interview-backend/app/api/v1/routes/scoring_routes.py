"""
这个路由文件提供ASR 转写、答题评分和评分状态接口；它只做请求参数、鉴权依赖和服务层转发，业务规则尽量留在 service 里。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import re
import shutil
from importlib.util import find_spec as importlib_util_find

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.ai import _resolve_asr_model, _resolve_remote_asr_model
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
async def scoring_transcribe(
    audio: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    scoring_transcribe 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param audio: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    audio_bytes = await audio.read()
    return await transcribe(audio_bytes, filename=audio.filename or "answer.webm", db=db)


@router.get("/asr-status")
def scoring_asr_status(current_user: AuthUser = Depends(get_current_user)):
    """
    scoring_asr_status 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    asr_model = _resolve_asr_model()
    remote_asr_model = _resolve_remote_asr_model()
    funasr_provider = str(settings.asr_provider or "").strip().lower()
    funasr_dependency_ready = (
        importlib_util_find("funasr_onnx") is not None
        or importlib_util_find("funasr") is not None
    )
    ffmpeg_ready = shutil.which("ffmpeg") is not None
    funasr_ready = funasr_provider in {"funasr", "funasr_onnx", "paraformer", "paraformer_onnx"} and funasr_dependency_ready and ffmpeg_ready
    remote_ready = bool(settings.llm_api_key and remote_asr_model)

    ready = funasr_ready or remote_ready
    mode = "funasr_onnx_vad" if funasr_ready else "remote_asr" if remote_ready else "unavailable"
    model = asr_model if ready else ""
    message = "语音转写服务已就绪" if ready else "语音转写服务未就绪，请检查 FunASR/ONNX 依赖、模型缓存和 ffmpeg。"
    return {
        "ready": ready,
        "mode": mode,
        "provider": settings.asr_provider,
        "model": model,
        "vadModel": settings.funasr_vad_model_name,
        "puncModel": settings.funasr_punc_model_name if settings.funasr_enable_punc else "",
        "funasrReady": funasr_ready,
        "funasrDependencyReady": funasr_dependency_ready,
        "remoteAsrReady": remote_ready,
        "ffmpegReady": ffmpeg_ready,
        "message": message,
    }


@router.post("/evaluate")
async def scoring_evaluate(data: EvaluateRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    scoring_evaluate 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
    """
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
    """
    scoring_result 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    本模块位于 FastAPI 路由边界，负责把端侧请求收束到服务层，便于统一鉴权、错误语义和审核口径。

    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return get_scoring_result(db, exam_id, question_id)
