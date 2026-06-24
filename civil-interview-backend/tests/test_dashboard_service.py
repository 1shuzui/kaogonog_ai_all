"""
管理员数据看板服务测试。

用内存 SQLite 覆盖看板的管理员鉴权、账号排除、聚合口径和心跳幂等规则，避免依赖现网 MySQL 或系统资源。
"""
import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.v1 import api_router
from app.db.session import Base
from app.models.entities import Exam, PaymentOrder, UsageRecord, User, UserActivitySession
from app.schemas.common import DashboardHeartbeatRequest
from app.services.dashboard_service import (
    HEARTBEAT_MAX_SECONDS,
    get_dashboard_overview,
    list_dashboard_users,
    record_dashboard_heartbeat,
)


class DummyAuthUser:
    def __init__(self, username="admin", is_admin=True):
        self.username = username
        self.isAdmin = is_admin
        self.permissions = {}


class DashboardServiceTestCase(unittest.TestCase):
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
        self.admin = DummyAuthUser()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_user(self, username, registered_at=None):
        user = User(
            username=username,
            hashed_password="x",
            registered_at=registered_at or datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc),
            created_at=registered_at or datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(user)
        return user

    def test_admin_required_for_dashboard_queries(self):
        self.add_user("alice")
        self.db.commit()

        with self.assertRaises(HTTPException):
            list_dashboard_users(self.db, DummyAuthUser("alice", False))

    def test_dashboard_routes_are_registered(self):
        route_paths = {route.path for route in api_router.routes}

        for path in {
            "/admin/dashboard/overview",
            "/admin/dashboard/system",
            "/admin/dashboard/users",
            "/admin/dashboard/users/{username}",
            "/admin/dashboard/heartbeat",
        }:
            self.assertIn(path, route_paths)

    def test_user_list_excludes_admin_and_test_accounts(self):
        for username in ["admin", "test_user", "demo_user", "wx_test_openid", "real_user"]:
            self.add_user(username)
        self.db.commit()

        result = list_dashboard_users(self.db, self.admin)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["list"][0]["username"], "real_user")

    def test_heartbeat_is_idempotent_and_clamps_duration(self):
        self.add_user("alice")
        self.db.commit()

        payload = DashboardHeartbeatRequest(
            sessionId="session-1",
            eventId="event-1",
            clientType="pc",
            routePath="/admin",
            durationSeconds=999,
            activeAt="2026-06-18T10:00:00+00:00",
        )
        first = record_dashboard_heartbeat(self.db, DummyAuthUser("alice", False), payload)
        repeated = record_dashboard_heartbeat(self.db, DummyAuthUser("alice", False), payload)

        self.assertTrue(first["success"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(repeated["duplicate"])
        session = self.db.query(UserActivitySession).first()
        self.assertEqual(session.duration_seconds, HEARTBEAT_MAX_SECONDS)
        self.assertEqual(first["activeSeconds"], HEARTBEAT_MAX_SECONDS)

    def test_overview_aggregates_user_usage_payment_and_active_seconds(self):
        user = self.add_user("alice", datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc))
        self.add_user("test_skip", datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc))
        exam = Exam(id="exam_1", user_id="alice", question_ids=["q1"], status="completed")
        self.db.add(exam)
        self.db.flush()
        self.db.add(UsageRecord(
            username="alice",
            exam_id=exam.id,
            question_id="q1",
            usage_type="practice",
            usage_seconds=180,
            billed_minutes=3,
            reported_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        ))
        self.db.add(PaymentOrder(
            order_no="ORDER1",
            username="alice",
            package_code="trial_3h",
            package_type="hourly",
            amount="99.00",
            status="paid",
            paid_at=datetime(2026, 6, 18, 10, 10, tzinfo=timezone.utc),
            created_at=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        ))
        self.db.commit()

        record_dashboard_heartbeat(
            self.db,
            DummyAuthUser("alice", False),
            DashboardHeartbeatRequest(
                sessionId="session-1",
                eventId="event-2",
                clientType="pc",
                routePath="/",
                durationSeconds=60,
                activeAt="2026-06-18T10:00:00+00:00",
            ),
        )

        result = get_dashboard_overview(
            self.db,
            self.admin,
            user_start_date="2026-06-18",
            user_end_date="2026-06-18",
        )

        self.assertEqual(result["users"]["totalUsers"], 1)
        self.assertEqual(result["users"]["registrations"], 1)
        self.assertEqual(result["users"]["activeUsers"], 1)
        self.assertEqual(result["users"]["activeSeconds"], 60)
        self.assertEqual(result["usage"]["records"], 1)
        self.assertEqual(result["usage"]["usageSeconds"], 180)
        self.assertEqual(result["payments"]["paidOrders"], 1)
        self.assertEqual(result["payments"]["netAmount"], 99.0)


if __name__ == "__main__":
    unittest.main()
