"""
邀请码注册、首登绑定、后台纠错和报表聚合测试。

用内存 SQLite 覆盖邀请码核心规则，避免依赖现网 MySQL 或微信网络请求。
"""
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import InviteActivityDaily, InviteAuditLog, InviteCode, InvitePartner, InvitePaymentEvent, User
from app.schemas.common import (
    InviteAttributionCorrectionRequest,
    InviteCodeUpdateRequest,
    InviteReportQueryRequest,
    RegisterRequest,
    WechatMiniProgramInviteBindRequest,
)
from app.services.auth_service import register_user
from app.services.invite_service import (
    bind_registration_invite,
    bind_wechat_first_session_invite,
    create_first_session_token,
    delete_invite_code,
    delete_invite_partner,
    get_invite_report,
    record_payment_event_for_order,
    record_user_daily_activity,
    resolve_active_invite_code,
    update_invite_code,
)


class DummyAuthUser:
    def __init__(self, username="admin", is_admin=True):
        self.username = username
        self.isAdmin = is_admin
        self.permissions = {}


class DummyOrder:
    def __init__(self, order_no, username, amount, paid_at):
        self.order_no = order_no
        self.username = username
        self.amount = amount
        self.paid_at = paid_at
        self.status = "paid"


class InviteServiceTestCase(unittest.TestCase):
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
        self.partner = InvitePartner(name="渠道A", enabled=True)
        self.db.add(self.partner)
        self.db.flush()
        self.code = InviteCode(code="ABC-001", partner_id=self.partner.id, enabled=True)
        self.db.add(self.code)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_resolve_invite_code_normalizes_and_blocks_disabled(self):
        self.assertEqual(resolve_active_invite_code(self.db, " abc-001 ").code, "ABC-001")
        self.code.enabled = False
        self.db.commit()
        with self.assertRaises(HTTPException):
            resolve_active_invite_code(self.db, "ABC-001")

    def test_register_user_binds_invite_and_writes_registration_snapshot(self):
        result = register_user(
            self.db,
            RegisterRequest(username="alice", password="secret1", inviteCode="abc-001"),
        )
        self.assertTrue(result["success"])
        user = self.db.query(User).filter(User.username == "alice").first()
        self.assertEqual(user.invite_code, "ABC-001")
        self.assertEqual(user.invite_partner_id, self.partner.id)
        self.assertEqual(user.invite_source, "register")
        self.assertEqual(len(user.preferences or {}), 0)
        self.assertEqual(self.db.query(InviteActivityDaily).count(), 0)

    def test_register_user_rejects_invalid_invite(self):
        with self.assertRaises(HTTPException):
            register_user(
                self.db,
                RegisterRequest(username="alice", password="secret1", inviteCode="missing"),
            )

    def test_wechat_first_session_bind_uses_token_once(self):
        user = User(username="wxmp_user", hashed_password="x")
        self.db.add(user)
        self.db.flush()
        token = create_first_session_token(user)
        self.db.commit()

        result = bind_wechat_first_session_invite(
            self.db,
            DummyAuthUser("wxmp_user", False),
            WechatMiniProgramInviteBindRequest(inviteCode="ABC-001", inviteSessionToken=token),
        )

        self.assertTrue(result["success"])
        self.assertEqual(user.invite_code, "ABC-001")
        self.assertNotIn("wechatInviteFirstSession", user.preferences or {})
        repeated = bind_wechat_first_session_invite(
            self.db,
            DummyAuthUser("wxmp_user", False),
            WechatMiniProgramInviteBindRequest(inviteCode="ABC-001", inviteSessionToken=token),
        )
        self.assertTrue(repeated["success"])

    def test_admin_correction_writes_audit_without_changing_registration_snapshot(self):
        user = User(username="bob", hashed_password="x")
        self.db.add(user)
        self.db.flush()
        bind_registration_invite(self.db, user, "ABC-001", "register")
        second_partner = InvitePartner(name="渠道B", enabled=True)
        self.db.add(second_partner)
        self.db.flush()
        second_code = InviteCode(code="BETA", partner_id=second_partner.id, enabled=True)
        self.db.add(second_code)
        self.db.commit()

        from app.services.invite_service import correct_user_invite_attribution

        result = correct_user_invite_attribution(
            self.db,
            self.admin,
            "bob",
            InviteAttributionCorrectionRequest(inviteCode="BETA", reason="录入错误"),
        )

        self.assertTrue(result["success"])
        self.assertEqual(user.invite_code, "BETA")
        event = self.db.query(InviteAuditLog).first()
        self.assertEqual(event.action_type, "correct_user_attribution")
        report = get_invite_report(
            self.db,
            self.admin,
            InviteReportQueryRequest(startDate="2000-01-01", endDate="2999-12-31"),
        )
        self.assertEqual(report["summary"][0]["code"], "ABC-001")

    def test_delete_unused_code_and_partner_only_when_unreferenced(self):
        temp_partner = InvitePartner(name="临时渠道", enabled=True)
        self.db.add(temp_partner)
        self.db.flush()
        temp_code = InviteCode(code="TEMP", partner_id=temp_partner.id, enabled=True)
        self.db.add(temp_code)
        self.db.commit()

        code_result = delete_invite_code(self.db, self.admin, temp_code.id)
        self.assertTrue(code_result["success"])
        partner_result = delete_invite_partner(self.db, self.admin, temp_partner.id)
        self.assertTrue(partner_result["success"])

    def test_delete_blocks_referenced_code_and_partner_with_codes(self):
        with self.assertRaises(HTTPException):
            delete_invite_partner(self.db, self.admin, self.partner.id)

        user = User(username="used", hashed_password="x")
        self.db.add(user)
        self.db.flush()
        bind_registration_invite(self.db, user, "ABC-001", "register")
        self.db.commit()

        with self.assertRaises(HTTPException):
            delete_invite_code(self.db, self.admin, self.code.id)

    def test_used_invite_code_can_toggle_but_not_change_code(self):
        user = User(username="locked", hashed_password="x")
        self.db.add(user)
        self.db.flush()
        bind_registration_invite(self.db, user, "ABC-001", "register")
        self.db.commit()

        updated = update_invite_code(self.db, self.admin, self.code.id, InviteCodeUpdateRequest(enabled=False))
        self.assertFalse(updated["enabled"])
        with self.assertRaises(HTTPException):
            update_invite_code(self.db, self.admin, self.code.id, InviteCodeUpdateRequest(code="NEWCODE"))

    def test_daily_activity_and_payment_report_use_snapshots(self):
        from datetime import datetime, timezone

        user = User(username="buyer", hashed_password="x")
        self.db.add(user)
        self.db.flush()
        bind_registration_invite(self.db, user, "ABC-001", "register")
        record_user_daily_activity(self.db, user, datetime(2026, 6, 18, 2, 0, tzinfo=timezone.utc))
        record_user_daily_activity(self.db, user, datetime(2026, 6, 18, 3, 0, tzinfo=timezone.utc))
        self.db.flush()
        order = DummyOrder("PAY1", "buyer", "99.00", datetime(2026, 6, 18, 2, 30, tzinfo=timezone.utc))
        record_payment_event_for_order(self.db, order)
        self.db.commit()

        self.assertEqual(self.db.query(InviteActivityDaily).count(), 1)
        self.assertEqual(self.db.query(InvitePaymentEvent).count(), 1)
        report = get_invite_report(
            self.db,
            self.admin,
            InviteReportQueryRequest(startDate="2026-06-18", endDate="2026-06-18"),
        )
        self.assertEqual(report["totals"]["registrations"], 1)
        self.assertEqual(report["totals"]["activeUsers"], 1)
        self.assertEqual(report["totals"]["paidOrders"], 1)
        self.assertEqual(report["totals"]["netPaidAmount"], 99.0)


if __name__ == "__main__":
    unittest.main()
