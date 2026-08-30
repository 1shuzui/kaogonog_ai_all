"""
回归测试：转写已保存但点评尚未完成时，历史详情仍能展示考生答案。

转写和评分现在是两个阶段，历史详情不能把“尚未有最终分数”误判成“没有答案”。
"""
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, Question
from app.services.history_service import get_history_detail, get_history_list


class HistoryAnswerDetailRegressionTestCase(unittest.TestCase):
    """验证未评分文字稿可以被结果页历史详情读取。"""

    def setUp(self):
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
                id="history_transcript_exam",
                user_id="test-user",
                question_ids=["history_transcript_q1"],
                status="in_progress",
            )
        )
        self.db.add(
            Question(
                id="history_transcript_q1",
                stem="请谈谈如何做好群众沟通工作。",
                dimension="practical",
                province="national",
            )
        )
        self.db.add(
            ExamAnswer(
                exam_id="history_transcript_exam",
                question_id="history_transcript_q1",
                transcript="我会主动沟通群众，了解诉求后协调资源。",
                score_result={},
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_detail_returns_transcript_before_final_score_exists(self):
        detail = get_history_detail(self.db, "history_transcript_exam", "test-user")

        self.assertEqual(detail["examId"], "history_transcript_exam")
        self.assertEqual(detail["answers"][0]["transcript"], "我会主动沟通群众，了解诉求后协调资源。")
        self.assertEqual(detail["answers"][0]["scoringResult"], {})

    def test_list_includes_transcript_while_scoring_is_pending(self):
        listing = get_history_list(self.db, "test-user")

        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["list"][0]["examId"], "history_transcript_exam")
        self.assertEqual(listing["list"][0]["questionCount"], 1)
        self.assertEqual(listing["list"][0]["scoringStatus"], "pending")
        self.assertIn("点评中", listing["list"][0]["questionSummary"])

    def test_detail_does_not_reveal_another_users_answer(self):
        with self.assertRaises(Exception) as raised:
            get_history_detail(self.db, "history_transcript_exam", "another-user")

        self.assertEqual(getattr(raised.exception, "status_code", None), 404)


if __name__ == "__main__":
    unittest.main()
