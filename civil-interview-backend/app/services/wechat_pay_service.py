from __future__ import annotations

from datetime import datetime, timezone
import base64
import json
import logging
from pathlib import Path
import time
from typing import Any
from urllib.parse import quote
import uuid

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
import requests

from app.core.config import BACKEND_ROOT, settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentCallbackRequest, PaymentOrderCreateRequest


WECHAT_TRADE_SUCCESS = "SUCCESS"
WECHAT_REFUND_SUCCESS = "SUCCESS"
WECHAT_REFUND_PROCESSING = "PROCESSING"

logger = logging.getLogger(__name__)


class WechatPayService:
    def is_real_pay_enabled(self) -> bool:
        return bool(settings.wechat_pay_enabled)

    def get_pay_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        scene = str(data.scene or settings.wechat_pay_scene or "mini_program")
        if scene != "mini_program":
            raise HTTPException(status_code=400, detail="PC 端暂不直接拉起微信支付，请在小程序端完成购买")
        if not self.is_real_pay_enabled():
            raise HTTPException(status_code=503, detail="微信支付未启用，请联系管理员检查商户配置")
        return self._build_real_mini_program_payload(order, package, data)

    def query_order(self, order: PaymentOrder) -> dict | None:
        if not self.is_real_pay_enabled() or order.pay_channel != "wechat":
            return None
        logger.info(
            "Wechat Pay order query started",
            extra={"event": "wechat_pay.order.query.started", "order_no": order.order_no},
        )
        path = f"/v3/pay/transactions/out-trade-no/{quote(order.order_no, safe='')}?mchid={quote(settings.wechat_pay_mchid, safe='')}"
        result = self._request_wechat("GET", path)
        logger.info(
            "Wechat Pay order query completed",
            extra={"event": "wechat_pay.order.query.completed", "order_no": order.order_no},
        )
        return self._parse_wechat_transaction(result, mode="wechat_query", verified=True, headers={})

    def request_refund(self, order: PaymentOrder, amount_total: int, amount_refund: int, reason: str = "", out_refund_no: str = "") -> dict:
        if not self.is_real_pay_enabled() or order.pay_channel != "wechat":
            raise HTTPException(status_code=503, detail="微信真实退款未启用，不能执行退款")

        if amount_refund <= 0:
            raise HTTPException(status_code=400, detail="退款金额必须大于 0")

        body = {
            "out_trade_no": order.order_no,
            "out_refund_no": out_refund_no or f"RF{order.order_no}",
            "reason": (reason or "用户申请退款")[:80],
            "amount": {
                "refund": amount_refund,
                "total": amount_total,
                "currency": "CNY",
            },
        }
        if settings.wechat_pay_refund_notify_url:
            body["notify_url"] = settings.wechat_pay_refund_notify_url
        logger.info(
            "Wechat Pay refund request started",
            extra={
                "event": "wechat_pay.refund.started",
                "order_no": order.order_no,
                "amount_total": amount_total,
                "amount_refund": amount_refund,
            },
        )
        result = self._request_wechat("POST", "/v3/refund/domestic/refunds", body)
        logger.info(
            "Wechat Pay refund request completed",
            extra={
                "event": "wechat_pay.refund.completed",
                "order_no": order.order_no,
                "status": result.get("status") or "",
                "refund_id": result.get("refund_id") or "",
            },
        )
        return {
            "mode": "wechat",
            "status": result.get("status") or WECHAT_REFUND_PROCESSING,
            "outRefundNo": result.get("out_refund_no") or body["out_refund_no"],
            "refundId": result.get("refund_id") or "",
            "raw": result,
        }

    def parse_callback(self, data: PaymentCallbackRequest, headers: dict | None = None, raw_body: bytes | None = None) -> dict:
        headers = headers or {}
        mode = str(data.mode or data.callbackPayload.get("mode") or "wechat").lower()
        if mode != "wechat":
            raise HTTPException(status_code=400, detail="仅接受微信支付真实回调")
        if data.callbackPayload.get("resourcePlain") or data.callbackPayload.get("resource_plain"):
            raise HTTPException(status_code=400, detail="微信支付回调不能使用未验签明文资源")
        return self._parse_wechat_callback(data, headers, raw_body)

    def upload_shipping_info(self, transaction: dict, order: PaymentOrder, package: SubscriptionPackage) -> dict:
        if not settings.wechat_pay_shipping_upload_enabled:
            return {"skipped": True, "reason": "shipping_upload_disabled"}
        if not settings.wechat_miniprogram_app_secret:
            return {"skipped": True, "reason": "missing_miniprogram_app_secret"}

        access_token = self._get_miniprogram_access_token()
        url = f"{settings.wechat_miniprogram_api_base}/wxa/sec/order/upload_shipping_info"
        transaction_id = transaction.get("transactionId") or order.third_party_order_no
        openid = transaction.get("openid") or (order.extra_payload or {}).get("openId") or ""
        body = {
            "order_key": {
                "order_number_type": 2 if transaction_id else 1,
                "mchid": settings.wechat_pay_mchid,
            },
            "logistics_type": 3,
            "delivery_mode": 1,
            "shipping_list": [
                {
                    "item_desc": (settings.wechat_pay_shipping_item_desc or package.package_name)[:120],
                }
            ],
            "upload_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "payer": {"openid": openid},
        }
        if transaction_id:
            body["order_key"]["transaction_id"] = transaction_id
        else:
            body["order_key"]["out_trade_no"] = order.order_no

        response = requests.post(
            url,
            params={"access_token": access_token},
            json=body,
            timeout=settings.wechat_pay_request_timeout,
        )
        try:
            result = response.json()
        except ValueError:
            result = {"raw": response.text}
        if response.status_code >= 400 or int(result.get("errcode") or 0) != 0:
            return {"skipped": False, "success": False, "request": body, "response": result}
        return {"skipped": False, "success": True, "request": body, "response": result}

    def _parse_wechat_callback(self, data: PaymentCallbackRequest, headers: dict, raw_body: bytes | None) -> dict:
        picked_headers = self._pick_wechat_headers(headers)
        if not data.resource:
            raise HTTPException(status_code=400, detail="微信支付回调缺少 resource")
        if not raw_body:
            raise HTTPException(status_code=400, detail="微信支付回调缺少原始请求体，无法验签")

        self._verify_wechat_signature(raw_body, headers)
        plain = self._decrypt_resource(data.resource)
        return self._parse_wechat_transaction(plain, mode="wechat", verified=True, headers=picked_headers)

    def _parse_wechat_transaction(self, payload: dict[str, Any], mode: str, verified: bool, headers: dict) -> dict:
        self._assert_wechat_identity(payload)
        order_no = payload.get("out_trade_no") or payload.get("orderNo") or payload.get("order_no")
        if not order_no:
            raise HTTPException(status_code=400, detail="微信支付数据缺少 out_trade_no")

        trade_state = payload.get("trade_state") or payload.get("status") or ""
        amount = payload.get("amount") if isinstance(payload.get("amount"), dict) else {}
        return {
            "mode": mode,
            "verified": verified,
            "orderNo": order_no,
            "status": "paid" if trade_state == WECHAT_TRADE_SUCCESS else str(trade_state or "pending").lower(),
            "transactionId": payload.get("transaction_id") or payload.get("transactionId") or "",
            "paidAt": payload.get("success_time") or payload.get("paidAt") or datetime.now(timezone.utc).isoformat(),
            "amountTotal": amount.get("total") if amount else payload.get("amountTotal"),
            "appid": payload.get("appid") or "",
            "mchid": payload.get("mchid") or "",
            "openid": (payload.get("payer") or {}).get("openid") if isinstance(payload.get("payer"), dict) else "",
            "rawPayload": payload,
            "headers": headers,
        }

    def _build_real_mini_program_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        openid = self._resolve_openid(data)
        request_body = self._build_jsapi_order_body(order, package, openid)
        logger.info(
            "Wechat Pay JSAPI order request started",
            extra={
                "event": "wechat_pay.order.create.started",
                "order_no": order.order_no,
                "package_code": package.package_code,
                "amount": float(order.amount or 0),
            },
        )
        prepay_id = self._request_wechat_jsapi_order(request_body)
        mini_program_pay = self._build_miniprogram_pay_params(prepay_id)
        logger.info(
            "Wechat Pay JSAPI order request completed",
            extra={
                "event": "wechat_pay.order.create.completed",
                "order_no": order.order_no,
                "package_code": package.package_code,
            },
        )
        return {
            "mode": "wechat",
            "scene": "mini_program",
            "message": "已调用微信支付小程序/JSAPI 下单接口并生成 wx.requestPayment 参数。",
            "miniProgramPay": mini_program_pay,
            "prepayId": prepay_id,
            "appId": settings.wechat_pay_appid,
        }

    def _resolve_openid(self, data: PaymentOrderCreateRequest) -> str:
        self._validate_client_appid(data.appId)
        if data.openId:
            return data.openId
        if data.code:
            return self.exchange_code_for_openid(data.code)
        raise HTTPException(status_code=400, detail="小程序真实支付需要 openId 或 wx.login code")

    def exchange_code_for_openid(self, code: str) -> str:
        return str(self.exchange_code_for_session(code).get("openid") or "")

    def exchange_code_for_session(self, code: str) -> dict:
        self._require_miniprogram_secret()
        logger.info("Wechat mini program code exchange started", extra={"event": "wechat.openid.exchange.started"})
        response = requests.get(
            f"{settings.wechat_miniprogram_api_base}/sns/jscode2session",
            params={
                "appid": settings.wechat_pay_appid,
                "secret": settings.wechat_miniprogram_app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=settings.wechat_pay_request_timeout,
        )
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信登录换取 openid 响应不是 JSON") from exc
        if response.status_code >= 400 or result.get("errcode"):
            raise HTTPException(status_code=502, detail=f"微信登录换取 openid 失败: {result.get('errmsg') or response.text}")
        openid = result.get("openid")
        if not openid:
            raise HTTPException(status_code=502, detail="微信登录换取 openid 响应缺少 openid")
        logger.info("Wechat mini program code exchange completed", extra={"event": "wechat.openid.exchange.completed"})
        return {
            "openid": openid,
            "unionid": result.get("unionid") or "",
            "sessionKey": result.get("session_key") or "",
        }

    def _build_jsapi_order_body(self, order: PaymentOrder, package: SubscriptionPackage, openid: str) -> dict:
        self._require_real_pay_config()
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
                "openid": openid,
            },
            "attach": order.username,
        }

    def _request_wechat_jsapi_order(self, body: dict) -> str:
        result = self._request_wechat("POST", "/v3/pay/transactions/jsapi", body)
        prepay_id = result.get("prepay_id")
        if not prepay_id:
            raise HTTPException(status_code=502, detail="微信支付下单响应缺少 prepay_id")
        return prepay_id

    def _request_wechat(self, method: str, path: str, body: dict | None = None) -> dict:
        body_json = ""
        if body is not None:
            body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        authorization = self._build_authorization_header(method, path, body_json)
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "civil-interview-ai/1.0",
        }
        if settings.wechat_pay_public_key_id:
            headers["Wechatpay-Serial"] = settings.wechat_pay_public_key_id
        started_at = time.perf_counter()
        response = requests.request(
            method,
            f"{settings.wechat_pay_api_base}{path}",
            data=body_json.encode("utf-8") if body_json else None,
            headers=headers,
            timeout=settings.wechat_pay_request_timeout,
        )
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "Wechat Pay API request completed",
            extra={
                "event": "wechat_pay.api.completed",
                "wechat_method": method,
                "wechat_path": path.split("?")[0],
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        if response.status_code >= 400:
            detail = response.text or f"HTTP {response.status_code}"
            raise HTTPException(status_code=502, detail=f"微信支付接口调用失败: {detail}")
        if not response.text:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信支付接口响应不是 JSON") from exc

    def _build_authorization_header(self, method: str, path: str, body_json: str) -> str:
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        message = f"{method}\n{path}\n{timestamp}\n{nonce_str}\n{body_json}\n"
        signature = self._sign_message(message)
        return (
            "WECHATPAY2-SHA256-RSA2048 "
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

    def _verify_wechat_signature(self, raw_body: bytes, headers: dict) -> None:
        picked = self._pick_wechat_headers(headers)
        timestamp = picked["wechatpayTimestamp"]
        nonce = picked["wechatpayNonce"]
        signature = picked["wechatpaySignature"]
        if not all((timestamp, nonce, signature)):
            raise HTTPException(status_code=400, detail="微信支付回调缺少验签头")
        try:
            if abs(int(time.time()) - int(timestamp)) > 300:
                raise HTTPException(status_code=401, detail="微信支付回调时间戳已过期")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="微信支付回调时间戳无效") from exc

        public_key = self._load_wechatpay_verification_key(picked["wechatpaySerial"])
        message = f"{timestamp}\n{nonce}\n{raw_body.decode('utf-8')}\n".encode("utf-8")
        try:
            public_key.verify(
                base64.b64decode(signature),
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError) as exc:
            raise HTTPException(status_code=401, detail="微信支付回调验签失败") from exc

    def _decrypt_resource(self, resource: dict) -> dict:
        api_key = settings.wechat_pay_api_v3_key.encode("utf-8")
        if len(api_key) != 32:
            raise HTTPException(status_code=500, detail="WECHAT_PAY_API_V3_KEY 必须为 32 字节")
        try:
            nonce = str(resource["nonce"]).encode("utf-8")
            ciphertext = base64.b64decode(resource["ciphertext"])
            associated_data = str(resource.get("associated_data") or "").encode("utf-8")
            plaintext = AESGCM(api_key).decrypt(nonce, ciphertext, associated_data)
            return json.loads(plaintext.decode("utf-8"))
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"微信支付回调 resource 缺少字段: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="微信支付回调 resource 解密失败") from exc

    def _load_private_key(self):
        key_path = self._resolve_path(settings.wechat_pay_private_key_path)
        if not key_path.exists():
            raise HTTPException(status_code=500, detail=f"微信支付商户私钥不存在: {key_path}")
        try:
            return serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"微信支付商户私钥读取失败: {exc}") from exc

    def _load_wechatpay_verification_key(self, header_serial: str):
        header_serial = str(header_serial or "").upper()
        public_key_id = str(settings.wechat_pay_public_key_id or "").upper()
        if public_key_id or header_serial.startswith("PUB_KEY_ID_"):
            if header_serial and public_key_id and header_serial != public_key_id:
                raise HTTPException(status_code=401, detail="微信支付公钥 ID 不匹配")
            return self._load_wechatpay_public_key()
        return self._load_platform_certificate(header_serial).public_key()

    def _load_wechatpay_public_key(self):
        if not settings.wechat_pay_public_key_path:
            raise HTTPException(status_code=500, detail="缺少 WECHAT_PAY_PUBLIC_KEY_PATH，无法验证微信支付回调")
        key_path = self._resolve_path(settings.wechat_pay_public_key_path)
        if not key_path.exists():
            raise HTTPException(status_code=500, detail=f"微信支付公钥不存在: {key_path}")
        try:
            return serialization.load_pem_public_key(key_path.read_bytes())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"微信支付公钥读取失败: {exc}") from exc

    def _load_platform_certificate(self, header_serial: str):
        cert_path = self._resolve_path(settings.wechat_pay_platform_cert_path)
        if not cert_path.exists():
            self._refresh_platform_certificates(header_serial)
        if not cert_path.exists():
            raise HTTPException(status_code=500, detail=f"微信支付平台证书不存在: {cert_path}")
        try:
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"微信支付平台证书读取失败: {exc}") from exc

        cert_serial = format(cert.serial_number, "X").upper()
        expected_serial = (settings.wechat_pay_platform_serial_no or cert_serial).upper()
        callback_serial = str(header_serial or "").upper()
        if callback_serial and callback_serial not in {expected_serial, cert_serial}:
            self._refresh_platform_certificates(header_serial)
            try:
                cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
                cert_serial = format(cert.serial_number, "X").upper()
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"微信支付平台证书读取失败: {exc}") from exc
            if callback_serial != cert_serial:
                raise HTTPException(status_code=401, detail="微信支付回调平台证书序列号不匹配")
        return cert

    def _refresh_platform_certificates(self, target_serial: str = "") -> None:
        target_serial = str(target_serial or settings.wechat_pay_platform_serial_no or "").upper()
        cert_path = self._resolve_path(settings.wechat_pay_platform_cert_path)
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        result = self._request_wechat("GET", "/v3/certificates")
        certificates = result.get("data") if isinstance(result, dict) else []
        if not isinstance(certificates, list) or not certificates:
            raise HTTPException(status_code=502, detail="微信支付平台证书列表为空")

        fallback_pem = ""
        matched_pem = ""
        for item in certificates:
            if not isinstance(item, dict):
                continue
            serial_no = str(item.get("serial_no") or "").upper()
            encrypt_certificate = item.get("encrypt_certificate") or {}
            pem = self._decrypt_platform_certificate(encrypt_certificate)
            if not fallback_pem:
                fallback_pem = pem
            if serial_no:
                serial_path = cert_path.with_name(f"{cert_path.stem}_{serial_no}{cert_path.suffix}")
                serial_path.write_text(pem, encoding="utf-8")
            if target_serial and serial_no == target_serial:
                matched_pem = pem

        selected_pem = matched_pem or fallback_pem
        if not selected_pem:
            raise HTTPException(status_code=502, detail="微信支付平台证书下载失败")
        cert_path.write_text(selected_pem, encoding="utf-8")

    def _decrypt_platform_certificate(self, encrypt_certificate: dict) -> str:
        api_key = settings.wechat_pay_api_v3_key.encode("utf-8")
        if len(api_key) != 32:
            raise HTTPException(status_code=500, detail="WECHAT_PAY_API_V3_KEY 必须为 32 字节")
        if str(encrypt_certificate.get("algorithm") or "").upper() not in {"AEAD_AES_256_GCM", ""}:
            raise HTTPException(status_code=502, detail="不支持的微信支付平台证书加密算法")
        try:
            nonce = str(encrypt_certificate["nonce"]).encode("utf-8")
            ciphertext = base64.b64decode(encrypt_certificate["ciphertext"])
            associated_data = str(encrypt_certificate.get("associated_data") or "").encode("utf-8")
            plaintext = AESGCM(api_key).decrypt(nonce, ciphertext, associated_data)
            return plaintext.decode("utf-8")
        except KeyError as exc:
            raise HTTPException(status_code=502, detail=f"微信支付平台证书缺少字段: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="微信支付平台证书解密失败") from exc

    def _get_miniprogram_access_token(self) -> str:
        self._require_miniprogram_secret()
        response = requests.get(
            f"{settings.wechat_miniprogram_api_base}/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_pay_appid,
                "secret": settings.wechat_miniprogram_app_secret,
            },
            timeout=settings.wechat_pay_request_timeout,
        )
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信 access_token 响应不是 JSON") from exc
        if response.status_code >= 400 or result.get("errcode"):
            raise HTTPException(status_code=502, detail=f"获取微信 access_token 失败: {result.get('errmsg') or response.text}")
        token = result.get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="微信 access_token 响应缺少 access_token")
        return token

    def _assert_wechat_identity(self, payload: dict) -> None:
        if not settings.wechat_pay_strict_appid_check:
            return
        appid = payload.get("appid")
        mchid = payload.get("mchid")
        if not appid or appid != settings.wechat_pay_appid:
            raise HTTPException(status_code=400, detail="微信支付回调 appid 不匹配")
        if not mchid or mchid != settings.wechat_pay_mchid:
            raise HTTPException(status_code=400, detail="微信支付回调 mchid 不匹配")

    def _validate_client_appid(self, appid: str | None) -> None:
        if settings.wechat_pay_strict_appid_check and appid and appid != settings.wechat_pay_appid:
            raise HTTPException(status_code=400, detail="支付请求 appId 与后端配置不匹配")

    def _require_real_pay_config(self) -> None:
        missing = []
        for key, value in {
            "WECHAT_PAY_APPID": settings.wechat_pay_appid,
            "WECHAT_PAY_MCHID": settings.wechat_pay_mchid,
            "WECHAT_PAY_NOTIFY_URL": settings.wechat_pay_notify_url,
            "WECHAT_PAY_API_V3_KEY": settings.wechat_pay_api_v3_key,
            "WECHAT_PAY_SERIAL_NO": settings.wechat_pay_serial_no,
            "WECHAT_PAY_PRIVATE_KEY_PATH": settings.wechat_pay_private_key_path,
        }.items():
            if not value or str(value).startswith("MOCK_"):
                missing.append(key)
        if missing:
            raise HTTPException(status_code=500, detail=f"微信支付配置缺失: {', '.join(missing)}")
        if not str(settings.wechat_pay_notify_url).startswith("https://"):
            raise HTTPException(status_code=500, detail="WECHAT_PAY_NOTIFY_URL 必须是可公网访问的 HTTPS 地址")

    def _require_miniprogram_secret(self) -> None:
        if not settings.wechat_miniprogram_app_secret:
            raise HTTPException(status_code=500, detail="缺少 WECHAT_MINIPROGRAM_APP_SECRET，无法换取 openid")

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


wechat_pay_service = WechatPayService()
