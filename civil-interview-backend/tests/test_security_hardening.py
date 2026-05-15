import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.core.config import settings
from app.data.legal_documents import LATEST_TERMS_VERSION
from app.db.schema import ensure_runtime_schema
from app.db.session import Base
from app.models.entities import PaymentOrder, SubscriptionPackage, User
from app.schemas.common import PaymentCallbackRequest, WechatMiniLoginRequest
from app.services import auth_service, payment_service
from app.services.auth_service import login_or_register_miniprogram_wechat
from app.services.media_storage import media_response, save_media_upload
from app.services.payment_service import handle_payment_callback


class SecurityHardeningTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed_payment_order(self):
        user = User(username="buyer", hashed_password="hash", role="user")
        package = SubscriptionPackage(
            package_code="monthly_1h_day",
            package_name="包月套餐",
            package_type="monthly",
            price=Decimal("299.00"),
            total_minutes=1800,
            daily_limit_minutes=60,
            duration_days=30,
            is_active=True,
        )
        order = PaymentOrder(
            order_no="PAY_SECURE_1",
            username="buyer",
            package_code="monthly_1h_day",
            package_type="monthly",
            amount=Decimal("299.00"),
            pay_channel="wechat",
            status="pending",
        )
        self.db.add_all([user, package, order])
        self.db.commit()

    def test_wechat_mini_login_creates_regular_user(self):
        original = auth_service.wechat_pay_service.exchange_code_for_session
        auth_service.wechat_pay_service.exchange_code_for_session = lambda code: {
            "openid": "openid_security_test",
            "unionid": "unionid_security_test",
        }
        try:
            result = login_or_register_miniprogram_wechat(
                self.db,
                WechatMiniLoginRequest(code="wx_code", agreedTermsVersion=LATEST_TERMS_VERSION),
            )
        finally:
            auth_service.wechat_pay_service.exchange_code_for_session = original

        self.assertTrue(result["access_token"])
        self.assertTrue(result["isNewUser"])
        user = self.db.query(User).filter(User.username == result["username"]).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "user")
        self.assertEqual(user.wechat_mini_openid, "openid_security_test")

    def test_payment_callback_rejects_unverified_payload(self):
        original = payment_service.wechat_pay_service.parse_callback
        payment_service.wechat_pay_service.parse_callback = lambda data, headers=None, raw_body=None: {
            "mode": "wechat",
            "verified": False,
            "verifyPending": True,
            "orderNo": "PAY_SECURE_1",
        }
        try:
            with self.assertRaises(HTTPException) as ctx:
                handle_payment_callback(self.db, PaymentCallbackRequest())
        finally:
            payment_service.wechat_pay_service.parse_callback = original
        self.assertEqual(ctx.exception.status_code, 401)

    def test_payment_callback_requires_amount(self):
        self._seed_payment_order()
        original = payment_service.wechat_pay_service.parse_callback
        payment_service.wechat_pay_service.parse_callback = lambda data, headers=None, raw_body=None: {
            "mode": "wechat",
            "verified": True,
            "orderNo": "PAY_SECURE_1",
            "status": "paid",
            "transactionId": "wx_txn",
            "paidAt": "2026-05-15T00:00:00Z",
            "amountTotal": None,
            "rawPayload": {},
            "headers": {},
        }
        try:
            with self.assertRaises(HTTPException) as ctx:
                handle_payment_callback(self.db, PaymentCallbackRequest())
        finally:
            payment_service.wechat_pay_service.parse_callback = original
        self.assertEqual(ctx.exception.status_code, 400)

    def test_private_media_range_response(self):
        old_root = settings.media_storage_root
        old_optimize = settings.media_lossless_optimize_enabled
        with tempfile.TemporaryDirectory() as tmpdir:
            settings.media_storage_root = Path(tmpdir)
            settings.media_lossless_optimize_enabled = False
            try:
                record = save_media_upload(
                    b"\x1a\x45\xdf\xa3" + b"media-bytes-for-range",
                    "answer.webm",
                    media_type="audio/webm",
                    source="unit_test",
                )
                request = Request({
                    "type": "http",
                    "method": "GET",
                    "path": "/",
                    "headers": [(b"range", b"bytes=0-3")],
                })
                response = media_response(request, record)
            finally:
                settings.media_storage_root = old_root
                settings.media_lossless_optimize_enabled = old_optimize

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers["content-range"], "bytes 0-3/25")
        self.assertEqual(response.headers["accept-ranges"], "bytes")

    def test_runtime_schema_adds_media_record_to_existing_exam_answers(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(64) NOT NULL, hashed_password VARCHAR(128) NOT NULL)"))
                conn.execute(text("CREATE TABLE exam_answers (id INTEGER PRIMARY KEY, exam_id VARCHAR(32) NOT NULL, question_id VARCHAR(32) NOT NULL)"))

            ensure_runtime_schema(engine)
            with engine.connect() as conn:
                columns = {row[1] for row in conn.execute(text("PRAGMA table_info(exam_answers)"))}
            self.assertIn("media_record", columns)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
