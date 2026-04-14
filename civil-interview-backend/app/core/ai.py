"""LLM (Qwen) and ASR utilities"""
import asyncio
import base64
import io
import logging
import mimetypes
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Optional, Dict

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

SHORT_AUDIO_PLACEHOLDER = "（录音内容过短，未能识别出有效语音）"
ASR_UNAVAILABLE_PLACEHOLDER = "（当前未配置真实语音转写服务，无法生成可靠文字稿）"
DASHSCOPE_DEFAULT_ASR_MODEL = "qwen3-asr-flash"
DASHSCOPE_CHAT_AUDIO_SAFE_BYTES = 12 * 1024 * 1024
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
_whisper_model = None

# OpenAI-compatible client for Qwen
_client: Optional[OpenAI] = None


def get_client() -> Optional[OpenAI]:
    global _client
    if not settings.qwen_api_key:
        return None
    if _client is None:
        _client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    return _client


def call_llm_api(
    prompt: str,
    system_msg: str = "You are a civil service interview expert. Output JSON only.",
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> Optional[Dict]:
    """Synchronous LLM call (run via executor to avoid blocking)"""
    import json

    client = get_client()
    if not client:
        logger.warning("No QWEN_API_KEY configured, skipping LLM call")
        return None
    try:
        response = client.chat.completions.create(
            model=settings.qwen_model,
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
        logger.error(f"LLM call failed: {e}")
        return None


async def call_llm_api_async(
    prompt: str,
    system_msg: str = "You are a civil service interview expert. Output JSON only.",
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> Optional[Dict]:
    """Async wrapper to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: call_llm_api(prompt, system_msg, temperature, max_tokens)
    )


def _resolve_asr_model() -> str:
    configured = str(settings.qwen_asr_model or "").strip()
    if configured:
        return configured
    if "dashscope.aliyuncs.com" in str(settings.qwen_base_url or ""):
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


def _transcribe_with_dashscope_chat_asr(client: OpenAI, audio_bytes: bytes, filename: str, model: str) -> str:
    data_url = (
        f"data:{_guess_audio_media_type(filename)};base64,"
        f"{base64.b64encode(audio_bytes).decode('ascii')}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": data_url},
                    }
                ],
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


def _get_local_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    import whisper

    model_size = str(os.getenv("WHISPER_MODEL_SIZE", "tiny")).strip() or "tiny"
    logger.info("Loading local Whisper fallback model: %s", model_size)
    _whisper_model = whisper.load_model(model_size)
    return _whisper_model


def _transcribe_with_local_whisper(media_bytes: bytes, filename: str) -> str:
    source_path = None
    suffix = Path(filename or "").suffix.lower() or ".webm"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_file:
            source_path = source_file.name
            source_file.write(media_bytes)
        model = _get_local_whisper_model()
        result = model.transcribe(source_path, language="zh", fp16=False)
        text = str((result or {}).get("text") or "").strip()
        return text
    finally:
        if source_path:
            Path(source_path).unlink(missing_ok=True)


async def transcribe_audio_file(audio_bytes: bytes, filename: str = "answer.webm") -> str:
    """Best-effort ASR with an honest fallback.

    Do not fabricate transcripts. If no real ASR is configured, return a
    placeholder so downstream scoring can degrade conservatively.
    """
    if len(audio_bytes) < 2048:
        return SHORT_AUDIO_PLACEHOLDER

    client = get_client()
    asr_model = _resolve_asr_model()
    if client and asr_model:
        try:
            prepared_bytes, prepared_name = _normalize_media_for_asr(audio_bytes, filename)
            if "dashscope.aliyuncs.com" in str(settings.qwen_base_url or ""):
                text = _transcribe_with_dashscope_chat_asr(client, prepared_bytes, prepared_name, asr_model)
            else:
                file_obj = io.BytesIO(prepared_bytes)
                file_obj.name = prepared_name or "answer.webm"
                response = client.audio.transcriptions.create(
                    model=asr_model,
                    file=file_obj,
                    language="zh",
                )
                text = getattr(response, "text", None)
                if not text and isinstance(response, dict):
                    text = response.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception as exc:
            logger.warning("ASR transcription failed, trying local Whisper fallback: %s", exc)

    try:
        text = _transcribe_with_local_whisper(audio_bytes, filename)
        if text.strip():
            return text.strip()
    except Exception as exc:
        logger.warning("Local Whisper fallback failed, falling back to placeholder: %s", exc)

    return ASR_UNAVAILABLE_PLACEHOLDER


# Province name mapping
PROVINCE_NAMES = {
    "national": "国家公务员考试",
    "beijing": "北京",
    "guangdong": "广东",
    "zhejiang": "浙江",
    "sichuan": "四川",
    "jiangsu": "江苏",
    "henan": "河南",
    "shandong": "山东",
    "hubei": "湖北",
    "hunan": "湖南",
    "liaoning": "辽宁",
    "shanxi": "陕西",
}

DIMENSION_NAMES = {
    "analysis": "综合分析",
    "practical": "实务落地",
    "emergency": "应急应变",
    "legal": "法治思维",
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
}
