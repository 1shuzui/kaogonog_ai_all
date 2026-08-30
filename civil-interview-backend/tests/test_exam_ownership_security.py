"""个人考试与答案接口对不存在和他人资源使用同一种 404 边界。"""
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam
from app.services.exam_access_service import get_owned_exam_or_404


class ExamOwnershipSecurityTestCase(unittest.TestCase):
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
        self.db.add(Exam(id="private_exam", user_id="alice", question_ids=["q1"], status="in_progress"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_owner_succeeds_but_other_user_and_wrong_question_receive_same_404(self):
        exam = get_owned_exam_or_404(self.db, "private_exam", "alice", question_id="q1")
        self.assertEqual(exam.id, "private_exam")

        for exam_id, username, question_id in [
            ("private_exam", "bob", "q1"),
            ("missing_exam", "alice", "q1"),
            ("private_exam", "alice", "q2"),
        ]:
            with self.assertRaises(HTTPException) as raised:
                get_owned_exam_or_404(self.db, exam_id, username, question_id=question_id)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(raised.exception.detail, "记录不存在")


if __name__ == "__main__":
    unittest.main()
