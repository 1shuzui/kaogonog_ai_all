"""两阶段评分后处理测试。"""

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
    prepare_evidence_packet,
)


class ScoringCalculatorTestCase(unittest.TestCase):
    """验证证据抽取校验和证据约束评分。"""

    @classmethod
    def setUpClass(cls):
        bank = QuestionBank(settings.QUESTION_DB_PATH)
        cls.question = bank.get_question("HN-LX-20200606-01")
        cls.imported_question = bank.get_question("HN-20200816-01")

    def test_prepare_evidence_packet_filters_fake_quotes_and_adds_absence_evidence(self):
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

    def test_post_processing_requires_evidence_binding_for_deductions(self):
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
        repo_root = Path(__file__).resolve().parents[2]
        expected_files = [
            "低分1.txt",
            "18分左右.txt",
            "21分左右.txt",
            "中低分1.txt",
            "26分.txt",
            "28分.txt",
            "中高分1.txt",
            "标准1.txt",
        ]

        scores = {}
        for filename in expected_files:
            transcript = (repo_root / filename).read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
