"""
回归测试：转写先落库，以及题库参考答案仍通过外部模型完成评分。

这两个行为共同保证“转写已经有了但答案没有收录”时不会因为后续点评慢而丢失答案，
并验证题库参考答案只作为外部模型上下文，不会绕过统一的 LLM 评分链路。
"""
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, Question
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


if __name__ == "__main__":
    unittest.main()
