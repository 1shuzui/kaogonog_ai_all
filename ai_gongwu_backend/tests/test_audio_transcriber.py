"""
这个测试文件守住 `test_audio_transcriber` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch
import wave
from pathlib import Path
import uuid

from app.core.config import settings
from app.services.media.audio_transcriber import (
    FunASRTranscriber,
    WhisperLocalTranscriber,
    _FUNASR_MODEL_CACHE,
    _WHISPER_MODEL_CACHE,
    get_transcriber,
)
from app.services.media.video_processor import get_audio_duration_seconds, process_audio


class AudioTranscriberTestCase(unittest.TestCase):
    """
    AudioTranscriberTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def setUp(self):
        """
        setUp 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        _WHISPER_MODEL_CACHE.clear()
        _FUNASR_MODEL_CACHE.clear()
        self.temp_root = Path.cwd() / "storage" / "test_audio_transcriber"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.created_paths: list[Path] = []

    def tearDown(self):
        """
        tearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        for path in self.created_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def test_get_transcriber_returns_whisper(self):
        """
        test_get_transcriber_returns_whisper 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        with patch.object(WhisperLocalTranscriber, "_load_model") as mock_load:
            _WHISPER_MODEL_CACHE[settings.WHISPER_MODEL_SIZE] = object()
            transcriber = get_transcriber("whisper")
            self.assertIsInstance(transcriber, WhisperLocalTranscriber)
            mock_load.assert_not_called()

    def test_get_transcriber_returns_funasr(self):
        """
        test_get_transcriber_returns_funasr 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        cache_key = (
            settings.FUNASR_MODEL_NAME,
            settings.FUNASR_VAD_MODEL_NAME,
            settings.FUNASR_PUNC_MODEL_NAME,
            settings.ASR_DEVICE,
        )
        _FUNASR_MODEL_CACHE[cache_key] = object()
        transcriber = get_transcriber("funasr")
        self.assertIsInstance(transcriber, FunASRTranscriber)

    def test_unknown_provider_raises(self):
        """
        test_unknown_provider_raises 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises RuntimeError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        with self.assertRaises(RuntimeError) as exc_info:
            get_transcriber("unknown")
        self.assertIn("unknown", str(exc_info.exception))

    def test_funasr_transcribe_extracts_text_from_list_payload(self):
        """
        test_funasr_transcribe_extracts_text_from_list_payload 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        class StubAutoModel:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def generate(self, input):
                """
                generate 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

                测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

                @param input: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
                @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
                @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
                """
                return [{"text": "你好，世界"}]

        funasr_module = types.ModuleType("funasr")
        funasr_module.AutoModel = StubAutoModel

        with patch.dict(sys.modules, {"funasr": funasr_module}):
            transcriber = FunASRTranscriber()
            text = transcriber.transcribe("dummy.wav")

        self.assertEqual(text, "你好，世界")

    def test_get_audio_duration_seconds_for_wav(self):
        """
        test_get_audio_duration_seconds_for_wav 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        wav_path = self.temp_root / f"duration_{uuid.uuid4().hex}.wav"
        self.created_paths.append(wav_path)
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

        duration = get_audio_duration_seconds(str(wav_path))

        self.assertIsNotNone(duration)
        assert duration is not None
        self.assertAlmostEqual(duration, 1.0, places=2)

    def test_process_audio_includes_duration_seconds(self):
        """
        test_process_audio_includes_duration_seconds 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        class StubTranscriber:
            def transcribe(self, audio_path: str, language=None) -> str:
                """
                transcribe 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

                测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

                @param audio_path: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
                @param language: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
                @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
                @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
                """
                del audio_path, language
                return "这是一段音频作答"

        wav_path = self.temp_root / f"process_audio_{uuid.uuid4().hex}.wav"
        self.created_paths.append(wav_path)
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 8000)

        with patch("app.services.media.video_processor.get_transcriber", return_value=StubTranscriber()):
            result = process_audio(str(wav_path))

        self.assertEqual(result.source, "audio")
        self.assertEqual(result.transcript, "这是一段音频作答")
        self.assertIsNotNone(result.duration_seconds)
        assert result.duration_seconds is not None
        self.assertAlmostEqual(result.duration_seconds, 0.5, places=2)


if __name__ == "__main__":
    unittest.main()
