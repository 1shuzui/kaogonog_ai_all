import hashlib
import hmac
import json
from decimal import Decimal

from app.core.config import settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentOrderCreateRequest
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
        payChannel="wechat",
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
