"""
这个文件封装旧后端音频转写；本地模型、远程服务和不可用提示都在这里统一处理。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import abc
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_WHISPER_MODEL_CACHE: dict[str, object] = {}
_FUNASR_MODEL_CACHE: dict[tuple[str, str, str, str], object] = {}


def _pick_writable_dir(preferred: Path, fallback_name: str) -> Path:
    """Return a writable directory, falling back to the user temp dir."""

    for candidate in (preferred, Path(tempfile.gettempdir()) / fallback_name):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    raise RuntimeError("无法找到可写的模型缓存目录。")


def _configure_model_cache_env() -> Path:
    """Configure a writable cache path for FunASR and model downloads."""

    preferred = settings.resolve_path(settings.MODELSCOPE_CACHE)
    cache_dir = _pick_writable_dir(preferred, "kaogong_ai_modelscope_cache")
    credentials_dir = cache_dir / ".modelscope" / "credentials"
    credentials_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MODELSCOPE_CACHE"] = str(cache_dir)
    os.environ["MODELSCOPE_CREDENTIALS_PATH"] = str(credentials_dir)
    os.environ["HF_HOME"] = str(cache_dir / "hf_home")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_dir / "huggingface")
    return cache_dir


class BaseTranscriber(abc.ABC):
    """
    BaseTranscriber 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    @abc.abstractmethod
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        transcribe 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

        @param audio_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param language: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """


class WhisperLocalTranscriber(BaseTranscriber):
    """
    WhisperLocalTranscriber 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def __init__(self, model_size: str):
        self.model_size = model_size
        if self.model_size not in _WHISPER_MODEL_CACHE:
            self._load_model()
        self.model = _WHISPER_MODEL_CACHE[self.model_size]

    def _load_model(self) -> None:
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError(
                "缺少 openai-whisper 依赖，请先安装 requirements.txt 中的依赖。"
            ) from exc

        try:
            import torch

            torch.set_num_threads(max(settings.WHISPER_CPU_THREADS, 1))
        except ImportError:
            logger.warning("未安装 torch，无法设置 Whisper CPU 线程数。")

        logger.info("首次初始化 Whisper 模型: %s", self.model_size)
        _WHISPER_MODEL_CACHE[self.model_size] = whisper.load_model(self.model_size)
        logger.info("Whisper 模型加载完成。")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        transcribe 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

        @param audio_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param language: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        logger.info("ASR 开始转录: %s", audio_path)
        try:
            result = self.model.transcribe(
                audio_path,
                language=language or settings.WHISPER_LANGUAGE,
                fp16=False,
            )
        except Exception as exc:
            logger.error("Whisper 转录失败: %s", exc)
            raise RuntimeError(f"语音识别失败: {exc}") from exc

        text = str(result.get("text", "")).strip()
        logger.info("ASR 转录完成，文本长度: %s", len(text))
        return text


class FunASRTranscriber(BaseTranscriber):
    """
    FunASRTranscriber 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def __init__(self):
        self.device = settings.ASR_DEVICE
        cache_key = (
            settings.FUNASR_MODEL_NAME,
            settings.FUNASR_VAD_MODEL_NAME,
            settings.FUNASR_PUNC_MODEL_NAME,
            self.device,
        )
        if cache_key not in _FUNASR_MODEL_CACHE:
            self._load_model(cache_key)
        self.model = _FUNASR_MODEL_CACHE[cache_key]

    def _load_model(self, cache_key: tuple[str, str, str, str]) -> None:
        try:
            _configure_model_cache_env()
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "缺少 funasr 依赖，请先安装 requirements.txt 中的依赖。"
            ) from exc

        logger.info(
            "首次初始化 FunASR 模型: %s / %s / %s",
            settings.FUNASR_MODEL_NAME,
            settings.FUNASR_VAD_MODEL_NAME,
            settings.FUNASR_PUNC_MODEL_NAME,
        )

        _FUNASR_MODEL_CACHE[cache_key] = AutoModel(
            model=settings.FUNASR_MODEL_NAME,
            model_revision=settings.FUNASR_MODEL_REVISION,
            vad_model=settings.FUNASR_VAD_MODEL_NAME,
            vad_model_revision=settings.FUNASR_VAD_MODEL_REVISION,
            punc_model=settings.FUNASR_PUNC_MODEL_NAME,
            punc_model_revision=settings.FUNASR_PUNC_MODEL_REVISION,
            disable_update=True,
            device=self.device,
        )
        logger.info("FunASR 模型加载完成。")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        transcribe 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

        @param audio_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param language: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        del language
        logger.info("ASR 开始转录: %s", audio_path)
        try:
            result = self.model.generate(input=audio_path)
        except Exception as exc:
            logger.error("FunASR 转录失败: %s", exc)
            raise RuntimeError(f"语音识别失败: {exc}") from exc

        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                text = str(first.get("text", "")).strip()
            else:
                text = str(first).strip()
        elif isinstance(result, dict):
            text = str(result.get("text", "")).strip()
        else:
            text = str(result).strip()

        logger.info("ASR 转录完成，文本长度: %s", len(text))
        return text


def get_transcriber(provider: Optional[str] = None) -> BaseTranscriber:
    """
    get_transcriber 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    媒体服务负责把音视频转成可评分文本，注释重点记录模型能力、缓存和降级边界。

    @param provider: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
    """

    provider_name = (provider or settings.ASR_PROVIDER).strip().lower()
    if provider_name == "whisper":
        return WhisperLocalTranscriber(model_size=settings.WHISPER_MODEL_SIZE)
    if provider_name == "funasr":
        return FunASRTranscriber()
    raise RuntimeError(f"不支持的 ASR_PROVIDER: {provider_name}")
