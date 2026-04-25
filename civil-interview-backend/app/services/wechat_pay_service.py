from datetime import datetime, timezone
import base64
import hashlib
import json
from pathlib import Path
import time
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import HTTPException
import requests

from app.core.config import BACKEND_ROOT, settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentCallbackRequest, PaymentOrderCreateRequest


class WechatPayService:
    def get_pay_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        if data.scene != "mini_program":
            return self._build_mock_payload(order, package, data, reason="当前仅预置小程序支付框架")
        if settings.wechat_pay_mock_mode or not settings.wechat_pay_enabled:
            return self._build_mock_payload(order, package, data)
        return self._build_real_mini_program_payload(order, package, data)

    def parse_callback(self, data: PaymentCallbackRequest, headers: dict | None = None) -> dict:
        headers = headers or {}
        mode = (data.mode or data.callbackPayload.get("mode") or "mock").lower()
        if mode == "mock":
            return self._parse_mock_callback(data, headers)
        if mode == "wechat":
            return self._parse_wechat_callback_placeholder(data, headers)
        raise HTTPException(status_code=400, detail="不支持的微信支付回调模式")

    def _parse_mock_callback(self, data: PaymentCallbackRequest, headers: dict) -> dict:
        if not data.orderNo:
            raise HTTPException(status_code=400, detail="mock 回调缺少 orderNo")
        return {
            "mode": "mock",
            "verified": True,
            "orderNo": data.orderNo,
            "status": data.status or "paid",
            "transactionId": data.thirdPartyOrderNo or f"mock_wx_txn_{data.orderNo}",
            "paidAt": data.paidAt or datetime.now(timezone.utc).isoformat(),
            "amountTotal": data.amountTotal,
            "rawPayload": data.callbackPayload or {"mock": True},
            "headers": self._pick_wechat_headers(headers),
        }

    def _parse_wechat_callback_placeholder(self, data: PaymentCallbackRequest, headers: dict) -> dict:
        picked_headers = self._pick_wechat_headers(headers)
        resource_plain = data.resourcePlain or data.callbackPayload.get("resourcePlain") or data.callbackPayload.get("resource_plain")
        if not resource_plain:
            raise HTTPException(
                status_code=501,
                detail="真实微信回调验签与 resource 解密尚未接入；当前可用 mode=mock 或传入 resourcePlain 做结构联调",
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
            "realCallbackTodo": {
                "step1": "用微信平台证书校验 Wechatpay-Signature",
                "step2": "用 WECHAT_PAY_API_V3_KEY 解密 resource",
                "step3": "校验 mchid、appid、金额、订单号",
                "step4": "幂等更新订单和订阅权益",
            },
        }

    def _build_real_mini_program_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        if not data.openId:
            raise HTTPException(status_code=400, detail="小程序真实支付需要 openId")
        request_body = self._build_jsapi_order_body(order, package, data)
        prepay_id = self._request_wechat_jsapi_order(request_body)
        mini_program_pay = self._build_miniprogram_pay_params(prepay_id)
        return {
            "mode": "wechat",
            "scene": "mini_program",
            "message": "已调用微信支付小程序/JSAPI 下单接口并生成 wx.requestPayment 参数。",
            "miniProgramPay": mini_program_pay,
            "unifiedOrderRequest": request_body,
        }

    def _build_jsapi_order_body(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        return {
            "appid": settings.wechat_pay_appid,
            "mchid": settings.wechat_pay_mchid,
            "description": package.package_name[:127],
            "out_trade_no": order.order_no,
            "notify_url": settings.wechat_pay_notify_url,
            "amount": {
                "total": int(round(float(order.amount or 0) * 100)),
                "currency": "CNY",
            },
            "payer": {
                "openid": data.openId,
            },
            "attach": order.username,
        }

    def _request_wechat_jsapi_order(self, body: dict) -> str:
        method = "POST"
        path = "/v3/pay/transactions/jsapi"
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        authorization = self._build_authorization_header(method, path, body_json)
        response = requests.post(
            f"{settings.wechat_pay_api_base}{path}",
            data=body_json.encode("utf-8"),
            headers={
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=settings.wechat_pay_request_timeout,
        )
        if response.status_code >= 400:
            detail = response.text or f"HTTP {response.status_code}"
            raise HTTPException(status_code=502, detail=f"微信支付下单失败: {detail}")
        result = response.json()
        prepay_id = result.get("prepay_id")
        if not prepay_id:
            raise HTTPException(status_code=502, detail="微信支付下单响应缺少 prepay_id")
        return prepay_id

    def _build_authorization_header(self, method: str, path: str, body_json: str) -> str:
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        message = f"{method}\n{path}\n{timestamp}\n{nonce_str}\n{body_json}\n"
        signature = self._sign_message(message)
        return (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{settings.wechat_pay_mchid}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{settings.wechat_pay_serial_no}"'
        )

    def _build_miniprogram_pay_params(self, prepay_id: str) -> dict:
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        package_value = f"prepay_id={prepay_id}"
        message = f"{settings.wechat_pay_appid}\n{timestamp}\n{nonce_str}\n{package_value}\n"
        pay_sign = self._sign_message(message)
        return {
            "appId": settings.wechat_pay_appid,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package_value,
            "signType": "RSA",
            "paySign": pay_sign,
            "prepayId": prepay_id,
        }

    def _sign_message(self, message: str) -> str:
        private_key = self._load_private_key()
        signature = private_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _load_private_key(self):
        key_path = self._resolve_path(settings.wechat_pay_private_key_path)
        if not key_path.exists():
            raise HTTPException(status_code=500, detail=f"微信支付商户私钥不存在: {key_path}")
        try:
            return serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"微信支付商户私钥读取失败: {exc}") from exc

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return BACKEND_ROOT / path

    def _pick_wechat_headers(self, headers: dict) -> dict:
        lower_headers = {str(k).lower(): v for k, v in headers.items()}
        return {
            "wechatpayTimestamp": lower_headers.get("wechatpay-timestamp", ""),
            "wechatpayNonce": lower_headers.get("wechatpay-nonce", ""),
            "wechatpaySignature": lower_headers.get("wechatpay-signature", ""),
            "wechatpaySerial": lower_headers.get("wechatpay-serial", ""),
        }

    def _build_mock_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest, reason: str = "待替换真实商户配置") -> dict:
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        package_value = f"prepay_id=mock_{order.order_no}"
        mock_prepay_id = f"mock_prepay_{order.order_no}"
        pay_sign = hashlib.sha256(f"{order.order_no}|{timestamp}|{nonce_str}".encode("utf-8")).hexdigest()
        return {
            "mode": "mock",
            "scene": "mini_program",
            "message": "当前返回的是微信小程序支付 mock 数据，拿到真实商户资料后替换为真实下单结果。",
            "mockConfig": {
                "appid": settings.wechat_pay_appid,
                "mchid": settings.wechat_pay_mchid,
                "notifyUrl": settings.wechat_pay_notify_url,
                "reason": reason,
                "replaceFields": [
                    "WECHAT_PAY_ENABLED",
                    "WECHAT_PAY_MOCK_MODE",
                    "WECHAT_PAY_APPID",
                    "WECHAT_PAY_MCHID",
                    "WECHAT_PAY_NOTIFY_URL",
                    "WECHAT_PAY_API_V3_KEY",
                    "WECHAT_PAY_SERIAL_NO",
                    "WECHAT_PAY_PRIVATE_KEY_PATH",
                    "WECHAT_PAY_PLATFORM_CERT_PATH",
                ],
            },
            "miniProgramPay": {
                "appId": settings.wechat_pay_appid,
                "timeStamp": timestamp,
                "nonceStr": nonce_str,
                "package": package_value,
                "signType": "RSA",
                "paySign": pay_sign,
                "prepayId": mock_prepay_id,
            },
            "unifiedOrderRequestPreview": {
                "appid": settings.wechat_pay_appid,
                "mchid": settings.wechat_pay_mchid,
                "description": package.package_name,
                "out_trade_no": order.order_no,
                "notify_url": settings.wechat_pay_notify_url,
                "amount": {"total": int(round(float(order.amount or 0) * 100))},
                "payer": {
                    "openid": data.openId or "mock_openid_replace_me",
                },
                "attach": order.username,
            },
        }


wechat_pay_service = WechatPayService()
