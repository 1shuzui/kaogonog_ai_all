"""
评分路由，提供音频转写、ASR 状态检查、答案评分和历史评分结果读取接口。

路由层负责接收上传文件、保存临时媒体、做基础文本清洗和权限校验；真正的 ASR、视频行为分析、能力维度评分和缓存策略都在服务层。
这里要维持两个边界：能力维度用于评价学生答题能力，题型分类只用于训练筛选；录音文件过长时应由 FunASR/VAD 切句处理，
不能把整段长音频直接塞给模型。

@param: FastAPI 注入上传文件、请求体、当前用户和数据库 Session。
@return: 返回转写文本、ASR 服务状态、评分详情或已保存评分结果。
@raises HTTPException: 未登录、文件格式不支持、ASR 不可用、题目不存在或评分失败时返回 HTTP 错误。
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


def _safe_answer_meta(raw_meta) -> dict:
    """
    清洗端侧传入的答题元信息。

    答题用时、跳过原因和 ASR 失败类型属于复盘展示和扣量解释，不参与模型打分；白名单合入可以避免端侧把任意字段写进评分结果。

    @param raw_meta: 小程序评分请求里的 answerMeta 字典。
    @return: 允许持久化到 score_result 的安全字段。
    @raises: 不主动抛出异常；异常输入按空字典处理。
    """
    if not isinstance(raw_meta, dict):
        return {}

    def safe_seconds(value) -> int:
        try:
            return max(0, int(float(value or 0)))
        except (TypeError, ValueError):
            return 0

    result: dict = {}
    timing = raw_meta.get("answerTiming")
    if isinstance(timing, dict):
        result["answerTiming"] = {
            "actualSeconds": safe_seconds(timing.get("actualSeconds")),
            "standardSeconds": safe_seconds(timing.get("standardSeconds")),
            "overtimeSeconds": safe_seconds(timing.get("overtimeSeconds")),
        }
    for key in ("skipReason", "asrFailureType", "asrStatus", "asrMessage"):
        value = str(raw_meta.get(key) or "").strip()
        if value:
            result[key] = value[:120]
    return result


def _merge_answer_meta(result: dict, answer_meta: dict) -> dict:
    """
    将安全答题元信息并入评分结果。

    评分服务仍只根据文字稿和题目打分；这里的合并只是为了结果页、历史页和客服排查能解释为什么没有文字稿或为什么超时。

    @param result: 评分服务返回的结果。
    @param answer_meta: `_safe_answer_meta` 清洗后的字段。
    @return: 合并后的评分结果。
    @raises: 不主动包装底层异常。
    """
    if not answer_meta:
        return result
    merged = {**(result or {})}
    for key, value in answer_meta.items():
        if key == "asrStatus":
            media_record = merged.get("mediaRecord") if isinstance(merged.get("mediaRecord"), dict) else {}
            asr_meta = media_record.get("asrMeta") if isinstance(media_record.get("asrMeta"), dict) else {}
            media_record["asrMeta"] = {**asr_meta, "status": value}
            merged["mediaRecord"] = media_record
        else:
            merged[key] = value
    return merged


@router.post("/transcribe")
async def scoring_transcribe(
    audio: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    语音/视频转写路由。

    这里只负责接收上传文件和当前用户，真实 ASR、VAD 分段、缓存和占位文本策略由 scoring_service/core.ai 处理。

    @param file: 上传的音频或视频文件。
    @param questionId: 可选题目 ID，用于后续上下文纠错。
    @param current_user: Bearer token 解析出的当前用户。
    @return: 转写文本、ASR 状态和诊断信息。
    @raises HTTPException: 未登录、文件异常或 ASR 服务错误时抛出。
    """
    audio_bytes = await audio.read()
    return await transcribe(audio_bytes, filename=audio.filename or "answer.webm", db=db)


@router.get("/asr-status")
def scoring_asr_status(current_user: AuthUser = Depends(get_current_user)):
    """
    ASR 服务状态路由。

    该接口给前端和运维判断当前是否启用真实转写，避免页面把“未配置服务”的占位文本当作考生稿件。

    @param current_user: Bearer token 解析出的当前用户。
    @return: ASR provider、模型和可用状态。
    @raises HTTPException: 未登录时抛出 401。
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
    面试答案评分路由。

    路由层负责合并表单、文本答案和可选媒体文件；评分维度、采分点、ASR 和视频观察都由服务层统一处理。

    @param request: FastAPI 原始请求，用于读取 multipart 或 JSON。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 评分结果、文字稿、能力维度和建议。
    @raises HTTPException: 未登录、题目不存在、答案缺失或评分服务失败时抛出。
    """
    if not db.query(Question.id).filter(Question.id == data.questionId).first():
        raise HTTPException(status_code=404, detail="Question not found")

    transcript = str(data.transcript or "").strip()
    answer_meta = _safe_answer_meta(data.answerMeta)
    if _is_low_value_transcript(transcript):
        return _persist_result(
            db,
            data.examId,
            data.questionId,
            transcript,
            _merge_answer_meta(
                _build_zero_score_result("系统判定本次作答仅包含语气词或无有效内容，按无效作答记 0 分。"),
                answer_meta,
            ),
        )

    result = await evaluate_answer(db, data.questionId, data.transcript, data.examId)
    if not answer_meta:
        return result
    return _persist_result(
        db,
        data.examId,
        data.questionId,
        transcript,
        _merge_answer_meta(result, answer_meta),
    )


@router.get("/result/{exam_id}/{question_id}")
def scoring_result(exam_id: str, question_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    读取评分结果详情的路由。

    结果页按 resultId 回看历史评分，路由层只做鉴权和服务转发，避免前端直接拼历史记录结构。

    @param result_id: 评分结果或历史记录标识。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 评分结果详情。
    @raises HTTPException: 未登录、结果不存在或无权访问时抛出。
    """
    return get_scoring_result(db, exam_id, question_id)
