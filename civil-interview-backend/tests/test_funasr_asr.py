"""
FunASR 测试锁定长音频切段、静音跳过和考公词汇纠错。

面试录音可能长达数分钟，不能整段塞给 Paraformer；VAD 切段、片段拼接和领域纠错任何一步退化，
都会让答题文字稿变慢、断句变差或把“预研/敢试”等面试高频词识别错。

@param: 无；用例通过 stub 模型、假 librosa 和 numpy 音频构造边界场景。
@return: 无直接返回；断言通过表示 ASR 管线仍按短句识别而不是整段推理。
@raises ImportError: numpy、ASR 网关或测试替身依赖缺失时会失败。
"""
import unittest
from unittest.mock import patch

import sys
import types

import numpy as np

from app.core import ai


class FunasrAsrTestCase(unittest.TestCase):
    """
    FunASR 管线回归用例集合，覆盖 VAD 切段、标点拼接、领域纠错和静音短路。

    面试录音通常是一整段连续表达，模型入口必须先切成短句再识别；这些断言把“不能整段推理”和
    “识别结果要适配考公表达”两件事固定下来，避免 ASR 优化时牺牲稳定性。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: VAD 切段、静音跳过、文本抽取或领域纠错退化时由断言报告。
    """
    def test_vad_segments_are_padded_and_split_by_max_duration(self):
        """
        VAD 片段要先补上下文，再按最大时长拆成可控短句。

        过短会切掉句首句尾语义，过长会退回整段推理；这个用例把两者之间的折中固定下来。

        @param: 无；临时缩短最大片段时长和 padding 配置。
        @return: None；片段按预期补边并拆分时通过。
        @raises AssertionError: 切段长度、边界或补边策略改变时失败。
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
        VAD 片段补边后不能互相重叠。

        片段重叠会让 Paraformer 重复识别同一句话，最终文字稿出现“接近接近”“机制机制”这类重复词。

        @param: 无；临时调整片段 padding 后直接调用切段 helper。
        @return: None；两个相邻片段被裁成连续不重叠区间时通过。
        @raises AssertionError: 片段边界重叠或补边策略漂移时失败。
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
        拼接 VAD 片段时要根据停顿长度补逗号或句号。

        面试评分会读取文字稿结构；长停顿如果不转成句号，LLM 更容易把分论点黏成一整句。

        @param: 无；构造三段带时间间隔的转写片段。
        @return: None；短停顿生成逗号、长停顿生成句号时通过。
        @raises AssertionError: 断句符号或拼接顺序变化时失败。
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
        FunASR 后处理要修正常见考公表达误识别。

        “预研”“敢试”“反馈机制”等词会直接影响评分关键词命中；领域纠错能减少 ASR 错字对内容评分的干扰。

        @param: 无；输入一段包含典型误识别的模拟文字稿。
        @return: None；关键考公表达被修正时通过。
        @raises AssertionError: 领域纠错规则失效或断句修复退化时失败。
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

    def test_funasr_postprocess_repairs_recent_domain_errors(self):
        """
        FunASR 后处理要覆盖近期暴露的高频错词。

        这些词大多来自应急处置、算法监管、基层治理和名句引用题，错一个字就会影响关键词命中和结果页复盘。

        @param: 无；输入包含近期服务器样例里的典型误识别。
        @return: None；所有固定短语被保守修正时通过。
        @raises AssertionError: 新增纠错表失效时失败。
        """
        raw = (
            "严防刺凶险轻，分级普惠社保代交补贴，增设骑手一件避险功能，"
            "破除为时效考核，杜绝顾客恶意评差评。"
            "做到领域标新，砍掉冗于报表和勇于爆表，推进邻里矛盾调节。"
        )

        transcript = ai._postprocess_funasr_transcript(raw)

        self.assertIn("严防次生险情", transcript)
        self.assertIn("社保代缴补贴", transcript)
        self.assertIn("一键避险", transcript)
        self.assertIn("唯时效考核", transcript)
        self.assertIn("恶意差评", transcript)
        self.assertIn("领异标新", transcript)
        self.assertIn("冗余报表", transcript)
        self.assertIn("邻里矛盾调解", transcript)

    def test_funasr_postprocess_uses_question_context_phrases_conservatively(self):
        """
        题目上下文短语只触发明确的短语纠错。

        没有题目上下文时不做宽泛猜测；当题干或关键词明确包含目标短语时，再修正对应常见错词。

        @param: 无；用“错峰就餐”模拟题干热词纠错。
        @return: None；有上下文时修正，无上下文时保持原文。
        @raises AssertionError: 上下文纠错过宽或失效时失败。
        """
        raw = "高校食堂措峰就餐能够分流人群"

        self.assertIn("措峰就餐", ai._postprocess_funasr_transcript(raw))
        self.assertIn(
            "错峰就餐",
            ai._postprocess_funasr_transcript(raw, context_phrases=["错峰就餐", "高校食堂"]),
        )

    def test_build_asr_context_phrases_extracts_question_terms(self):
        """
        题干、采分点和关键词要能生成 ASR 上下文短语。

        转写接口拿到 questionId 后会用这些短语参与缓存分桶和保守纠错，避免不同题目共用同一段音频缓存。

        @param: 无；构造题干、采分点和关键词的常见 JSON 形状。
        @return: None；关键短语被提取且去重时通过。
        @raises AssertionError: 上下文提取遗漏题目字段时失败。
        """
        phrases = ai.build_asr_context_phrases(
            "高校食堂为实现错峰就餐，缓解校内就餐高峰压力。",
            [{"content": "增设骑手一键避险功能", "keywords": ["唯时效考核"]}],
            {"scoring": ["次生险情"], "_meta": {"coreKeywords": ["领异标新"]}},
        )

        self.assertIn("错峰就餐", phrases)
        self.assertIn("一键避险", phrases)
        self.assertIn("唯时效考核", phrases)
        self.assertIn("次生险情", phrases)
        self.assertIn("领异标新", phrases)

    def test_audio_rms_detects_near_silence(self):
        """
        RMS 静音检测要能区分空录音和有效低音量录音。

        静音短路用于避免把空白音频送进 VAD/ASR；阈值过高又会误伤学生小声作答。

        @param: 无；构造全零波形和低幅度有效波形。
        @return: None；全零 RMS 为 0 且有效波形超过静音阈值时通过。
        @raises AssertionError: RMS 计算或静音阈值判断退化时失败。
        """
        self.assertEqual(ai._audio_rms(np.zeros(ai.ASR_SAMPLE_RATE, dtype=np.float32)), 0.0)
        self.assertGreater(ai._audio_rms(np.ones(ai.ASR_SAMPLE_RATE, dtype=np.float32) * 0.01), 0.001)

    def test_funasr_onnx_skips_near_silent_audio(self):
        """
        近静音音频要在进入 VAD 和 ASR 前直接返回空文字稿。

        空录音常见于权限或录音失败场景；短路可以避免模型误产出幻觉文字，也能节省一次无意义推理。

        @param: 无；用 stub 模型确保静音时不会调用 VAD/ASR。
        @return: None；返回空字符串且 stub 未被触发时通过。
        @raises AssertionError: 近静音音频仍进入模型推理时失败。
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
        文本抽取要兼容 FunASR ONNX 和 pipeline 返回的多种形状。

        FunASR 不同引擎、标点模型和批处理模式返回结构不完全一致；这里防止某个部署形态只返回空文字稿。

        @param: 无；直接构造列表、字典、元组和 token tuple 几种返回形态。
        @return: None；所有形态都能抽出文本时通过。
        @raises AssertionError: 某种 FunASR 返回结构被解析为空或顺序错误时失败。
        """
        self.assertEqual(ai._extract_funasr_text([{"preds": "第一句"}, {"text": "第二句"}]), "第一句第二句")
        self.assertEqual(ai._extract_funasr_text({"text": "整段文本"}), "整段文本")
        self.assertEqual(ai._extract_funasr_text(("标点后的文本", [1, 2, 3])), "标点后的文本")
        self.assertEqual(ai._extract_funasr_text([{"preds": ("识别文本", ["识", "别", "文", "本"])}]), "识别文本")

    def test_funasr_onnx_transcribes_vad_segments_instead_of_full_audio(self):
        """
        ONNX 转写必须逐个识别 VAD 片段，而不是把整段音频送给 ASR。

        这是长音频稳定性的核心约束：5 分钟朗读先由 VAD 切句，再逐句给 Paraformer，避免整段推理变慢或识别崩掉。

        @param: 无；用 stub VAD 返回两个 1 秒片段，并记录 ASR 收到的片段长度。
        @return: None；ASR 只收到两个短片段且拼接文本正确时通过。
        @raises AssertionError: ASR 收到整段音频、片段数量不对或拼接结果错误时失败。
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
