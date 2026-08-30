"""支付确认只覆盖到账权威性、原子发放和幂等三个关键边界。"""
import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import PaymentVirtualConfirmRequest
from app.services.payment_service import confirm_virtual_payment_order, verify_virtual_payment_order
import app.services.payment_service as payment_service


class DummyAuthUser:
    def __init__(self, username="buyer"):
        self.username = username


class PaymentConfirmationSecurityTestCase(unittest.TestCase):
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
        self.db.add_all([
            User(username="buyer", hashed_password="x", preferences={}),
            SubscriptionPackage(
                package_code="trial_3h",
                package_name="3小时套餐",
                package_type="hourly",
                price=Decimal("0.01"),
                total_minutes=180,
                daily_limit_minutes=180,
                duration_days=0,
                is_active=True,
            ),
            PaymentOrder(
                order_no="PAY_SECURE_1",
                username="buyer",
                package_code="trial_3h",
                package_type="hourly",
                amount=Decimal("0.01"),
                status="pending",
                callback_payload={},
                extra_payload={
                    "openId": "openid_buyer",
                    "virtualPayEnv": 0,
                    "virtualProductId": "trial_3h",
                    "virtualGoodsPrice": 1,
                },
            ),
        ])
        self.db.commit()
        self.original_query = payment_service.wechat_pay_service.query_virtual_order
        self.original_notify = payment_service.wechat_pay_service.notify_provide_goods

    def tearDown(self):
        payment_service.wechat_pay_service.query_virtual_order = self.original_query
        payment_service.wechat_pay_service.notify_provide_goods = self.original_notify
        self.db.close()
        self.engine.dispose()

    def _confirm(self):
        return confirm_virtual_payment_order(
            self.db,
            DummyAuthUser(),
            "PAY_SECURE_1",
            PaymentVirtualConfirmRequest(
                scene="mini_program_virtual",
                payResult="success",
                thirdPartyOrderNo="UNTRUSTED_CLIENT_ID",
                rawResult={"client": "success"},
            ),
        )

    def test_unverified_order_stays_pending_and_grants_no_subscription(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": False,
            "transactionId": "",
            "amountTotal": None,
            "paidAt": "",
            "raw": {"trade_state": "NOTPAY"},
            "request": {"order_id": order.order_no},
        }

        with self.assertRaises(HTTPException) as raised:
            self._confirm()

        self.assertEqual(raised.exception.status_code, 409)
        self.db.expire_all()
        order = self.db.query(PaymentOrder).filter(PaymentOrder.order_no == "PAY_SECURE_1").one()
        self.assertEqual(order.status, "pending")
        self.assertEqual(self.db.query(UserSubscription).count(), 0)

    def test_verified_order_grants_once_and_uses_authoritative_transaction(self):
        calls = []

        def verified_query(order, package):
            calls.append(order.order_no)
            return {
                "verified": True,
                "transactionId": "WX_AUTHORITATIVE_1",
                "amountTotal": 1,
                "paidAt": "2026-08-24T10:00:00+00:00",
                "raw": {"trade_state": "SUCCESS", "goods_price": 1},
                "request": {"order_id": order.order_no},
            }

        payment_service.wechat_pay_service.query_virtual_order = verified_query

        first = self._confirm()
        second = self._confirm()

        self.assertTrue(first["success"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(calls, ["PAY_SECURE_1"])
        order = self.db.query(PaymentOrder).filter(PaymentOrder.order_no == "PAY_SECURE_1").one()
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.third_party_order_no, "WX_AUTHORITATIVE_1")
        self.assertTrue(order.callback_payload["verified"])
        self.assertEqual(self.db.query(UserSubscription).count(), 1)

    def test_authoritative_amount_mismatch_is_rejected(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "transactionId": "WX_WRONG_AMOUNT",
            "amountTotal": 2,
            "paidAt": "2026-08-24T10:00:00+00:00",
            "raw": {"trade_state": "SUCCESS", "goods_price": 2},
            "request": {"order_id": order.order_no},
        }

        with self.assertRaises(HTTPException) as raised:
            self._confirm()

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.db.query(UserSubscription).count(), 0)

    def test_authoritative_amount_is_required_before_entitlement_grant(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "transactionId": "WX_WITHOUT_AMOUNT",
            "amountTotal": None,
            "paidAt": "2026-08-24T10:00:00+00:00",
            "raw": {"order": {"status": 2, "order_id": order.order_no}},
            "request": {"order_id": order.order_no, "openid": "must-not-leak"},
        }

        with self.assertRaises(HTTPException) as raised:
            self._confirm()

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.db.query(UserSubscription).count(), 0)

    def test_verify_response_does_not_expose_raw_wechat_payload_or_openid(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "transactionId": "WX_SAFE_RESPONSE",
            "amountTotal": 1,
            "paidAt": "2026-08-24T10:00:00+00:00",
            "raw": {
                "order": {"status": 2, "order_id": order.order_no, "order_fee": 1},
                "internalTrace": "server-only",
            },
            "request": {"order_id": order.order_no, "openid": "must-not-leak"},
        }

        result = verify_virtual_payment_order(self.db, DummyAuthUser(), "PAY_SECURE_1")

        self.assertTrue(result["verification"]["verified"])
        self.assertEqual(result["verification"]["amountTotal"], 1)
        self.assertNotIn("raw", result["verification"])
        self.assertNotIn("request", result["verification"])
        order = self.db.query(PaymentOrder).filter(PaymentOrder.order_no == "PAY_SECURE_1").one()
        self.assertNotIn("openid", order.callback_payload.get("queryRequest", {}))

    def test_local_entitlement_commits_before_wechat_delivery_notification(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "orderId": order.order_no,
            "orderStatus": 2,
            "orderType": 0,
            "transactionId": "WX_DELIVERY_ORDER",
            "amountTotal": 1,
            "paidAt": "2026-08-24T10:00:00+00:00",
            "raw": {"order": {"status": 2, "order_id": order.order_no, "order_fee": 1}},
            "request": {"order_id": order.order_no, "env": 0},
        }
        delivery_calls = []

        def notify(order):
            delivery_calls.append((
                order.status,
                self.db.query(UserSubscription).filter(
                    UserSubscription.source_order_no == order.order_no,
                ).count(),
            ))
            return {"success": True, "orderId": order.order_no, "env": 0}

        payment_service.wechat_pay_service.notify_provide_goods = notify

        result = self._confirm()

        self.assertTrue(result["success"])
        self.assertEqual(delivery_calls, [("paid", 1)])
        order = self.db.query(PaymentOrder).filter(PaymentOrder.order_no == "PAY_SECURE_1").one()
        self.assertEqual(order.callback_payload["delivery"]["status"], "confirmed")

    def test_delivery_notification_failure_keeps_entitlement_and_marks_retry(self):
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "orderId": order.order_no,
            "orderStatus": 2,
            "orderType": 0,
            "transactionId": "WX_DELIVERY_RETRY",
            "amountTotal": 1,
            "paidAt": "2026-08-24T10:00:00+00:00",
            "raw": {"order": {"status": 2, "order_id": order.order_no, "order_fee": 1}},
            "request": {"order_id": order.order_no, "env": 0},
        }

        def notify(_order):
            raise HTTPException(status_code=502, detail="temporary delivery failure")

        payment_service.wechat_pay_service.notify_provide_goods = notify

        result = self._confirm()

        self.assertTrue(result["success"])
        order = self.db.query(PaymentOrder).filter(PaymentOrder.order_no == "PAY_SECURE_1").one()
        self.assertEqual(order.status, "paid")
        self.assertEqual(self.db.query(UserSubscription).count(), 1)
        self.assertEqual(order.callback_payload["delivery"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
