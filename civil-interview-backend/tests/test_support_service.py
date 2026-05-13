import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import FeedbackTicket, User
from app.services.support_service import list_feedback, submit_feedback, update_feedback
from app.schemas.common import SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest


class DummyAuthUser:
    def __init__(self, username, is_admin=False):
        self.username = username
        self.isAdmin = is_admin
        self.permissions = {"canAccessPremiumModules": is_admin}


class SupportServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            User(username="alice", hashed_password="x", role="user"),
            User(username="admin", hashed_password="x", role="admin"),
        ])
        self.db.add_all([
            FeedbackTicket(
                username="alice",
                feedback_type="页面显示问题",
                summary="首页数据显示为空",
                province="江苏",
                status="pending",
                created_at=datetime.now(timezone.utc),
            ),
            FeedbackTicket(
                username="bob",
                feedback_type="支付或权益问题",
                summary="支付成功但套餐未到账",
                province="广东",
                status="handled",
                created_at=datetime.now(timezone.utc),
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_regular_user_only_sees_own_feedback(self):
        result = list_feedback(self.db, DummyAuthUser("alice"), scope="all")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["list"][0]["username"], "alice")

    def test_admin_can_see_all_feedback(self):
        result = list_feedback(self.db, DummyAuthUser("admin", is_admin=True), scope="all")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["summary"]["handled"], 1)

    def test_submit_and_handle_feedback(self):
        created = submit_feedback(
            self.db,
            DummyAuthUser("alice"),
            SupportFeedbackCreateRequest(
                type="题库内容问题",
                summary="这道题分类不对",
                province="江苏",
                questionId="q001",
            ),
        )
        self.assertTrue(created["success"])
        feedback_id = created["record"]["id"]

        updated = update_feedback(
            self.db,
            feedback_id,
            DummyAuthUser("admin", is_admin=True),
            SupportFeedbackUpdateRequest(status="handled", adminNote="已修正分类"),
        )
        self.assertEqual(updated["record"]["status"], "handled")
        self.assertEqual(updated["record"]["adminNote"], "已修正分类")


if __name__ == "__main__":
    unittest.main()
