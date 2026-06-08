"""
这个测试文件守住 `test_funasr_asr` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest
from unittest.mock import patch

import sys
import types

import numpy as np

from app.core import ai


class FunasrAsrTestCase(unittest.TestCase):
    """
    FunasrAsrTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def test_vad_segments_are_padded_and_split_by_max_duration(self):
        """
        test_vad_segments_are_padded_and_split_by_max_duration 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_max = ai.settings.asr_max_segment_seconds
        original_padding = ai.settings.asr_segment_padding_ms
        try:
            ai.settings.asr_max_segment_seconds = 1.0
            ai.settings.asr_segment_padding_ms = 100

            segments = ai._merge_vad_segments([[[500, 2800]]], audio_length=ai.ASR_SAMPLE_RATE * 4)
        finally:
            ai.settings.asr_max_segment_seconds = original_max
            ai.settings.asr_segment_padding_ms = original_padding

        self.assertEqual(
            segments,
            [
                (6400, 22400),
                (22400, 38400),
                (38400, 46400),
            ],
        )

    def test_vad_segments_do_not_overlap_after_padding(self):
        """
        test_vad_segments_do_not_overlap_after_padding 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_padding = ai.settings.asr_segment_padding_ms
        try:
            ai.settings.asr_segment_padding_ms = 200

            segments = ai._merge_vad_segments(
                [[[1000, 1800], [2200, 3000]]],
                audio_length=ai.ASR_SAMPLE_RATE * 4,
            )
        finally:
            ai.settings.asr_segment_padding_ms = original_padding

        self.assertEqual(
            segments,
            [
                (12800, 32000),
                (32000, 51200),
            ],
        )

    def test_funasr_segment_join_inserts_punctuation_by_gap(self):
        """
        test_funasr_segment_join_inserts_punctuation_by_gap 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = ai._join_funasr_segments(
            [
                ("首先要肯定试点意义", 0, ai.ASR_SAMPLE_RATE),
                ("然后分析推广失败原因", int(ai.ASR_SAMPLE_RATE * 1.4), ai.ASR_SAMPLE_RATE * 2),
                ("最后建立闭环", int(ai.ASR_SAMPLE_RATE * 3), ai.ASR_SAMPLE_RATE * 4),
            ]
        )

        self.assertEqual(transcript, "首先要肯定试点意义，然后分析推广失败原因。最后建立闭环")

    def test_funasr_postprocess_repairs_exam_domain_errors(self):
        """
        test_funasr_postprocess_repairs_exam_domain_errors 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        raw = (
            "试点本身是是在小范围可控条件下做的探索，第一是忽略了水土不服试点一般会有政策倾斜，"
            "推广时搞梯度推广，先找条件，接近接近的区域扩面，试点阶段做差异化的预言，"
            "快速反馈机机制没跟上，既敢闯敢式又稳扎稳打。"
        )

        transcript = ai._postprocess_funasr_transcript(raw)

        self.assertIn("试点本身是在小范围可控条件下做的探索", transcript)
        self.assertIn("水土不服，试点一般会有政策倾斜", transcript)
        self.assertIn("接近的区域扩面", transcript)
        self.assertIn("差异化的预研", transcript)
        self.assertIn("快速反馈机制", transcript)
        self.assertIn("敢闯敢试", transcript)

    def test_audio_rms_detects_near_silence(self):
        """
        test_audio_rms_detects_near_silence 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.assertEqual(ai._audio_rms(np.zeros(ai.ASR_SAMPLE_RATE, dtype=np.float32)), 0.0)
        self.assertGreater(ai._audio_rms(np.ones(ai.ASR_SAMPLE_RATE, dtype=np.float32) * 0.01), 0.001)

    def test_funasr_onnx_skips_near_silent_audio(self):
        """
        test_funasr_onnx_skips_near_silent_audio 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises AssertionError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        class StubVad:
            def __call__(self, waveform):
                raise AssertionError("VAD should not run for near-silent audio")

        class StubAsr:
            def __call__(self, segment_audio):
                raise AssertionError("ASR should not run for near-silent audio")

        librosa_module = types.ModuleType("librosa")
        librosa_module.load = lambda path, sr, mono: (np.zeros(ai.ASR_SAMPLE_RATE * 2), ai.ASR_SAMPLE_RATE)

        with patch.dict(sys.modules, {"librosa": librosa_module}), patch(
            "app.core.ai._get_funasr_onnx_models",
            return_value={"vad": StubVad(), "asr": StubAsr(), "punc": None},
        ):
            transcript = ai._transcribe_with_funasr_onnx("dummy.wav")

        self.assertEqual(transcript, "")

    def test_extract_funasr_text_supports_onnx_and_pipeline_shapes(self):
        """
        test_extract_funasr_text_supports_onnx_and_pipeline_shapes 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.assertEqual(ai._extract_funasr_text([{"preds": "第一句"}, {"text": "第二句"}]), "第一句第二句")
        self.assertEqual(ai._extract_funasr_text({"text": "整段文本"}), "整段文本")
        self.assertEqual(ai._extract_funasr_text(("标点后的文本", [1, 2, 3])), "标点后的文本")
        self.assertEqual(ai._extract_funasr_text([{"preds": ("识别文本", ["识", "别", "文", "本"])}]), "识别文本")

    def test_funasr_onnx_transcribes_vad_segments_instead_of_full_audio(self):
        """
        test_funasr_onnx_transcribes_vad_segments_instead_of_full_audio 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        original_padding = ai.settings.asr_segment_padding_ms
        try:
            ai.settings.asr_segment_padding_ms = 0

            class StubVad:
                def __call__(self, waveform):
                    self.waveform_length = len(waveform)
                    return [[[0, 1000], [2000, 3000]]]

            class StubAsr:
                def __init__(self):
                    self.segment_lengths = []

                def __call__(self, segment_audio):
                    self.segment_lengths.append(len(segment_audio))
                    return [{"preds": f"片段{len(self.segment_lengths)}"}]

            vad = StubVad()
            asr = StubAsr()
            librosa_module = types.ModuleType("librosa")
            librosa_module.load = lambda path, sr, mono: (np.ones(ai.ASR_SAMPLE_RATE * 5) * 0.01, ai.ASR_SAMPLE_RATE)

            with patch.dict(sys.modules, {"librosa": librosa_module}), patch(
                "app.core.ai._get_funasr_onnx_models",
                return_value={"vad": vad, "asr": asr, "punc": None},
            ):
                transcript = ai._transcribe_with_funasr_onnx("dummy.wav")
        finally:
            ai.settings.asr_segment_padding_ms = original_padding

        self.assertEqual(transcript, "片段1。片段2")
        self.assertEqual(vad.waveform_length, ai.ASR_SAMPLE_RATE * 5)
        self.assertEqual(asr.segment_lengths, [ai.ASR_SAMPLE_RATE, ai.ASR_SAMPLE_RATE])


if __name__ == "__main__":
    unittest.main()
