from datetime import datetime, timezone
import hashlib
import hmac
import json

from fastapi import HTTPException
import requests

from app.core.config import settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentCallbackRequest, PaymentOrderCreateRequest


VIRTUAL_PAY_SCENE = "mini_program_virtual"


class WechatPayService:
    def get_pay_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        if data.payChannel != "wechat":
            raise HTTPException(status_code=400, detail="当前仅支持微信支付")
        if data.scene != VIRTUAL_PAY_SCENE:
            raise HTTPException(status_code=400, detail="小程序虚拟商品必须使用官方小程序虚拟支付")
        if not settings.wechat_pay_enabled:
            raise HTTPException(status_code=503, detail="小程序虚拟支付未启用")
        return self._build_virtual_payment_payload(order, package, data)

    def parse_callback(self, data: PaymentCallbackRequest, headers: dict | None = None) -> dict:
        headers = headers or {}
        mode = (data.mode or data.callbackPayload.get("mode") or "").lower()
        if mode == "wechat":
            return self._parse_wechat_callback_placeholder(data, headers)
        raise HTTPException(status_code=400, detail="不支持的微信支付回调模式")

    def _build_virtual_payment_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        self._assert_virtual_config(data)
        session_info = self._code_to_session(data.code or "")
        session_key = session_info["session_key"]
        openid = session_info.get("openid", "")
        if data.openId and data.openId != openid:
            raise HTTPException(status_code=400, detail="微信登录 openId 与支付用户不一致")

        product_id = self._get_virtual_product_id(package)
        goods_price = self._get_virtual_goods_price(order, package)
        attach = json.dumps(
            {"username": order.username, "packageCode": package.package_code},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sign_data_payload = {
            "offerId": settings.wechat_virtual_pay_offer_id,
            "buyQuantity": 1,
            "env": settings.wechat_virtual_pay_env,
            "currencyType": "CNY",
            "productId": product_id,
            "goodsPrice": goods_price,
            "outTradeNo": order.order_no,
            "attach": attach,
        }
        sign_data = json.dumps(sign_data_payload, ensure_ascii=False, separators=(",", ":"))
        app_key = self._get_virtual_app_key()
        pay_sig = self._hmac_sha256(app_key, f"requestVirtualPayment&{sign_data}")
        signature = self._hmac_sha256(session_key, sign_data)

        order.extra_payload = {
            **(order.extra_payload if isinstance(order.extra_payload, dict) else {}),
            "scene": VIRTUAL_PAY_SCENE,
            "openId": openid,
            "wechatUnionId": session_info.get("unionid", ""),
            "virtualPayEnv": settings.wechat_virtual_pay_env,
            "virtualPayMode": settings.wechat_virtual_pay_mode,
            "virtualProductId": product_id,
            "virtualGoodsPrice": goods_price,
            "idempotencyKey": data.idempotencyKey or "",
        }

        return {
            "mode": "wechat_virtual",
            "scene": VIRTUAL_PAY_SCENE,
            "message": "已生成官方小程序虚拟支付参数。",
            "virtualPay": {
                "mode": settings.wechat_virtual_pay_mode,
                "signData": sign_data,
                "paySig": pay_sig,
                "signature": signature,
            },
            "virtualPayMeta": {
                "env": settings.wechat_virtual_pay_env,
                "productId": product_id,
                "goodsPrice": goods_price,
                "outTradeNo": order.order_no,
            },
        }

    def _assert_virtual_config(self, data: PaymentOrderCreateRequest) -> None:
        if data.appId and data.appId != settings.wechat_pay_appid:
            raise HTTPException(status_code=400, detail="小程序 AppID 与服务端配置不一致")
        missing = []
        if not settings.wechat_pay_appid:
            missing.append("WECHAT_PAY_APPID")
        if not settings.wechat_miniprogram_app_secret:
            missing.append("WECHAT_MINIPROGRAM_APP_SECRET")
        if not settings.wechat_virtual_pay_offer_id:
            missing.append("WECHAT_VIRTUAL_PAY_OFFER_ID")
        if not self._get_virtual_app_key(raise_on_missing=False):
            missing.append("WECHAT_VIRTUAL_PAY_APP_KEY 或 WECHAT_VIRTUAL_PAY_SANDBOX_APP_KEY")
        if not data.code:
            missing.append("code")
        if missing:
            raise HTTPException(status_code=500, detail=f"小程序虚拟支付配置不完整: {', '.join(missing)}")

    def _code_to_session(self, code: str) -> dict:
        response = requests.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": settings.wechat_pay_appid,
                "secret": settings.wechat_miniprogram_app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=settings.wechat_pay_request_timeout,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"微信 code2Session 失败: HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信 code2Session 响应不是 JSON") from exc
        errcode = int(result.get("errcode") or 0)
        if errcode:
            errmsg = result.get("errmsg") or "unknown error"
            raise HTTPException(status_code=502, detail=f"微信 code2Session 失败: {errcode} {errmsg}")
        if not result.get("session_key"):
            raise HTTPException(status_code=502, detail="微信 code2Session 响应缺少 session_key")
        return result

    def _get_virtual_product_id(self, package: SubscriptionPackage) -> str:
        mapping = self._load_json_mapping(settings.wechat_virtual_pay_product_map_json)
        product_id = mapping.get(package.package_code)
        if not product_id:
            extra_config = package.extra_config if isinstance(package.extra_config, dict) else {}
            product_id = extra_config.get("virtualProductId") or package.package_code
        return str(product_id)

    def _get_virtual_goods_price(self, order: PaymentOrder, package: SubscriptionPackage) -> int:
        mapping = self._load_json_mapping(settings.wechat_virtual_pay_product_price_map_json)
        raw_price = mapping.get(package.package_code)
        if raw_price not in (None, ""):
            try:
                return int(raw_price)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=500, detail="小程序虚拟支付道具价格配置必须是分为单位的整数") from exc
        return int(round(float(order.amount or 0) * 100))

    def _get_virtual_app_key(self, raise_on_missing: bool = True) -> str:
        key = settings.wechat_virtual_pay_sandbox_app_key if settings.wechat_virtual_pay_env == 1 else settings.wechat_virtual_pay_app_key
        if not key and raise_on_missing:
            raise HTTPException(status_code=500, detail="小程序虚拟支付 AppKey 未配置")
        return key

    def _load_json_mapping(self, raw: str) -> dict:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="小程序虚拟支付 JSON 映射配置格式错误") from exc
        if not isinstance(value, dict):
            raise HTTPException(status_code=500, detail="小程序虚拟支付 JSON 映射配置必须是对象")
        return value

    def _hmac_sha256(self, key: str, message: str) -> str:
        return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    def _parse_wechat_callback_placeholder(self, data: PaymentCallbackRequest, headers: dict) -> dict:
        picked_headers = self._pick_wechat_headers(headers)
        resource_plain = data.resourcePlain or data.callbackPayload.get("resourcePlain") or data.callbackPayload.get("resource_plain")
        if not resource_plain:
            raise HTTPException(
                status_code=501,
                detail="微信服务端回调验签与 resource 解密尚未接入；小程序虚拟支付当前通过客户端成功回传确认订单。",
            )
        order_no = resource_plain.get("out_trade_no") or resource_plain.get("orderNo") or resource_plain.get("order_no")
        if not order_no:
            raise HTTPException(status_code=400, detail="微信回调明文缺少 out_trade_no")
        trade_state = resource_plain.get("trade_state") or resource_plain.get("status") or "SUCCESS"
        amount = resource_plain.get("amount") if isinstance(resource_plain.get("amount"), dict) else {}
        return {
            "mode": "wechat",
            "verified": False,
            "verifyPending": True,
            "orderNo": order_no,
            "status": "paid" if trade_state == "SUCCESS" else str(trade_state).lower(),
            "transactionId": resource_plain.get("transaction_id") or resource_plain.get("transactionId") or "",
            "paidAt": resource_plain.get("success_time") or resource_plain.get("paidAt") or datetime.now(timezone.utc).isoformat(),
            "amountTotal": amount.get("total") if amount else resource_plain.get("amountTotal"),
            "rawPayload": resource_plain,
            "headers": picked_headers,
        }

    def _pick_wechat_headers(self, headers: dict) -> dict:
        lower_headers = {str(k).lower(): v for k, v in headers.items()}
        return {
            "wechatpayTimestamp": lower_headers.get("wechatpay-timestamp", ""),
            "wechatpayNonce": lower_headers.get("wechatpay-nonce", ""),
            "wechatpaySignature": lower_headers.get("wechatpay-signature", ""),
            "wechatpaySerial": lower_headers.get("wechatpay-serial", ""),
        }


wechat_pay_service = WechatPayService()
