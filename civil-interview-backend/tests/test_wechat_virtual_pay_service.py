"""
微信虚拟支付测试锁定小程序审核最敏感的支付参数和订单确认路径。

所有虚拟训练权益都必须走官方小程序虚拟支付，不能回退普通微信支付或 PC mock 支付；手机端拉起失败时，
最容易出错的是 openId、offerId、env、paySig 和商品价格映射。这里用可控签名和假微信返回值验证这些字段。

@param: 无；用例通过 monkeypatch 构造微信配置、code2session 和订单查询响应。
@return: 无直接返回；断言通过表示虚拟支付请求和确认逻辑仍符合当前审核口径。
@raises ImportError: 支付服务、配置或订单模型导入失败时会中断测试。
"""
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
    """
    小程序下单 payload 必须来自 code2session，并包含官方虚拟支付要求的签名字段。

    手机端“当前仅支持微信支付”这类问题通常来自 openId、env、offerId、productId 或 paySig 不完整；
    这里用固定 session_key 和 sandbox key 锁住参数生成口径。

    @param monkeypatch: pytest 提供的隔离工具，用于替换配置、网络请求或外部服务返回值。
    @return: None；payload 内的 openId、商品价格和两类签名都符合预期时通过。
    @raises AssertionError: 虚拟支付参数缺失、价格不一致或签名计算漂移时失败。
    """
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
    """
    虚拟训练权益不能接受普通微信支付 channel。

    小程序审核要求所有虚拟商品购买接入官方虚拟支付；这里锁住服务端兜底，防止前端传错 payChannel 后悄悄回退普通支付。

    @param monkeypatch: pytest 提供的隔离工具，用于替换配置、网络请求或外部服务返回值。
    @return: None；非虚拟支付 channel 被 400 拒绝时通过。
    @raises AssertionError: 普通微信支付被接受或错误信息不含审核口径时失败。
    """
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
    """
    本地订单金额要跟微信虚拟支付道具价格对齐。

    套餐页展示价和微信商品价一旦不一致，审核和到账都会出现解释不清的差异；
    这里用 1 分钱道具确认服务层会按实际 goodsPrice 修正订单金额。

    @param: 无；构造 99 元本地订单和 1 分钱虚拟支付元数据。
    @return: None；订单金额被同步为 0.01 时通过。
    @raises AssertionError: 本地订单没有跟随微信商品价格修正时失败。
    """
    order = PaymentOrder(order_no="PAY_TEST_002", username="alice", amount=Decimal("99.00"), extra_payload={})

    _sync_order_amount_to_virtual_goods_price(order, {"virtualPayMeta": {"goodsPrice": 1}})

    assert order.amount == Decimal("0.01")


def test_virtual_pay_confirm_extracts_transaction_id_from_raw_result():
    """
    小程序支付确认要能从原始 rawResult 中提取微信交易号。

    手机端拉起虚拟支付后，前端回传字段可能嵌在 WeChatPayInfo 里；提取不到交易号会让后续查单和退款缺少凭证。

    @param: 无；构造只包含 rawResult 的确认对象。
    @return: None；能读出 TransactionId 时通过。
    @raises AssertionError: 微信交易号提取失败时失败。
    """
    data = type("Confirm", (), {
        "thirdPartyOrderNo": "",
        "rawResult": {"WeChatPayInfo": {"TransactionId": "420000000000000001"}},
    })()

    assert _extract_virtual_transaction_id(data) == "420000000000000001"


def test_virtual_pay_query_order_uses_access_token_and_pay_sig(monkeypatch):
    """
    查单请求必须先取 access_token，再用官方路径和请求体计算 pay_sig。

    微信虚拟支付查单不是普通商户订单查询；参数名、签名路径和 order_id 口径错一个，都会导致微信侧 502 或验单失败。

    @param monkeypatch: pytest 提供的隔离工具，用于替换配置、网络请求或外部服务返回值。
    @return: None；GET token、POST 查单和 pay_sig 校验都符合预期时通过。
    @raises AssertionError: 查单请求参数、签名或返回值归一化错误时失败。
    """
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
            """
            返回假微信响应体，保持 requests.Response 的最小接口。

            查单逻辑只依赖 `status_code` 和 `json()`；保留这个小替身可以专注验证 access_token、pay_sig 和请求体，而不引入真实网络。

            @param: 无；由被测服务调用。
            @return: 构造 FakeResponse 时传入的微信响应字典。
            @raises: 不主动抛出异常；异常场景由具体 payload 模拟。
            """
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
    """
    微信查单成功后必须把交易号和核验结果写回本地订单。

    本地 order.status 不是到账依据，只有微信侧确认后才能发权益；同时退款、客服排查和订单中心都依赖 third_party_order_no。

    @param monkeypatch: pytest 提供的隔离工具，用于替换配置、网络请求或外部服务返回值。
    @return: None；订单写入交易号、verified 和 verifyPending=false 时通过。
    @raises AssertionError: 查单结果没有持久化到订单 callback_payload 或交易号字段时失败。
    """
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
    """
    微信查单返回嵌套 order 结构时，也要提取支付状态、金额和交易号。

    微信不同接口版本和环境返回字段层级可能不同；如果只读顶层字段，订单中心和退款会拿不到真实交易信息。

    @param: 无；构造含 `order` 子对象的微信响应。
    @return: None；能提取已支付状态、微信交易号、金额和支付时间时通过。
    @raises AssertionError: 嵌套字段解析失败时失败。
    """
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


def test_virtual_pay_status_only_accepts_paid_or_fulfilment_states():
    """微信 XPay 状态 1 只是创建成功，只有 2/3/4 可以进入本地发货流程。"""
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 0}}) is False
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 1, "paid_fee": 1}}) is False
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 2}}) is True
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 3}}) is True
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 4}}) is True
    assert wechat_pay_service._virtual_order_is_paid({"order": {"status": 5, "paid_fee": 1}}) is False


def test_virtual_pay_amount_prefers_order_fee_over_paid_or_remaining_fee():
    """本地商品价应与微信订单金额 order_fee 对账，不能误用优惠后实付或剩余可退金额。"""
    result = {
        "order": {
            "status": 2,
            "order_fee": 100,
            "paid_fee": 80,
            "left_fee": 60,
        },
    }

    assert wechat_pay_service._extract_virtual_order_amount(result) == 100


def test_notify_provide_goods_uses_server_token_and_local_order_identity(monkeypatch):
    """本地权益到账后通知微信发货，只能使用服务端 token、订单号和下单环境。"""
    monkeypatch.setattr(wechat_pay_service, "_get_access_token", lambda: "SERVER_ACCESS_TOKEN")
    calls = []

    class FakeResponse:
        status_code = 200
        text = '{"errcode":0,"errmsg":"ok"}'

        def json(self):
            return {"errcode": 0, "errmsg": "ok"}

    def fake_post(url, params, json, headers, timeout):
        calls.append((url, params, json, headers, timeout))
        return FakeResponse()

    monkeypatch.setattr(wechat_pay_module.requests, "post", fake_post)
    order = PaymentOrder(
        order_no="PAY_DELIVER_001",
        username="alice",
        extra_payload={"openId": "must-not-be-sent", "virtualPayEnv": 1},
    )

    result = wechat_pay_service.notify_provide_goods(order)

    assert result["success"] is True
    assert calls[0][1] == {"access_token": "SERVER_ACCESS_TOKEN"}
    assert calls[0][2] == {"order_id": "PAY_DELIVER_001", "env": 1}
    assert "openId" not in calls[0][2]
