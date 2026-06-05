import hashlib
import hmac
import json
from decimal import Decimal

from app.core.config import settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentOrderCreateRequest
from app.services.payment_service import _extract_virtual_transaction_id, _sync_order_amount_to_virtual_goods_price, _verify_order_with_wechat
import app.services.wechat_pay_service as wechat_pay_module
from app.services.wechat_pay_service import wechat_pay_service


def test_virtual_pay_payload_uses_code2session_and_official_params(monkeypatch):
    monkeypatch.setattr(settings, "wechat_pay_enabled", True)
    monkeypatch.setattr(settings, "wechat_pay_appid", "wx_test")
    monkeypatch.setattr(settings, "wechat_miniprogram_app_secret", "secret")
    monkeypatch.setattr(settings, "wechat_virtual_pay_offer_id", "1450536341")
    monkeypatch.setattr(settings, "wechat_virtual_pay_env", 1)
    monkeypatch.setattr(settings, "wechat_virtual_pay_sandbox_app_key", "sandbox_key")
    monkeypatch.setattr(settings, "wechat_virtual_pay_mode", "short_series_goods")
    monkeypatch.setattr(settings, "wechat_virtual_pay_product_map_json", '{"trial_3h":"trial_3h"}')
    monkeypatch.setattr(settings, "wechat_virtual_pay_product_price_map_json", "")
    monkeypatch.setattr(
        wechat_pay_service,
        "_code_to_session",
        lambda code: {"session_key": "session_key", "openid": "openid_1"},
    )

    order = PaymentOrder(order_no="PAY_TEST_001", username="alice", amount=Decimal("99.00"), extra_payload={})
    package = SubscriptionPackage(package_code="trial_3h", package_name="3小时套餐", package_type="hourly")
    data = PaymentOrderCreateRequest(
        packageCode="trial_3h",
        payChannel="wechat_virtual",
        appId="wx_test",
        code="wx_code",
        scene="mini_program_virtual",
    )

    payload = wechat_pay_service.get_pay_payload(order, package, data)
    virtual_pay = payload["virtualPay"]
    sign_data = virtual_pay["signData"]
    sign_data_payload = json.loads(sign_data)

    assert payload["mode"] == "wechat_virtual"
    assert virtual_pay["mode"] == "short_series_goods"
    assert sign_data_payload["offerId"] == "1450536341"
    assert sign_data_payload["env"] == 1
    assert sign_data_payload["productId"] == "trial_3h"
    assert sign_data_payload["goodsPrice"] == 9900
    assert sign_data_payload["outTradeNo"] == "PAY_TEST_001"
    assert virtual_pay["paySig"] == hmac.new(
        b"sandbox_key",
        f"requestVirtualPayment&{sign_data}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert virtual_pay["signature"] == hmac.new(b"session_key", sign_data.encode("utf-8"), hashlib.sha256).hexdigest()
    assert order.extra_payload["openId"] == "openid_1"


def test_virtual_pay_payload_rejects_non_virtual_channel(monkeypatch):
    monkeypatch.setattr(settings, "wechat_pay_enabled", True)
    order = PaymentOrder(order_no="PAY_TEST_001A", username="alice", amount=Decimal("99.00"), extra_payload={})
    package = SubscriptionPackage(package_code="trial_3h", package_name="3小时套餐", package_type="hourly")
    data = PaymentOrderCreateRequest(
        packageCode="trial_3h",
        payChannel="wechat",
        appId="wx_test",
        code="wx_code",
        scene="mini_program_virtual",
    )

    try:
        wechat_pay_service.get_pay_payload(order, package, data)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "官方小程序虚拟支付" in str(getattr(exc, "detail", ""))
    else:
        raise AssertionError("non-virtual payChannel should be rejected")


def test_virtual_pay_order_amount_follows_actual_goods_price():
    order = PaymentOrder(order_no="PAY_TEST_002", username="alice", amount=Decimal("99.00"), extra_payload={})

    _sync_order_amount_to_virtual_goods_price(order, {"virtualPayMeta": {"goodsPrice": 1}})

    assert order.amount == Decimal("0.01")


def test_virtual_pay_confirm_extracts_transaction_id_from_raw_result():
    data = type("Confirm", (), {
        "thirdPartyOrderNo": "",
        "rawResult": {"WeChatPayInfo": {"TransactionId": "420000000000000001"}},
    })()

    assert _extract_virtual_transaction_id(data) == "420000000000000001"


def test_virtual_pay_query_order_uses_access_token_and_pay_sig(monkeypatch):
    monkeypatch.setattr(settings, "wechat_pay_appid", "wx_test")
    monkeypatch.setattr(settings, "wechat_miniprogram_app_secret", "secret")
    monkeypatch.setattr(settings, "wechat_virtual_pay_offer_id", "1450536341")
    monkeypatch.setattr(settings, "wechat_virtual_pay_env", 1)
    monkeypatch.setattr(settings, "wechat_virtual_pay_sandbox_app_key", "sandbox_key")
    monkeypatch.setattr(settings, "wechat_virtual_pay_product_map_json", '{"trial_3h":"trial_3h"}')
    wechat_pay_service._access_token = ""
    wechat_pay_service._access_token_expires_at = 0
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, params, timeout):
        calls.append(("GET", url, params))
        return FakeResponse({"access_token": "ACCESS_TOKEN", "expires_in": 7200})

    def fake_post(url, params, data, headers, timeout):
        body = data.decode("utf-8")
        expected_sig = hmac.new(
            b"sandbox_key",
            f"{wechat_pay_module.X_PAY_QUERY_ORDER_PATH}&{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        calls.append(("POST", url, params, body))
        assert params["access_token"] == "ACCESS_TOKEN"
        assert params["pay_sig"] == expected_sig
        return FakeResponse({"trade_state": "SUCCESS", "transaction_id": "WX_ORDER_1", "goods_price": 1})

    monkeypatch.setattr(wechat_pay_module.requests, "get", fake_get)
    monkeypatch.setattr(wechat_pay_module.requests, "post", fake_post)

    order = PaymentOrder(
        order_no="PAY_TEST_003",
        username="alice",
        amount=Decimal("0.01"),
        extra_payload={"openId": "openid_1", "virtualPayEnv": 1, "virtualProductId": "trial_3h"},
    )
    package = SubscriptionPackage(package_code="trial_3h", package_name="3小时套餐", package_type="hourly")

    result = wechat_pay_service.query_virtual_order(order, package)

    assert result["verified"] is True
    assert result["transactionId"] == "WX_ORDER_1"
    assert result["request"]["order_id"] == "PAY_TEST_003"
    assert "out_trade_no" not in result["request"]
    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"


def test_verify_order_with_wechat_persists_transaction_id(monkeypatch):
    order = PaymentOrder(
        order_no="PAY_TEST_004",
        username="alice",
        amount=Decimal("0.01"),
        callback_payload={"verifyPending": True},
    )
    package = SubscriptionPackage(package_code="trial_3h", package_name="3小时套餐", package_type="hourly")
    monkeypatch.setattr(
        wechat_pay_service,
        "query_virtual_order",
        lambda order, package: {
            "verified": True,
            "transactionId": "WX_ORDER_2",
            "amountTotal": 1,
            "paidAt": "2026-05-21T12:00:00+00:00",
            "raw": {"trade_state": "SUCCESS"},
            "request": {"out_trade_no": "PAY_TEST_004"},
        },
    )

    result = _verify_order_with_wechat(order, package)

    assert result["verified"] is True
    assert order.third_party_order_no == "WX_ORDER_2"
    assert order.callback_payload["verified"] is True
    assert order.callback_payload["verifyPending"] is False


def test_virtual_pay_query_extracts_wechat_order_fields_from_nested_order():
    result = {
        "errcode": 0,
        "errmsg": "OK",
        "order": {
            "order_id": "PAY_TEST_005",
            "status": 3,
            "paid_fee": 1,
            "order_fee": 1,
            "paid_time": 1779258124,
            "wx_order_id": "VPO260520142140032797045",
            "wxpay_order_id": "4500000144202605202996404879",
            "channel_order_id": "20260520219109146",
        },
    }

    assert wechat_pay_service._virtual_order_is_paid(result) is True
    assert wechat_pay_service._extract_virtual_order_id(result) == "4500000144202605202996404879"
    assert wechat_pay_service._extract_virtual_order_amount(result) == 1
    assert wechat_pay_service._extract_virtual_paid_at(result).startswith("2026-05-20")
