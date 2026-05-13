"""LLM and ASR utilities"""
import asyncio
import base64
import io
import importlib.util
import logging
import mimetypes
import os
from pathlib import Path
import shutil
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

# OpenAI-compatible client for the configured LLM provider
_client: Optional[OpenAI] = None


def get_client() -> Optional[OpenAI]:
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
    """Synchronous LLM call (run via executor to avoid blocking)"""
    import json

    client = get_client()
    if not client:
        logger.warning("No LLM_API_KEY configured, skipping LLM call")
        return None
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
    except Exception:
        logger.exception(
            "LLM call failed",
            extra={"event": "llm.call.failed", "provider": settings.llm_provider, "model": settings.llm_model},
        )
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


def _asr_provider_name() -> str:
    return str(settings.asr_provider or "").strip().lower()


def _local_whisper_enabled() -> bool:
    return _asr_provider_name() in {"", "whisper", "local_whisper", "auto"}


def _dependency_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _pick_writable_directory(preferred: Path, fallback_name: str) -> Path:
    for candidate in (preferred, Path(tempfile.gettempdir()) / fallback_name):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    raise RuntimeError("No writable model cache directory is available")


def _resolve_whisper_download_root() -> Optional[str]:
    configured = str(os.getenv("WHISPER_CACHE_DIR") or os.getenv("WHISPER_MODEL_DIR") or "").strip()
    if not configured:
        return None
    cache_dir = _pick_writable_directory(Path(configured).expanduser(), "civil_whisper_cache")
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir.parent))
    return str(cache_dir)


def get_asr_runtime_status() -> Dict:
    """Return non-secret ASR readiness details for diagnostics."""
    provider = _asr_provider_name() or "whisper"
    remote_model = _resolve_asr_model()
    remote_configured = bool(settings.llm_api_key and remote_model)
    whisper_enabled = _local_whisper_enabled()
    whisper_available = _dependency_available("whisper")
    torch_available = _dependency_available("torch")
    ffmpeg_path = shutil.which("ffmpeg") or ""
    local_ready = whisper_enabled and whisper_available and torch_available and bool(ffmpeg_path)

    if remote_configured:
        mode = "remote_asr"
        ready = True
        message = "远程 ASR 已配置"
    elif local_ready:
        mode = "local_whisper"
        ready = True
        message = "本地 Whisper ASR 可用"
    elif not whisper_enabled:
        mode = "disabled"
        ready = False
        message = f"当前 ASR_PROVIDER={provider}，未启用 Whisper 本地转写"
    else:
        mode = "unavailable"
        ready = False
        missing = []
        if not whisper_available:
            missing.append("openai-whisper")
        if not torch_available:
            missing.append("torch")
        if not ffmpeg_path:
            missing.append("ffmpeg")
        message = f"缺少真实 ASR 依赖：{', '.join(missing) or '未知依赖'}"

    return {
        "ready": ready,
        "mode": mode,
        "message": message,
        "provider": provider,
        "remote": {
            "configured": remote_configured,
            "provider": settings.llm_provider,
            "model": remote_model,
        },
        "localWhisper": {
            "enabled": whisper_enabled,
            "available": local_ready,
            "modelSize": str(settings.whisper_model_size or "base"),
            "language": settings.whisper_language or "zh",
            "device": settings.asr_device or "cpu",
            "cpuThreads": int(settings.whisper_cpu_threads or 0),
            "modelLoaded": _whisper_model is not None,
            "dependencies": {
                "openaiWhisper": whisper_available,
                "torch": torch_available,
                "ffmpeg": bool(ffmpeg_path),
            },
            "ffmpegPath": ffmpeg_path,
        },
    }


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

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError("缺少 openai-whisper 依赖，请在后端运行环境安装 requirements.txt。") from exc

    model_size = str(settings.whisper_model_size or os.getenv("WHISPER_MODEL_SIZE", "base")).strip() or "base"
    cpu_threads = int(settings.whisper_cpu_threads or 0)
    if cpu_threads > 0:
        try:
            import torch
            torch.set_num_threads(cpu_threads)
        except Exception:
            logger.debug("Unable to set torch CPU threads", exc_info=True)
    logger.info(
        "Loading local Whisper fallback model",
        extra={
            "event": "asr.whisper.load",
            "model_size": model_size,
            "device": settings.asr_device,
            "cpu_threads": cpu_threads,
        },
    )
    download_root = _resolve_whisper_download_root()
    device = str(settings.asr_device or "cpu").strip() or "cpu"
    _whisper_model = whisper.load_model(model_size, device=device, download_root=download_root)
    return _whisper_model


def _transcribe_with_local_whisper(media_bytes: bytes, filename: str) -> str:
    source_path = None
    suffix = Path(filename or "").suffix.lower() or ".webm"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_file:
            source_path = source_file.name
            source_file.write(media_bytes)
        model = _get_local_whisper_model()
        result = model.transcribe(
            source_path,
            language=settings.whisper_language or "zh",
            fp16=False,
        )
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
            if "dashscope.aliyuncs.com" in str(settings.llm_base_url or ""):
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
        except Exception:
            logger.warning(
                "ASR transcription failed, trying local Whisper fallback",
                extra={"event": "asr.remote.failed", "provider": settings.llm_provider, "model": asr_model},
                exc_info=True,
            )

    if _local_whisper_enabled():
        try:
            text = _transcribe_with_local_whisper(audio_bytes, filename)
            if text.strip():
                return text.strip()
        except Exception:
            logger.warning(
                "Local Whisper fallback failed, falling back to placeholder",
                extra={"event": "asr.local.failed", "provider": settings.asr_provider},
                exc_info=True,
            )

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
    "jiangsu_a": "A类 · 综合管理岗",
    "jiangsu_b": "B类 · 社会科学专技岗",
    "jiangsu_c": "C类 · 自然科学专技岗",
    "jiangsu_d": "D类 · 中小学教师岗",
    "jiangsu_e": "E类 · 医疗卫生岗",
    "jiangsu_worker": "工勤技能岗",
}
