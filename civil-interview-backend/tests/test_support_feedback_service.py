import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import api_router
from app.db.session import Base
from app.models.entities import SupportFeedback, User
from app.schemas.common import SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest
from app.services.support_service import (
    create_support_feedback,
    delete_support_feedback,
    list_support_feedback,
    update_support_feedback,
)


class DummyAuthUser:
    def __init__(self, username="alice", is_admin=False):
        self.username = username
        self.isAdmin = is_admin


class SupportFeedbackServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            User(username="alice", hashed_password="x"),
            User(username="bob", hashed_password="x"),
            User(username="admin", hashed_password="x"),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_support_routes_are_registered(self):
        route_paths = {route.path for route in api_router.routes}

        self.assertIn("/support/feedback", route_paths)
        self.assertIn("/support/feedback/attachments", route_paths)
        self.assertIn("/support/feedback/{feedback_id}", route_paths)

    def test_feedback_create_list_update_delete_uses_database_records(self):
        alice = DummyAuthUser("alice")
        admin = DummyAuthUser("admin", is_admin=True)

        created = create_support_feedback(
            self.db,
            alice,
            SupportFeedbackCreateRequest(
                type="页面显示问题",
                summary="筛选反馈接口返回 404",
                questionId="q001",
                contact="wechat",
                routePath="/pages/support/index",
                province="江苏",
                attachments=[{"url": "/uploads/support-feedback/demo.png", "filename": "demo.png"}],
            ),
        )
        self.db.add(
            SupportFeedback(
                username="bob",
                feedback_type="支付或权益问题",
                summary="支付状态未同步",
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

        mine = list_support_feedback(
            self.db,
            alice,
            current=1,
            page_size=200,
            feedback_type="undefined",
            status="undefined",
            province="undefined",
            keyword="undefined",
            scope="all",
        )
        self.assertEqual(mine["total"], 1)
        self.assertEqual(mine["list"][0]["summary"], "筛选反馈接口返回 404")
        self.assertEqual(mine["summary"]["mine"], 1)

        all_records = list_support_feedback(self.db, admin, current=1, page_size=200, scope="all")
        self.assertEqual(all_records["total"], 2)

        handled = update_support_feedback(
            self.db,
            admin,
            created["id"],
            SupportFeedbackUpdateRequest(status="handled", adminNote="已修复"),
        )
        self.assertEqual(handled["status"], "handled")
        self.assertEqual(handled["adminNote"], "已修复")
        self.assertTrue(handled["handledAt"])

        deleted = delete_support_feedback(self.db, admin, created["id"])
        self.assertTrue(deleted["success"])
        self.assertEqual(list_support_feedback(self.db, admin, scope="all")["total"], 1)

    def test_non_admin_cannot_update_feedback_status(self):
        created = create_support_feedback(
            self.db,
            DummyAuthUser("alice"),
            SupportFeedbackCreateRequest(type="其他建议", summary="请帮忙处理"),
        )

        with self.assertRaises(HTTPException):
            update_support_feedback(
                self.db,
                DummyAuthUser("alice"),
                created["id"],
                SupportFeedbackUpdateRequest(status="handled"),
            )


if __name__ == "__main__":
    unittest.main()
