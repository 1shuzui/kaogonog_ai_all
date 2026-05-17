import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, Question
from app.services.history_service import get_history_detail
from app.services.scoring_service import evaluate_answer


class ScoringImprovementSuggestionTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            Question(
                id="q_suggest_1",
                stem="群众反映窗口办理慢，你作为负责人怎么办？",
                dimension="practical",
                province="national",
                scoring_points=[
                    {"content": "核实群众诉求", "score": 10},
                    {"content": "优化办理流程", "score": 10},
                ],
                keywords={
                    "scoring": ["群众诉求", "流程优化", "反馈"],
                    "deducting": [],
                    "bonus": ["闭环"],
                    "_meta": {
                        "referenceAnswer": "先核实情况，再优化流程，最后做好反馈闭环。",
                        "coreKeywords": ["群众诉求", "流程优化"],
                    },
                },
            ),
            Exam(
                id="exam_suggest_1",
                user_id="tester",
                question_ids=["q_suggest_1"],
                status="completed",
                start_time=datetime.now(timezone.utc),
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_evaluate_answer_persists_model_improvement_suggestion(self):
        calls = []

        async def fake_llm(prompt, *args, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                return {
                    "evidence": {
                        "present": [{"id": "e1", "quote": "群众诉求", "dimension": "实务落地"}],
                        "absent": [],
                        "penalty": [],
                        "bonus": [],
                    }
                }
            if len(calls) == 2:
                return {
                    "dimension_scores": {
                        "综合分析": 12,
                        "实务落地": 16,
                        "应急应变": 10,
                        "行政思维": 10,
                        "逻辑结构": 11,
                        "语言表达": 12,
                    },
                    "total_score": 71,
                    "overall_rationale": "能够回应群众诉求，但流程细节还可展开。",
                }
            return {
                "summary": "要把流程优化讲得更具体。",
                "teacherComment": "已经有服务意识，建议补齐核实、协调和反馈闭环。",
                "diagnosisItems": ["流程优化措施偏概括"],
                "focusPoints": [{"order": "1", "title": "补流程", "hint": "说清排队、分流、反馈节点。"}],
                "missingKeywords": ["反馈闭环"],
                "expressionUpgrades": [{"before": "提高效率", "after": "通过预约分流和限时办结提升窗口效率"}],
                "sampleAnswer": "我会先核实窗口排队原因，再优化分流机制，并及时向群众反馈。",
                "rewriteOpening": "窗口服务慢，本质上是群众体验和流程效能问题。",
                "rewriteClosing": "后续我会持续跟踪办理时长，形成改进闭环。",
            }

        with patch("app.services.scoring_service.settings.llm_api_key", "test-key"), patch(
            "app.services.scoring_service.call_llm_api_async",
            fake_llm,
        ):
            result = await evaluate_answer(
                self.db,
                "q_suggest_1",
                "我会先核实群众诉求，分析窗口流程堵点，协调增设分流指引，推动流程优化，并及时反馈办理结果形成闭环。",
                "exam_suggest_1",
            )

        suggestion = result["answerImprovementSuggestion"]
        self.assertEqual(suggestion["source"], "model")
        self.assertEqual(suggestion["missingKeywords"], ["反馈闭环"])
        detail = get_history_detail(self.db, "exam_suggest_1", "tester")
        saved = detail["answers"][0]["scoringResult"]["answerImprovementSuggestion"]
        self.assertEqual(saved["teacherComment"], suggestion["teacherComment"])

    async def test_improvement_suggestion_falls_back_when_model_fails(self):
        calls = []

        async def fake_llm(prompt, *args, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                return {"evidence": {"present": [], "absent": [], "penalty": [], "bonus": []}}
            if len(calls) == 2:
                return {
                    "dimension_scores": {
                        "综合分析": 10,
                        "实务落地": 12,
                        "应急应变": 8,
                        "行政思维": 8,
                        "逻辑结构": 10,
                        "语言表达": 10,
                    },
                    "total_score": 58,
                    "overall_rationale": "基础作答完成。",
                }
            raise RuntimeError("suggestion model failed")

        with patch("app.services.scoring_service.settings.llm_api_key", "test-key"), patch(
            "app.services.scoring_service.call_llm_api_async",
            fake_llm,
        ):
            result = await evaluate_answer(
                self.db,
                "q_suggest_1",
                "我会核实群众诉求，协调窗口人员，优化流程安排，后续做好反馈和复盘。",
                "exam_suggest_1",
            )

        self.assertEqual(result["answerImprovementSuggestion"]["source"], "fallback")

    async def test_invalid_answer_does_not_call_model_for_improvement(self):
        llm = AsyncMock()
        with patch("app.services.scoring_service.settings.llm_api_key", "test-key"), patch(
            "app.services.scoring_service.call_llm_api_async",
            llm,
        ):
            result = await evaluate_answer(self.db, "q_suggest_1", "呃", "exam_suggest_1")

        llm.assert_not_called()
        self.assertEqual(result["answerImprovementSuggestion"]["source"], "fallback")


if __name__ == "__main__":
    unittest.main()
