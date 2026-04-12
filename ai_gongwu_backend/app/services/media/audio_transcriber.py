"""语音转文字模块。

这个模块的核心职责是：
把音频文件交给 Whisper，拿回文字 transcript。

这里专门做了“懒加载 + 缓存”：
- 第一次用时才加载模型
- 加载后复用同一个模型对象
这样能明显减少重复初始化带来的性能浪费。
"""

import abc
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_WHISPER_MODEL_CACHE = {}


class BaseTranscriber(abc.ABC):
    """语音转写抽象基类。

    先定义统一接口的好处是：
    以后如果你想把 Whisper 换成云厂商 ASR，
    只要新增一个实现类即可，业务层几乎不用改。
    """

    @abc.abstractmethod
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """Transcribe the provided audio file into text."""


class WhisperLocalTranscriber(BaseTranscriber):
    """本地 Whisper 实现。"""

    def __init__(self, model_size: str):
        self.model_size = model_size
        if self.model_size not in _WHISPER_MODEL_CACHE:
            # 模型还没加载过时，才真正执行加载。
            self._load_model()
        self.model = _WHISPER_MODEL_CACHE[self.model_size]

    def _load_model(self) -> None:
        """加载 Whisper 模型到内存。"""
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError(
                "缺少 openai-whisper 依赖，请先安装 requirements.txt 中的依赖。"
            ) from exc

        try:
            import torch

            # 控制 CPU 线程数，防止 Whisper 在 CPU 环境下把机器吃满。
            torch.set_num_threads(max(settings.WHISPER_CPU_THREADS, 1))
        except ImportError:
            logger.warning("未安装 torch，无法设置 Whisper CPU 线程数。")

        logger.info(
            "首次初始化 Whisper 模型: %s (首次运行可能会自动下载权重)",
            self.model_size,
        )
        _WHISPER_MODEL_CACHE[self.model_size] = whisper.load_model(self.model_size)
        logger.info("Whisper 模型加载完成。")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """执行转写并返回文本。"""
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

        text = result.get("text", "").strip()
        logger.info("ASR 转录完成，文本长度: %s", len(text))
        return text


def get_transcriber() -> BaseTranscriber:
    """返回当前系统配置好的转写器实现。"""

    return WhisperLocalTranscriber(model_size=settings.WHISPER_MODEL_SIZE)
