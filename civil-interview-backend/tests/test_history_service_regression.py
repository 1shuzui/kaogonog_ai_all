import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.services.history_service import get_history_list, get_history_stats, get_history_trend


class TestHistoryServiceRegression(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        now = datetime.now(timezone.utc)
        question = Question(
            id="q_history_1",
            stem="请谈谈基层治理中的沟通协调。",
            dimension="analysis",
            province="national",
        )
        exam = Exam(
            id="exam_history_1",
            user_id="tester",
            question_ids=["q_history_1"],
            status="completed",
            start_time=now - timedelta(minutes=10),
            end_time=now,
        )
        answer = ExamAnswer(
            exam_id="exam_history_1",
            question_id="q_history_1",
            transcript="我的作答内容",
            score_result={
                "totalScore": 82.5,
                "maxScore": 100,
                "grade": "B",
                "dimensions": [{"name": "综合分析", "score": 16.5, "maxScore": 20}],
                "mediaRecord": {"fileUrl": "/uploads/demo.webm"},
            },
            answered_at=now,
        )
        record = HistoryRecord(
            exam_id="exam_history_1",
            username="tester",
            question_count=1,
            total_score=82.5,
            max_score=100,
            grade="B",
            province="national",
            dimensions=[{"name": "综合分析", "score": 16.5, "maxScore": 20}],
            completed_at=now,
        )

        self.db.add_all([question, exam, answer, record])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_history_endpoints_can_read_persisted_scores(self):
        listing = get_history_list(self.db, "tester", current=1, page_size=10)
        stats = get_history_stats(self.db, "tester")
        trend = get_history_trend(self.db, "tester", days=30)

        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["list"][0]["totalScore"], 82.5)
        self.assertEqual(listing["list"][0]["status"], "completed")
        self.assertEqual(stats["totalExams"], 1)
        self.assertEqual(stats["avgScore"], 82.5)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["score"], 82.5)


if __name__ == "__main__":
    unittest.main()
