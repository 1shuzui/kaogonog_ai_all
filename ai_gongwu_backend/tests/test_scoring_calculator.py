"""
这个测试文件守住 `test_scoring_calculator` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import unittest
from pathlib import Path

from app.core.config import settings
from app.models.schemas import QuestionDefinition
from app.services.question_bank import QuestionBank
from app.services.scoring.calculator import (
    _compute_rule_based_dimension_scores,
    _extract_salvageable_fragment,
    apply_post_processing,
    build_deterministic_stage_two_payload,
    compute_speech_rate_feedback,
    prepare_evidence_packet,
)


class ScoringCalculatorTestCase(unittest.TestCase):
    """
    验证证据抽取校验和证据约束评分。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    @classmethod
    def setUpClass(cls):
        """
        setUpClass 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        bank = QuestionBank(settings.QUESTION_DB_PATH)
        cls.question = bank.get_question("HN-LX-20200606-01")
        cls.imported_question = bank.get_question("HN-20200816-01")

    def test_prepare_evidence_packet_filters_fake_quotes_and_adds_absence_evidence(self):
        """
        test_prepare_evidence_packet_filters_fake_quotes_and_adds_absence_evidence 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = "我觉得要因地制宜，不能一刀切，但没有提河南省情。"
        stage_one_payload = {
            "evidence_items": [
                {
                    "id": "",
                    "dimension_hint": "现象解读",
                    "claim": "指出一刀切问题",
                    "evidence_text": "不能一刀切",
                    "evidence_type": "quote",
                    "stance": "negative",
                },
                {
                    "id": "",
                    "dimension_hint": "现象解读",
                    "claim": "伪造原话",
                    "evidence_text": "为了直播而直播",
                    "evidence_type": "quote",
                    "stance": "negative",
                },
            ]
        }

        evidence_packet, notes = prepare_evidence_packet(
            raw_llm_result=stage_one_payload,
            transcript=transcript,
            question=self.question,
        )

        evidence_texts = [item.evidence_text for item in evidence_packet.evidence_items]
        self.assertIn("不能一刀切", evidence_texts)
        self.assertNotIn("为了直播而直播", evidence_texts)
        self.assertTrue(any(item.evidence_type == "absence" for item in evidence_packet.evidence_items))
        self.assertTrue(notes)

    def test_compute_speech_rate_feedback_returns_slow_normal_and_fast(self):
        """
        test_compute_speech_rate_feedback_returns_slow_normal_and_fast 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        slow = compute_speech_rate_feedback(
            transcript="这是一段用于测试语速的中文作答内容",
            source="audio",
            duration_seconds=20.0,
        )
        normal = compute_speech_rate_feedback(
            transcript="这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容",
            source="video",
            duration_seconds=20.0,
        )
        fast = compute_speech_rate_feedback(
            transcript="这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容这是一段用于测试语速的中文作答内容",
            source="audio",
            duration_seconds=20.0,
        )

        self.assertEqual(slow["speech_rate_level"], "偏慢")
        self.assertIn("适当加快表达节奏", slow["speech_rate_advice"])
        self.assertEqual(normal["speech_rate_level"], "正常")
        self.assertIn("继续保持表达清晰", normal["speech_rate_advice"])
        self.assertEqual(fast["speech_rate_level"], "偏快")
        self.assertIn("适当放慢语速", fast["speech_rate_advice"])

    def test_compute_speech_rate_feedback_skips_text_submission(self):
        """
        test_compute_speech_rate_feedback_skips_text_submission 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        result = compute_speech_rate_feedback(
            transcript="纯文本提交不应伪造语速",
            source="text",
            duration_seconds=None,
        )

        self.assertIsNone(result["speech_rate_chars_per_minute"])
        self.assertIsNone(result["speech_rate_level"])
        self.assertEqual(result["speech_rate_advice"], "")

    def test_post_processing_requires_evidence_binding_for_deductions(self):
        """
        test_post_processing_requires_evidence_binding_for_deductions 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = (
            "我觉得A市不能一刀切，应该因地制宜，完善农村物流，"
            "帮助农民把农产品包装好。"
        )
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={
                "evidence_items": [
                    {
                        "id": "",
                        "dimension_hint": "危害根源分析",
                        "claim": "指出一刀切问题",
                        "evidence_text": "不能一刀切",
                        "evidence_type": "quote",
                        "stance": "negative",
                    },
                    {
                        "id": "",
                        "dimension_hint": "科学决策与措施",
                        "claim": "提出完善农村物流",
                        "evidence_text": "完善农村物流",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                ]
            },
            transcript=transcript,
            question=self.question,
        )
        evidence_ids = {item.claim: item.id for item in evidence_packet.evidence_items}

        stage_two_payload = {
            "dimension_scores": {
                "现象解读": 9,
                "科学决策与措施": 6,
                "创新思维": "1.5",
            },
            "deduction_items": [
                {
                    "reason": "未结合河南省情展开分析",
                    "dimension": "现象解读",
                    "evidence_ids": [],
                },
                {
                    "reason": "原文存在明显口语表达",
                    "dimension": "语言逻辑与岗位适配",
                    "evidence_ids": [evidence_ids["指出一刀切问题"]],
                },
            ],
            "bonus_items": [
                {
                    "reason": "提出完善农村物流等具体措施",
                    "dimension": "科学决策与措施",
                    "evidence_ids": [evidence_ids["提出完善农村物流"]],
                }
            ],
            "rationale": "整体表现尚可。" * 80,
            "total_score": 30,
        }

        result = apply_post_processing(
            raw_llm_result=stage_two_payload,
            transcript=transcript,
            question=self.question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertTrue(any("未绑定有效证据" in note for note in result.validation_notes))
        self.assertFalse(any(item.reason == "未结合河南省情展开分析" for item in result.deduction_items))
        self.assertTrue(any(item.reason == "提出完善农村物流等具体措施" for item in result.bonus_items))
        self.assertTrue(result.evidence_quotes)
        self.assertLessEqual(len(result.rationale), settings.MAX_RATIONALE_CHARS + 3)
        self.assertGreater(result.total_score, 0)

    def test_post_processing_applies_generic_high_score_floor(self):
        """
        test_post_processing_applies_generic_high_score_floor 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = (
            "A市这样做初衷是好的，想通过县长直播带货推广本地农产品。"
            "但硬性要求必须参加并排名通报，容易把探索创新变成一刀切。"
            "不同县资源禀赋、物流条件和产业基础不同，简单照搬会影响实际效果。"
            "排名通报还可能诱导基层只看流量和名次，忽视农民增收和产业带动。"
            "我认为首先要取消强制要求，让各县根据实际自主选择。"
            "其次要完善农村物流、产品分级包装和电商人才培养。"
            "再次要把考核重点放在销量、群众受益和产业带动上。"
            "最后可以结合线下展销、订单农业等方式形成长期机制。"
        )
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={
                "evidence_items": [
                    {
                        "id": "",
                        "dimension_hint": "现象解读",
                        "claim": "指出初衷是推广农产品",
                        "evidence_text": "A市这样做初衷是好的",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                    {
                        "id": "",
                        "dimension_hint": "危害根源分析",
                        "claim": "指出强制要求和排名通报存在问题",
                        "evidence_text": "硬性要求必须参加并排名通报",
                        "evidence_type": "quote",
                        "stance": "negative",
                    },
                    {
                        "id": "",
                        "dimension_hint": "危害根源分析",
                        "claim": "指出不同县条件不同",
                        "evidence_text": "不同县资源禀赋、物流条件和产业基础不同",
                        "evidence_type": "quote",
                        "stance": "negative",
                    },
                    {
                        "id": "",
                        "dimension_hint": "科学决策与措施",
                        "claim": "提出取消强制要求",
                        "evidence_text": "首先要取消强制要求",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                    {
                        "id": "",
                        "dimension_hint": "科学决策与措施",
                        "claim": "提出完善配套和优化考核",
                        "evidence_text": "其次要完善农村物流、产品分级包装和电商人才培养",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                ]
            },
            transcript=transcript,
            question=self.question,
        )

        result = apply_post_processing(
            raw_llm_result={
                "dimension_scores": {
                    "现象解读": 3,
                    "危害根源分析": 4,
                    "科学决策与措施": 5,
                    "语言逻辑与岗位适配": 1,
                    "创新思维": 0,
                },
                "deduction_items": [],
                "bonus_items": [],
                "rationale": "通用分析较完整，但本土化不足。",
                "total_score": 13,
            },
            transcript=transcript,
            question=self.question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertGreaterEqual(result.total_score, 18.0)
        self.assertTrue(
            any("规则校准" in note for note in result.validation_notes)
        )

    def test_extract_salvageable_fragment_can_recover_non_exact_quote(self):
        """
        test_extract_salvageable_fragment_can_recover_non_exact_quote 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = (
            "这种做法也存在几个值得商榷和警惕的问题。"
            "一刀切与形式主义风险。成功的县长直播带货，往往基于当地特色产业的成熟度。"
        )
        evidence_text = (
            "然而，这种做法也存在几个值得商榷和警惕的问题 1. 一刀切与形式主义风险。"
        )
        recovered = _extract_salvageable_fragment(evidence_text, transcript)
        self.assertIsNotNone(recovered)
        self.assertIn(recovered, transcript)
        self.assertGreaterEqual(len(recovered), 8)

    def test_rule_based_scores_can_separate_sample_bands(self):
        """
        test_rule_based_scores_can_separate_sample_bands 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        repo_root = Path(__file__).resolve().parents[2]
        sample_paths = {
            "低分1.txt": repo_root / "sample_sets" / "非高分参考" / "低分1.txt",
            "18分左右.txt": repo_root / "sample_sets" / "非高分参考" / "18分左右.txt",
            "21分左右.txt": repo_root / "sample_sets" / "非高分参考" / "21分左右.txt",
            "中低分1.txt": repo_root / "sample_sets" / "非高分参考" / "中低分1.txt",
            "26分.txt": repo_root / "sample_sets" / "通用高分" / "26分.txt",
            "28分.txt": repo_root / "sample_sets" / "通用高分" / "28分.txt",
            "中高分1.txt": repo_root / "sample_sets" / "河南省直高分" / "中高分1.txt",
            "标准1.txt": repo_root / "sample_sets" / "河南省直高分" / "标准1.txt",
        }

        scores = {}
        for filename, sample_path in sample_paths.items():
            transcript = sample_path.read_text(encoding="utf-8")
            matched_keywords = {
                category: []
                for category in ("core", "strong", "weak", "bonus")
            }
            rule_scores, _ = _compute_rule_based_dimension_scores(
                transcript=transcript,
                question=self.question,
                matched_keywords=matched_keywords,
            )
            scores[filename] = round(sum(rule_scores.values()), 1)

        self.assertLessEqual(scores["低分1.txt"], 17.5)
        self.assertLessEqual(scores["18分左右.txt"], 16.0)
        self.assertGreaterEqual(scores["21分左右.txt"], 18.0)
        self.assertLessEqual(scores["中低分1.txt"], 22.0)
        self.assertGreaterEqual(scores["26分.txt"], 20.0)
        self.assertGreaterEqual(scores["28分.txt"], 23.0)
        self.assertGreaterEqual(scores["中高分1.txt"], 25.0)
        self.assertGreaterEqual(scores["标准1.txt"], 27.0)
        self.assertGreater(scores["标准1.txt"], scores["中高分1.txt"])
        self.assertGreater(scores["中高分1.txt"], scores["28分.txt"])
        self.assertGreater(scores["28分.txt"], scores["26分.txt"])
        self.assertGreater(scores["26分.txt"], scores["21分左右.txt"])

    def test_imported_reference_answer_can_be_scored_high_without_llm(self):
        """
        test_imported_reference_answer_can_be_scored_high_without_llm 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = self.imported_question.referenceAnswer
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={},
            transcript=transcript,
            question=self.imported_question,
        )
        payload = build_deterministic_stage_two_payload(
            transcript=transcript,
            question=self.imported_question,
            evidence_packet=evidence_packet,
        )
        result = apply_post_processing(
            raw_llm_result=payload,
            transcript=transcript,
            question=self.imported_question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertGreaterEqual(
            result.total_score,
            self.imported_question.fullScore - 3.0,
        )
        self.assertTrue(result.evidence_quotes)
        self.assertTrue(result.matched_keywords["core"])

    def test_reference_answer_similarity_floor_can_rescue_under_scored_imported_answer(self):
        """
        test_reference_answer_similarity_floor_can_rescue_under_scored_imported_answer 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = self.imported_question.referenceAnswer
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={},
            transcript=transcript,
            question=self.imported_question,
        )
        low_payload = {
            "dimension_scores": {
                item.name: max(0.0, round(item.score * 0.45, 1))
                for item in self.imported_question.dimensions
            },
            "deduction_items": [],
            "bonus_items": [],
            "rationale": "模型把高分答案压低了。",
            "total_score": 12,
        }

        result = apply_post_processing(
            raw_llm_result=low_payload,
            transcript=transcript,
            question=self.imported_question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertGreaterEqual(result.total_score, self.imported_question.fullScore - 3.0)
        self.assertTrue(
            any("参考答案相似度校准" in note for note in result.validation_notes)
        )

    def test_generic_calibration_can_cap_shallow_imported_answer(self):
        """
        test_generic_calibration_can_cap_shallow_imported_answer 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        transcript = (
            "我觉得这个事情总体方向是对的。"
            "如果让我来处理，我会先加强宣传，再做好沟通解释，最后抓好落实。"
            "这样大家基本就能理解，也能把工作继续往前推。"
        )
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={},
            transcript=transcript,
            question=self.imported_question,
        )
        inflated_payload = {
            "dimension_scores": {
                item.name: max(round(item.score * 0.78, 1), 0.0)
                for item in self.imported_question.dimensions
            },
            "deduction_items": [],
            "bonus_items": [],
            "rationale": "模型给了偏高分。",
            "total_score": round(self.imported_question.fullScore * 0.78, 1),
        }

        result = apply_post_processing(
            raw_llm_result=inflated_payload,
            transcript=transcript,
            question=self.imported_question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertLess(result.total_score, round(self.imported_question.fullScore * 0.7, 1))
        self.assertTrue(
            any("通用校准将总分上限压至" in note for note in result.validation_notes)
        )

    def test_prepare_evidence_packet_can_normalize_language_alias_dimension_hint(self):
        """
        test_prepare_evidence_packet_can_normalize_language_alias_dimension_hint 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        question = QuestionDefinition(
            id="AH-ALIAS-001",
            type="人际沟通",
            province="安徽",
            fullScore=24,
            question="小李总喜欢在朋友圈做调研，你作为同事怎么劝他？",
            dimensions=[
                {"name": "①沟通态度与语气", "score": 5},
                {"name": "②线上工作问题指出", "score": 6},
                {"name": "③基层作风重要性论述", "score": 7},
                {"name": "④引导建议与同事互助", "score": 4},
                {"name": "⑤语言逻辑", "score": 2},
            ],
            scoringCriteria=[
                "沟通态度与语气（5分）",
                "线上工作问题指出（6分）",
                "基层作风重要性论述（7分）",
                "引导建议与同事互助（4分）",
                "语言逻辑（2分）",
            ],
            deductionRules=[],
        )
        transcript = "我觉得这个事吧，还是得下到一线去看，不能老在朋友圈里做调研。"

        evidence_packet, notes = prepare_evidence_packet(
            raw_llm_result={
                "evidence_items": [
                    {
                        "id": "",
                        "dimension_hint": "language",
                        "claim": "表达偏口语化",
                        "evidence_text": "我觉得这个事吧",
                        "evidence_type": "quote",
                        "stance": "language",
                    }
                ]
            },
            transcript=transcript,
            question=question,
        )

        self.assertTrue(
            any(item.dimension_hint == "⑤语言逻辑" for item in evidence_packet.evidence_items)
        )
        self.assertTrue(any("已归一到 [⑤语言逻辑]" in note for note in notes))

    def test_post_processing_can_resolve_generic_dimension_alias_from_reason_context(self):
        """
        test_post_processing_can_resolve_generic_dimension_alias_from_reason_context 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        question = QuestionDefinition(
            id="AH-ALIAS-002",
            type="人际沟通",
            province="安徽",
            fullScore=24,
            question="小李总喜欢在朋友圈做调研，你作为同事怎么劝他？",
            dimensions=[
                {"name": "①沟通态度与语气", "score": 5},
                {"name": "②线上工作问题指出", "score": 6},
                {"name": "③基层作风重要性论述", "score": 7},
                {"name": "④引导建议与同事互助", "score": 4},
                {"name": "⑤语言逻辑", "score": 2},
            ],
            scoringCriteria=[
                "沟通态度与语气（5分）",
                "线上工作问题指出（6分）",
                "基层作风重要性论述（7分）",
                "引导建议与同事互助（4分）",
                "语言逻辑（2分）",
            ],
            deductionRules=[],
        )
        transcript = (
            "我觉得这个事吧，还是得下到一线去看。"
            "后面我可以和你一起下村看看，别总停在朋友圈里做调研。"
        )
        evidence_packet, evidence_notes = prepare_evidence_packet(
            raw_llm_result={
                "evidence_items": [
                    {
                        "id": "",
                        "dimension_hint": "language",
                        "claim": "表达偏口语化",
                        "evidence_text": "我觉得这个事吧",
                        "evidence_type": "quote",
                        "stance": "language",
                    },
                    {
                        "id": "",
                        "dimension_hint": "引导建议与同事互助",
                        "claim": "给出一起下村的跟进动作",
                        "evidence_text": "后面我可以和你一起下村看看",
                        "evidence_type": "quote",
                        "stance": "positive",
                    },
                ]
            },
            transcript=transcript,
            question=question,
        )
        evidence_ids = {item.claim: item.id for item in evidence_packet.evidence_items}

        result = apply_post_processing(
            raw_llm_result={
                "dimension_scores": {
                    "①沟通态度与语气": 3.5,
                    "②线上工作问题指出": 4.0,
                    "③基层作风重要性论述": 4.5,
                    "④引导建议与同事互助": 2.5,
                    "⑤语言逻辑": 1.0,
                },
                "deduction_items": [
                    {
                        "reason": "表达还有点口语化，逻辑不够顺",
                        "dimension": "通用",
                        "evidence_ids": [evidence_ids["表达偏口语化"]],
                    }
                ],
                "bonus_items": [
                    {
                        "reason": "愿意一起下去跟进，动作不算空",
                        "dimension": "建议",
                        "evidence_ids": [evidence_ids["给出一起下村的跟进动作"]],
                    }
                ],
                "rationale": "基本能围绕题目沟通。",
                "total_score": 15.5,
            },
            transcript=transcript,
            question=question,
            evidence_packet=evidence_packet,
            extra_validation_notes=evidence_notes,
        )

        self.assertTrue(any(item.dimension == "⑤语言逻辑" for item in result.deduction_items))
        self.assertTrue(any(item.dimension == "④引导建议与同事互助" for item in result.bonus_items))
        self.assertTrue(any("deduction_items 中的维度 [通用] 已归一到 [⑤语言逻辑]" in note for note in result.validation_notes))
        self.assertTrue(any("bonus_items 中的维度 [建议] 已归一到 [④引导建议与同事互助]" in note for note in result.validation_notes))

    def test_medical_default_appearance_is_returned_separately_and_added_once(self):
        question = QuestionDefinition(
            id="MED-SCORE-001",
            type="综合分析·医疗卫生",
            province="山东",
            fullScore=100,
            questionScore=95,
            appearanceScore=5,
            appearanceScoreMax=5,
            appearanceScoreSource="profile_default",
            appearanceScoreScope="question",
            effectiveFullScore=100,
            hasAppearanceScore=True,
            scoreCalculationNote="仪态分已按默认值计入。",
            question="医疗岗位题目，请结合岗位实际说明你的处理思路。",
            dimensions=[{"name": "内容分析", "score": 95}],
            scoringCriteria=["内容分析（95分）"],
            deductionRules=[],
        )
        evidence_packet, _ = prepare_evidence_packet(
            raw_llm_result={},
            transcript="我会结合岗位实际说明处理思路，先评估情况，再分类处置并做好跟进。",
            question=question,
        )

        result = apply_post_processing(
            raw_llm_result={
                "dimension_scores": {"内容分析": 80},
                "rationale": "结合岗位实际作答。",
                "total_score": 80,
            },
            transcript="我会结合岗位实际说明处理思路，先评估情况，再分类处置并做好跟进。",
            question=question,
            evidence_packet=evidence_packet,
        )

        self.assertEqual(result.appearance_score, 5.0)
        self.assertEqual(result.appearance_score_max, 5.0)
        self.assertEqual(result.appearance_score_source, "profile_default")
        self.assertEqual(result.max_score, 100.0)
        self.assertEqual(result.total_score, result.content_score + result.appearance_score)
        self.assertLessEqual(result.content_score, 95.0)


if __name__ == "__main__":
    unittest.main()
