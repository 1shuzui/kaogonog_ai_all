"""
这个文件封装 LLM 和 ASR 调用；FunASR、远程模型和降级提示都在这里收口，避免评分服务直接知道太多供应商细节。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import asyncio
import base64
import hashlib
import io
import logging
import mimetypes
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import tempfile
from typing import Optional, Dict

from openai import OpenAI

from app.core.config import settings
from app.core.redis_cache import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

SHORT_AUDIO_PLACEHOLDER = "（录音内容过短，未能识别出有效语音）"
ASR_UNAVAILABLE_PLACEHOLDER = "（当前未配置真实语音转写服务，无法生成可靠文字稿）"
DASHSCOPE_DEFAULT_ASR_MODEL = "qwen3-asr-flash"
DASHSCOPE_CHAT_AUDIO_SAFE_BYTES = 12 * 1024 * 1024
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
ASR_SIMPLIFIED_CHINESE_PROMPT = (
    "请将音频完整转写为简体中文普通话文本。"
    "保留考生原意，不要翻译成英文，不要输出繁体字，不要添加总结、标点说明或无关内容。"
)
LLM_MAX_RETRIES = 3
LLM_RETRY_BACKOFF_BASE = 1.5
ASR_SAMPLE_RATE = 16000
ASR_CACHE_SCHEMA = "funasr-onnx-v4"
FUNASR_PROVIDER_ALIASES = {"funasr", "funasr_onnx", "paraformer", "paraformer_onnx"}
FUNASR_ONNX_CACHE: dict[tuple, dict[str, object]] = {}
LAST_ASR_TRACE: dict = {}
FUNASR_MIN_AUDIO_RMS = 0.0008
FUNASR_MIN_SEGMENT_RMS = 0.001
FUNASR_VAD_MERGE_GAP_MS = 250
FUNASR_SEGMENT_COMMA_GAP_MS = 250
FUNASR_SEGMENT_PERIOD_GAP_MS = 650
FUNASR_SENTENCE_PUNCTUATION = "，。！？；、,.!?;"
FUNASR_CONTEXTUAL_CORRECTIONS = (
    ("是是在", "是在"),
    ("反馈机机制", "反馈机制"),
    ("快速反馈机机制", "快速反馈机制"),
    ("差异化的预言", "差异化的预研"),
    ("差异化预言", "差异化预研"),
    ("敢闯敢式", "敢闯敢试"),
    ("敢闯敢视", "敢闯敢试"),
    ("营兆环境", "营商环境"),
    ("主管复门", "主管部门"),
    ("执轰复门", "执法部门"),
    ("群众实机问题", "群众实际问题"),
    ("群众实际问提", "群众实际问题"),
    ("基层治里", "基层治理"),
    ("政策请斜", "政策倾斜"),
    ("动态调证", "动态调整"),
    ("水土不府", "水土不服"),
    ("落地适配行", "落地适配性"),
    ("试点价直", "试点价值"),
    ("万能摸板", "万能模板"),
    ("稳扎稳大", "稳扎稳打"),
    ("农民宫", "农民工"),
    ("消防通到", "消防通道"),
    ("商家信用品集", "商家信用评级"),
    ("消费者", "消费者"),
)

# OpenAI-compatible client for the configured LLM provider
_client: Optional[OpenAI] = None
_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")
    return _executor


def get_client() -> Optional[OpenAI]:
    """
    get_client 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    AI 网关承载 ASR/LLM 供应商差异，注释重点记录降级策略和真实服务缺失时的边界。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    global _client
    if not settings.llm_api_key:
        return None
    if _client is None:
        _client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    return _client


def call_llm_api(
    prompt: str,
    system_msg: str = "You are a civil service interview expert. Output JSON only.",
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> Optional[Dict]:
    """
    call_llm_api 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    AI 网关承载 ASR/LLM 供应商差异，注释重点记录降级策略和真实服务缺失时的边界。

    @param prompt: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param system_msg: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param temperature: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param max_tokens: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    import json

    client = get_client()
    if not client:
        logger.warning("No LLM_API_KEY configured, skipping LLM call")
        return None

    last_error = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            last_error = e
            if attempt < LLM_MAX_RETRIES - 1:
                delay = LLM_RETRY_BACKOFF_BASE ** attempt
                logger.warning("LLM call attempt %s/%s failed, retrying in %.1fs: %s", attempt + 1, LLM_MAX_RETRIES, delay, e)
                time.sleep(delay)
            else:
                logger.error("LLM call failed after %s attempts: %s", LLM_MAX_RETRIES, e)

    return None


async def call_llm_api_async(
    prompt: str,
    system_msg: str = "You are a civil service interview expert. Output JSON only.",
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> Optional[Dict]:
    """
    call_llm_api_async 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    AI 网关承载 ASR/LLM 供应商差异，注释重点记录降级策略和真实服务缺失时的边界。

    @param prompt: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param system_msg: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param temperature: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param max_tokens: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _get_executor(), lambda: call_llm_api(prompt, system_msg, temperature, max_tokens)
    )


def _resolve_asr_model() -> str:
    if _is_funasr_provider():
        return str(settings.funasr_model_name or "").strip()
    return _resolve_remote_asr_model()


def _resolve_remote_asr_model() -> str:
    configured = str(settings.llm_asr_model or "").strip()
    if configured:
        return configured
    if settings.llm_provider == "qwen" or "dashscope.aliyuncs.com" in str(settings.llm_base_url or ""):
        return DASHSCOPE_DEFAULT_ASR_MODEL
    return ""


def _extract_text_from_message_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
                continue
            text = getattr(item, "text", None)
            if text:
                parts.append(str(text))
        return "".join(parts).strip()
    return str(content or "").strip()


def _guess_audio_media_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or "audio/webm"


def _should_normalize_media_for_asr(filename: str, media_bytes: bytes) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return suffix in VIDEO_EXTENSIONS or len(media_bytes) > DASHSCOPE_CHAT_AUDIO_SAFE_BYTES


def _normalize_media_for_asr(media_bytes: bytes, filename: str) -> tuple[bytes, str]:
    suffix = Path(filename or "").suffix.lower() or ".bin"
    if not _should_normalize_media_for_asr(filename, media_bytes):
        return media_bytes, filename or f"answer{suffix}"

    source_path = None
    target_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_file:
            source_path = source_file.name
            source_file.write(media_bytes)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as target_file:
            target_path = target_file.name

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "32k",
                target_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        normalized = Path(target_path).read_bytes()
        if normalized:
            stem = Path(filename or "answer").stem or "answer"
            return normalized, f"{stem}_asr.mp3"
    except Exception as exc:
        logger.warning("Media normalization for ASR failed, using original file: %s", exc)
    finally:
        if source_path:
            Path(source_path).unlink(missing_ok=True)
        if target_path:
            Path(target_path).unlink(missing_ok=True)

    return media_bytes, filename or f"answer{suffix}"


def _decode_media_to_wav(media_bytes: bytes, filename: str) -> str:
    suffix = Path(filename or "").suffix.lower() or ".webm"
    source_path = None
    target_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_file:
            source_path = source_file.name
            source_file.write(media_bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as target_file:
            target_path = target_file.name

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(ASR_SAMPLE_RATE),
                "-sample_fmt",
                "s16",
                target_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return target_path
    except FileNotFoundError as exc:
        raise RuntimeError("系统未安装 ffmpeg，无法为 FunASR 预处理音频") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("音频格式转换失败，无法进行语音识别") from exc
    finally:
        if source_path:
            Path(source_path).unlink(missing_ok=True)


def _configure_funasr_cache_env() -> str:
    cache_dir = Path(settings.modelscope_cache).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = Path(__file__).resolve().parents[2] / cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    credentials_dir = cache_dir / ".modelscope" / "credentials"
    credentials_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MODELSCOPE_CACHE", str(cache_dir))
    os.environ.setdefault("MODELSCOPE_CREDENTIALS_PATH", str(credentials_dir))
    os.environ.setdefault("HF_HOME", str(cache_dir / "hf_home"))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "huggingface"))
    return str(cache_dir)


def _funasr_device_id():
    device = str(settings.asr_device or "cpu").strip().lower()
    if device in {"cpu", "-1"}:
        return "-1"
    if device.startswith("cuda"):
        parts = device.split(":", 1)
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if device.startswith("gpu"):
        parts = device.split(":", 1)
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return device


def _is_funasr_provider() -> bool:
    return str(settings.asr_provider or "").strip().lower() in FUNASR_PROVIDER_ALIASES


def _get_funasr_onnx_models() -> dict[str, object]:
    cache_key = (
        settings.funasr_model_name,
        settings.funasr_vad_model_name,
        settings.funasr_punc_model_name if settings.funasr_enable_punc else "",
        settings.funasr_quantize,
        settings.funasr_vad_max_end_sil_ms,
        settings.asr_device,
        settings.asr_intra_op_num_threads,
    )
    if cache_key in FUNASR_ONNX_CACHE:
        return FUNASR_ONNX_CACHE[cache_key]

    try:
        from funasr_onnx import CT_Transformer, Fsmn_vad, Paraformer
    except ImportError as exc:
        raise RuntimeError("缺少 funasr-onnx / onnxruntime 依赖，无法使用 Paraformer ONNX ASR") from exc

    cache_dir = _configure_funasr_cache_env()
    device_id = _funasr_device_id()
    common_kwargs = {
        "device_id": device_id,
        "quantize": settings.funasr_quantize,
        "intra_op_num_threads": settings.asr_intra_op_num_threads,
        "cache_dir": cache_dir,
    }
    logger.info("Loading FunASR ONNX Paraformer: %s", settings.funasr_model_name)
    asr_model = Paraformer(settings.funasr_model_name, batch_size=1, **common_kwargs)
    logger.info("Loading FunASR ONNX FSMN-VAD: %s", settings.funasr_vad_model_name)
    vad_model = Fsmn_vad(
        settings.funasr_vad_model_name,
        batch_size=1,
        max_end_sil=settings.funasr_vad_max_end_sil_ms,
        **common_kwargs,
    )
    punc_model = None
    if settings.funasr_enable_punc and settings.funasr_punc_model_name:
        logger.info("Loading FunASR ONNX punctuation model: %s", settings.funasr_punc_model_name)
        punc_model = CT_Transformer(settings.funasr_punc_model_name, **common_kwargs)

    models = {"asr": asr_model, "vad": vad_model, "punc": punc_model}
    FUNASR_ONNX_CACHE[cache_key] = models
    return models


def _extract_funasr_text(result) -> str:
    if isinstance(result, tuple):
        return _extract_funasr_text(result[0]) if result else ""
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, dict):
                value = item.get("text") or item.get("preds") or item.get("sentence")
                if value:
                    parts.append(_extract_funasr_text(value))
            elif item not in (None, ""):
                parts.append(_extract_funasr_text(item))
        return "".join(parts).strip()
    if isinstance(result, dict):
        return _extract_funasr_text(result.get("text") or result.get("preds") or result.get("sentence") or "")
    return str(result or "").strip()


def _normalize_funasr_segment_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def _join_funasr_segments(parts: list[tuple[str, int, int]]) -> str:
    transcript = ""
    previous_end = None
    for text, start, end in parts:
        text = _normalize_funasr_segment_text(text)
        if not text:
            continue
        if transcript and previous_end is not None:
            gap_ms = max(0, int((start - previous_end) * 1000 / ASR_SAMPLE_RATE))
            last_char = transcript[-1]
            if gap_ms >= FUNASR_SEGMENT_PERIOD_GAP_MS and last_char not in FUNASR_SENTENCE_PUNCTUATION:
                transcript += "。"
            elif gap_ms >= FUNASR_SEGMENT_COMMA_GAP_MS and last_char not in FUNASR_SENTENCE_PUNCTUATION:
                transcript += "，"
        transcript += text
        previous_end = end
    return transcript.strip()


def _postprocess_funasr_transcript(text: str) -> str:
    transcript = str(text or "").strip()
    if not transcript:
        return ""
    transcript = re.sub(r"\s+", "", transcript)
    for old, new in FUNASR_CONTEXTUAL_CORRECTIONS:
        transcript = transcript.replace(old, new)
    transcript = re.sub(r"(接近)(?:[，,、]?\1)+(?=的)", r"\1", transcript)
    transcript = re.sub(r"(人员)(?:[，,、]?\1)+(?=能力)", r"\1", transcript)
    transcript = re.sub(r"(点的)+点上", "点上", transcript)
    transcript = re.sub(r"(预研)(?:[，,、]?\1)+", r"\1", transcript)
    transcript = re.sub(r"(机制)(?:[，,、]?\1)+", r"\1", transcript)
    transcript = re.sub(r"(你好[，,。]?){2,}", "你好，", transcript)
    transcript = re.sub(r"(现在开始了?){2,}", "现在开始", transcript)
    transcript = re.sub(r"(防单持)(?:[，,、]?\1)+", r"\1", transcript)
    transcript = re.sub(r"水土不服试点(?=一般|通常|往往|会)", "水土不服，试点", transcript)
    transcript = re.sub(r"推广失败不能直接否\s*定", "推广失败不能直接否定", transcript)
    transcript = re.sub(r"([，。！？；、])\1+", r"\1", transcript)
    return transcript.strip()


def _audio_rms(waveform) -> float:
    try:
        import numpy as np

        if waveform is None or waveform.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(waveform.astype("float32")))))
    except Exception:
        return 0.0


def _merge_vad_segments(raw_segments, audio_length: int) -> list[tuple[int, int]]:
    if not raw_segments:
        return [(0, audio_length)]
    if isinstance(raw_segments, list) and raw_segments and isinstance(raw_segments[0], list):
        first = raw_segments[0]
        segments = first if first and isinstance(first[0], (list, tuple)) else raw_segments
    else:
        segments = raw_segments

    merge_gap_samples = int(FUNASR_VAD_MERGE_GAP_MS * ASR_SAMPLE_RATE / 1000)
    max_segment_samples = int(max(settings.asr_max_segment_seconds, 1.0) * ASR_SAMPLE_RATE)
    speech_segments: list[tuple[int, int]] = []
    for segment in segments:
        if not isinstance(segment, (list, tuple)) or len(segment) < 2:
            continue
        try:
            start_ms = int(float(segment[0]))
            end_ms = int(float(segment[1]))
        except (TypeError, ValueError):
            continue
        start = max(0, int(start_ms * ASR_SAMPLE_RATE / 1000))
        end = min(audio_length, int(end_ms * ASR_SAMPLE_RATE / 1000))
        if end <= start:
            continue
        speech_segments.append((start, end))

    if not speech_segments:
        return [(0, audio_length)]

    speech_segments.sort()
    merged_speech: list[tuple[int, int]] = []
    for start, end in speech_segments:
        if merged_speech and start - merged_speech[-1][1] <= merge_gap_samples:
            previous_start, previous_end = merged_speech[-1]
            merged_speech[-1] = (previous_start, max(previous_end, end))
        else:
            merged_speech.append((start, end))

    padding_samples = int(max(settings.asr_segment_padding_ms, 0) * ASR_SAMPLE_RATE / 1000)
    normalized: list[tuple[int, int]] = []
    for index, (speech_start, speech_end) in enumerate(merged_speech):
        previous_end = merged_speech[index - 1][1] if index > 0 else 0
        next_start = merged_speech[index + 1][0] if index + 1 < len(merged_speech) else audio_length
        start = max(0, speech_start - padding_samples)
        end = min(audio_length, speech_end + padding_samples)
        start = max(start, (previous_end + speech_start) // 2)
        end = min(end, (speech_end + next_start) // 2)
        while end - start > max_segment_samples:
            chunk_end = min(end, start + max_segment_samples)
            normalized.append((start, chunk_end))
            start = chunk_end
        normalized.append((start, end))
    return normalized or [(0, audio_length)]


def _punctuate_funasr_text(text: str, punc_model) -> str:
    text = str(text or "").strip()
    if not text or punc_model is None:
        return text
    try:
        result = punc_model(text)
        return _extract_funasr_text(result) or text
    except Exception as exc:
        logger.warning("FunASR punctuation recovery failed, using raw transcript: %s", exc)
        return text


def _set_asr_trace(**updates) -> dict:
    LAST_ASR_TRACE.clear()
    LAST_ASR_TRACE.update({
        "provider": settings.asr_provider,
        "mode": "funasr_onnx_vad" if _is_funasr_provider() else "remote_asr",
        "model": _resolve_asr_model(),
        "vadModel": settings.funasr_vad_model_name,
        "puncModel": settings.funasr_punc_model_name if settings.funasr_enable_punc else "",
        "cacheHit": False,
        "segmentCount": 0,
        "recognizedSegmentCount": 0,
        "durationSeconds": 0.0,
        "audioRms": 0.0,
        "transcriptChars": 0,
        "status": "started",
        "message": "",
    })
    LAST_ASR_TRACE.update(updates)
    return dict(LAST_ASR_TRACE)


def _transcribe_with_funasr_onnx(wav_path: str) -> str:
    import librosa

    models = _get_funasr_onnx_models()
    waveform, _ = librosa.load(wav_path, sr=ASR_SAMPLE_RATE, mono=True)
    duration_seconds = round(float(waveform.size or 0) / ASR_SAMPLE_RATE, 2)
    if waveform.size == 0:
        _set_asr_trace(status="empty_audio", message="音频为空，未能识别出有效语音")
        return ""
    audio_rms = _audio_rms(waveform)
    if audio_rms < FUNASR_MIN_AUDIO_RMS:
        logger.info("FunASR skipped near-silent audio before VAD")
        _set_asr_trace(
            status="silent_audio",
            durationSeconds=duration_seconds,
            audioRms=round(audio_rms, 6),
            message="录音音量过低，未识别到有效语音",
        )
        return ""

    vad_model = models["vad"]
    raw_segments = vad_model(waveform)
    segments = _merge_vad_segments(raw_segments, int(waveform.shape[-1]))
    logger.info("FunASR VAD split audio into %s segment(s)", len(segments))

    asr_model = models["asr"]
    parts: list[tuple[str, int, int]] = []
    for index, (start, end) in enumerate(segments, start=1):
        segment_audio = waveform[start:end]
        if segment_audio.size < int(0.2 * ASR_SAMPLE_RATE):
            continue
        if _audio_rms(segment_audio) < FUNASR_MIN_SEGMENT_RMS:
            logger.debug("FunASR segment %s/%s skipped by low RMS", index, len(segments))
            continue
        result = asr_model(segment_audio)
        text = _extract_funasr_text(result)
        if text:
            parts.append((text, start, end))
        logger.debug("FunASR segment %s/%s transcribed chars=%s", index, len(segments), len(text))

    transcript = _join_funasr_segments(parts)
    transcript = _punctuate_funasr_text(transcript, models.get("punc"))
    transcript = _postprocess_funasr_transcript(transcript)
    _set_asr_trace(
        status="ok" if transcript else "no_speech",
        segmentCount=len(segments),
        recognizedSegmentCount=len(parts),
        durationSeconds=duration_seconds,
        audioRms=round(audio_rms, 6),
        transcriptChars=len(transcript),
        message="" if transcript else "未识别到有效语音，请重新录制",
    )
    return transcript


def _transcribe_with_funasr(media_bytes: bytes, filename: str) -> str:
    wav_path = None
    try:
        wav_path = _decode_media_to_wav(media_bytes, filename)
        return _transcribe_with_funasr_onnx(wav_path)
    finally:
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)


def _transcribe_with_dashscope_chat_asr(
    client: OpenAI,
    audio_bytes: bytes,
    filename: str,
    model: str,
    *,
    include_prompt: bool = True,
) -> str:
    data_url = (
        f"data:{_guess_audio_media_type(filename)};base64,"
        f"{base64.b64encode(audio_bytes).decode('ascii')}"
    )
    content = []
    if include_prompt:
        content.append(
            {
                "type": "text",
                "text": ASR_SIMPLIFIED_CHINESE_PROMPT,
            }
        )
    content.append(
        {
            "type": "input_audio",
            "input_audio": {"data": data_url},
        }
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
        extra_body={
            "asr_options": {
                "language": "zh",
                "enable_itn": False,
            }
        },
        timeout=settings.llm_timeout_seconds,
    )
    return _extract_text_from_message_content(response.choices[0].message.content)


async def transcribe_audio_file_with_meta(audio_bytes: bytes, filename: str = "answer.webm") -> dict:
    """
    transcribe_audio_file_with_meta 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    AI 网关承载 ASR/LLM 供应商差异，注释重点记录降级策略和真实服务缺失时的边界。

    @param audio_bytes: 上传音频的二进制内容；进入 ASR 前用于缓存和切片，避免长音频直接压垮模型。
    @param filename: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    media_hash = hashlib.sha256(audio_bytes).hexdigest()
    base_meta = {
        "provider": settings.asr_provider,
        "mode": "funasr_onnx_vad" if _is_funasr_provider() else "remote_asr",
        "model": _resolve_asr_model(),
        "vadModel": settings.funasr_vad_model_name,
        "puncModel": settings.funasr_punc_model_name if settings.funasr_enable_punc else "",
        "cacheHit": False,
        "audioBytes": len(audio_bytes),
        "audioSha256": media_hash,
        "filename": filename or "answer.webm",
        "status": "started",
        "message": "",
    }
    if len(audio_bytes) < 2048:
        meta = {**base_meta, "status": "too_short", "message": "录音内容过短，请重新录制"}
        return {"transcript": SHORT_AUDIO_PLACEHOLDER, "asrMeta": meta, "needsRetry": True, "message": meta["message"]}

    asr_model = _resolve_asr_model()
    remote_asr_model = _resolve_remote_asr_model()
    asr_cache_scope = hashlib.sha256(
        "|".join(
            [
                settings.asr_provider,
                asr_model,
                remote_asr_model,
                settings.funasr_vad_model_name,
                settings.funasr_punc_model_name if settings.funasr_enable_punc else "",
                "zh",
                ASR_SIMPLIFIED_CHINESE_PROMPT,
                ASR_CACHE_SCHEMA,
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    asr_cache_key = f"asr:transcript:{asr_cache_scope}:{media_hash}"
    cached_transcript = await cache_get_json(asr_cache_key)
    if isinstance(cached_transcript, str) and cached_transcript.strip():
        logger.info("ASR cache hit: %s", asr_cache_key)
        transcript = cached_transcript.strip()
        meta = {**base_meta, "cacheHit": True, "status": "ok", "transcriptChars": len(transcript)}
        return {"transcript": transcript, "asrMeta": meta, "needsRetry": False, "message": ""}

    if _is_funasr_provider():
        try:
            text = _transcribe_with_funasr(audio_bytes, filename)
            trace = dict(LAST_ASR_TRACE)
            if text.strip():
                transcript = text.strip()
                await cache_set_json(
                    asr_cache_key,
                    transcript,
                    settings.redis_cache_ttl_transcript,
                )
                meta = {**base_meta, **trace, "audioSha256": media_hash, "audioBytes": len(audio_bytes), "status": "ok", "transcriptChars": len(transcript)}
                return {"transcript": transcript, "asrMeta": meta, "needsRetry": False, "message": ""}
            message = trace.get("message") or "未识别到有效语音，请重新录制"
            meta = {**base_meta, **trace, "audioSha256": media_hash, "audioBytes": len(audio_bytes), "status": trace.get("status") or "no_speech", "message": message}
            return {"transcript": "（未识别到有效语音，请重新录制）", "asrMeta": meta, "needsRetry": True, "message": message}
        except Exception as exc:
            logger.warning("FunASR transcription failed, falling back to remote ASR if configured: %s", exc)
            base_meta = {**base_meta, "status": "funasr_error", "message": str(exc)[:200]}

    client = get_client()
    if client and remote_asr_model:
        try:
            prepared_bytes, prepared_name = _normalize_media_for_asr(audio_bytes, filename)
            if "dashscope.aliyuncs.com" in str(settings.llm_base_url or ""):
                try:
                    text = _transcribe_with_dashscope_chat_asr(client, prepared_bytes, prepared_name, remote_asr_model)
                except Exception as prompt_exc:
                    logger.warning("DashScope ASR prompt request failed, retrying audio-only: %s", prompt_exc)
                    text = _transcribe_with_dashscope_chat_asr(
                        client,
                        prepared_bytes,
                        prepared_name,
                        remote_asr_model,
                        include_prompt=False,
                    )
            else:
                file_obj = io.BytesIO(prepared_bytes)
                file_obj.name = prepared_name or "answer.webm"
                try:
                    response = client.audio.transcriptions.create(
                        model=remote_asr_model,
                        file=file_obj,
                        language="zh",
                        prompt=ASR_SIMPLIFIED_CHINESE_PROMPT,
                    )
                except TypeError:
                    file_obj.seek(0)
                    response = client.audio.transcriptions.create(
                        model=remote_asr_model,
                        file=file_obj,
                        language="zh",
                    )
                text = getattr(response, "text", None)
                if not text and isinstance(response, dict):
                    text = response.get("text")
            if isinstance(text, str) and text.strip():
                transcript = text.strip()
                await cache_set_json(
                    asr_cache_key,
                    transcript,
                    settings.redis_cache_ttl_transcript,
                )
                meta = {**base_meta, "mode": "remote_asr", "status": "ok", "transcriptChars": len(transcript)}
                return {"transcript": transcript, "asrMeta": meta, "needsRetry": False, "message": ""}
        except Exception as exc:
            logger.warning("Remote ASR transcription failed, falling back to placeholder: %s", exc)
            base_meta = {**base_meta, "status": "remote_error", "message": str(exc)[:200]}

    message = "语音转写服务暂不可用，请稍后重试"
    meta = {**base_meta, "status": base_meta.get("status") or "unavailable", "message": base_meta.get("message") or message}
    return {"transcript": ASR_UNAVAILABLE_PLACEHOLDER, "asrMeta": meta, "needsRetry": True, "message": message}


async def transcribe_audio_file(audio_bytes: bytes, filename: str = "answer.webm") -> str:
    """
    transcribe_audio_file 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    AI 网关承载 ASR/LLM 供应商差异，注释重点记录降级策略和真实服务缺失时的边界。

    @param audio_bytes: 上传音频的二进制内容；进入 ASR 前用于缓存和切片，避免长音频直接压垮模型。
    @param filename: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    result = await transcribe_audio_file_with_meta(audio_bytes, filename=filename)
    return str(result.get("transcript") or "")


# Province name mapping
PROVINCE_NAMES = {
    "national": "国家公务员考试",
    "beijing": "北京",
    "shanghai": "上海",
    "guangdong": "广东",
    "zhejiang": "浙江",
    "sichuan": "四川",
    "jiangsu": "江苏",
    "anhui": "安徽",
    "henan": "河南",
    "shandong": "山东",
    "hubei": "湖北",
    "hunan": "湖南",
    "hebei": "河北",
    "fujian": "福建",
    "liaoning": "辽宁",
    "shanxi": "陕西",
}

DIMENSION_NAMES = {
    "analysis": "综合分析",
    "practical": "实务落地",
    "emergency": "应急应变",
    "legal": "行政思维",
    "logic": "逻辑结构",
    "expression": "语言表达",
}

POSITION_NAMES = {
    "tax": "税务系统",
    "customs": "海关系统",
    "police": "公安系统",
    "court": "法院系统",
    "procurate": "检察系统",
    "market": "市场监管",
    "general": "综合管理",
    "township": "乡镇基层",
    "finance": "银保监会",
    "diplomacy": "外交系统",
    "prison": "监狱系统",
    "bank": "银行招考",
    "medical": "医疗卫生",
    "jiangsu_a": "综合管理岗",
    "jiangsu_b": "社会科学专技岗",
    "jiangsu_c": "自然科学专技岗",
    "jiangsu_d": "中小学教师岗",
    "jiangsu_e": "医疗卫生岗",
    "jiangsu_worker": "工勤技能岗",
}
