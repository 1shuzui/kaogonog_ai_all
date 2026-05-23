import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.services.exam_service import complete_exam


class TestExamServiceRegression(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        now = datetime.now(timezone.utc)
        self.db.add(
            Question(
                id="q_complete_1",
                stem="请谈谈基层治理中的沟通协调。",
                dimension="analysis",
                province="jiangsu",
            )
        )
        self.db.add(
            Exam(
                id="exam_complete_1",
                user_id="tester",
                question_ids=["q_complete_1"],
                status="in_progress",
                start_time=now,
            )
        )
        self.db.add(
            ExamAnswer(
                exam_id="exam_complete_1",
                question_id="q_complete_1",
                transcript="作答内容",
                score_result={
                    "totalScore": 82.5,
                    "dimensions": [{"name": "综合分析", "score": 16.5, "maxScore": 20}],
                },
                answered_at=now,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_complete_exam_is_idempotent_for_repeated_submit(self):
        first = complete_exam(self.db, "exam_complete_1")
        second = complete_exam(self.db, "exam_complete_1")
        records = self.db.query(HistoryRecord).filter(HistoryRecord.exam_id == "exam_complete_1").all()

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(len(records), 1)
        self.assertEqual(second["finalScore"], 82.5)
        self.assertEqual(second["questionCount"], 1)


if __name__ == "__main__":
    unittest.main()
