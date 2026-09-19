"""
回归测试：转写先落库，以及题库参考答案仍通过外部模型完成评分。

这两个行为共同保证“转写已经有了但答案没有收录”时不会因为后续点评慢而丢失答案，
并验证题库参考答案只作为外部模型上下文，不会绕过统一的 LLM 评分链路。
"""
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.services import scoring_service


class AnswerPersistenceAndLocalScoringTestCase(unittest.IsolatedAsyncioTestCase):
    """验证答案持久化时序和题库参考答案的外部评分调用边界。"""

    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def _register_mysql_collation(dbapi_conn, _):
            dbapi_conn.create_collation(
                "utf8mb4_0900_ai_ci",
                lambda left, right: (left > right) - (left < right),
            )

        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            Exam(
                id="local_score_exam",
                user_id="test-user",
                question_ids=["local_score_q1"],
            )
        )
        self.db.add(
            ExamAnswer(
                exam_id="local_score_exam",
                question_id="local_score_q1",
                score_result={"mediaRecord": {"contentSha256": ""}},
            )
        )
        self.db.add(
            Question(
                id="local_score_q1",
                stem="请谈谈如何做好群众沟通工作。",
                dimension="practical",
                province="national",
                scoring_points=[{"content": "主动沟通协调", "score": 10}],
                keywords={
                    "scoring": ["沟通", "协调"],
                    "deducting": [],
                    "bonus": [],
                    "_meta": {
                        "coreKeywords": ["群众"],
                        "strongKeywords": ["落实"],
                        "referenceAnswer": "我会主动沟通群众，了解诉求，协调资源推动落实，并及时复盘完善机制。",
                    },
                },
            )
        )
        self.db.commit()

    async def asyncTearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_transcribe_persists_transcript_before_scoring(self):
        async def fake_transcribe_audio_file_with_meta(audio_bytes, filename="answer.webm", context_phrases=None):
            return {
                "transcript": "我会主动沟通群众，协调资源推动落实。",
                "asrMeta": {"audioSha256": ""},
                "needsRetry": False,
                "message": "",
            }

        with patch.object(
            scoring_service,
            "transcribe_audio_file_with_meta",
            new=fake_transcribe_audio_file_with_meta,
        ):
            result = await scoring_service.transcribe(
                b"audio-bytes",
                filename="answer.webm",
                db=self.db,
                question_id="local_score_q1",
                exam_id="local_score_exam",
            )

        answer = (
            self.db.query(ExamAnswer)
            .filter(
                ExamAnswer.exam_id == "local_score_exam",
                ExamAnswer.question_id == "local_score_q1",
            )
            .one()
        )
        self.assertEqual(answer.transcript, result["transcript"])
        self.assertTrue(result["transcriptSaved"])

    async def test_reference_answer_uses_external_scoring_model(self):
        llm_call = AsyncMock(
            side_effect=[
                {"evidence": {"present": [], "absent": [], "penalty": [], "bonus": []}},
                {
                    "dimension_scores": {"实务落地": 12},
                    "total_score": 12,
                    "overall_rationale": "回答包含沟通协调和落实措施。",
                },
            ]
        )
        with patch.object(scoring_service.settings, "llm_api_key", "test-key"), patch.object(
            scoring_service,
            "call_llm_api_async",
            new=llm_call,
        ), patch.object(
            scoring_service,
            "cache_get_json",
            new=AsyncMock(return_value=None),
        ), patch.object(
            scoring_service,
            "cache_set_json",
            new=AsyncMock(),
        ):
            result = await scoring_service.evaluate_answer(
                self.db,
                "local_score_q1",
                "我会主动沟通群众，协调资源推动落实，并及时复盘。",
                None,
            )

        self.assertFalse(scoring_service.settings.local_reference_scoring)
        self.assertEqual(result["scoringMode"], "llm")
        self.assertEqual(llm_call.await_count, 2)


    async def test_failed_evidence_uses_full_transcript_in_direct_scoring(self):
        transcript = "政府食堂开放是便民举措。首先了解游客需求，安排轮班和调休保障职工休息。其次做好食品安全和收费公示，最后根据反馈完善服务。"
        llm_call = AsyncMock(side_effect=[None, {
            "dimension_scores": {"综合分析": 15, "实务落地": 16, "应急应变": 10,
                                 "行政思维": 11, "逻辑结构": 12, "语言表达": 11},
            "overall_rationale": "回应了食堂开放的服务和轮班安排。",
        }])
        with patch.object(scoring_service.settings, "llm_api_key", "test-key"), patch.object(
            scoring_service, "call_llm_api_async", llm_call
        ), patch.object(scoring_service, "cache_get_json", AsyncMock(return_value=None)), patch.object(
            scoring_service, "cache_set_json", AsyncMock()
        ):
            result = await scoring_service.evaluate_answer(self.db, "local_score_q1", transcript, "local_score_exam")
        self.assertIn(transcript, llm_call.call_args_list[1].args[0])
        self.assertIn("【考生答案】", llm_call.call_args_list[1].args[0])
        self.assertGreater(result["totalScore"], 0)
        self.assertEqual(result["scoringMode"], "llm")
        self.assertNotIn("stageTwoPrompt", result["scoringTrace"])

    async def test_transcript_survives_interrupted_evaluation(self):
        transcript = "首先主动了解群众诉求，其次协调部门解决问题，最后及时跟进并完善工作机制。"
        with patch.object(scoring_service.settings, "llm_api_key", "test-key"), patch.object(
            scoring_service, "call_llm_api_async", AsyncMock(side_effect=RuntimeError("interrupted"))
        ), patch.object(scoring_service, "cache_get_json", AsyncMock(return_value=None)):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                await scoring_service.evaluate_answer(self.db, "local_score_q1", transcript, "local_score_exam")
        self.db.expire_all()
        answer = self.db.query(ExamAnswer).filter_by(exam_id="local_score_exam", question_id="local_score_q1").one()
        self.assertEqual(answer.transcript, transcript)
        self.assertNotIn("totalScore", answer.score_result)

    async def test_rescoring_updates_history_without_changing_completion_time(self):
        exam = self.db.query(Exam).filter_by(id="local_score_exam").one()
        exam.status = "completed"
        exam.end_time = datetime(2026, 9, 19, 4, 20)
        self.db.add(HistoryRecord(exam_id=exam.id, username="test-user", total_score=0))
        self.db.commit()
        scoring_service._persist_result(self.db, exam.id, "local_score_q1", "保存的作答", {
            "totalScore": 75, "maxScore": 100, "dimensions": []
        })
        history = self.db.query(HistoryRecord).filter_by(exam_id=exam.id).one()
        self.assertEqual(history.total_score, 75)
        self.assertEqual(history.completed_at, datetime(2026, 9, 19, 4, 20))


if __name__ == "__main__":
    unittest.main()
