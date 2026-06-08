"""
这个文件只负责和微信虚拟支付接口打交道；签名、现网/沙箱、查询和退款都集中在这里，便于排查审核或支付失败。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
from time import time

from fastapi import HTTPException
import requests

from app.core.config import settings
from app.models.entities import PaymentOrder, SubscriptionPackage
from app.schemas.common import PaymentOrderCreateRequest


VIRTUAL_PAY_SCENE = "mini_program_virtual"
X_PAY_QUERY_ORDER_PATH = "/xpay/query_order"
X_PAY_QUERY_ORDER_URL = f"https://api.weixin.qq.com{X_PAY_QUERY_ORDER_PATH}"
X_PAY_REFUND_ORDER_PATH = "/xpay/refund_order"
X_PAY_REFUND_ORDER_URL = f"https://api.weixin.qq.com{X_PAY_REFUND_ORDER_PATH}"


class WechatPayService:
    """
    WechatPayService 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    微信支付服务对接外部平台，注释需要说明现网配置、回调和退款查询的风险边界。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    _access_token: str = ""
    _access_token_expires_at: int = 0

    def get_pay_payload(self, order: PaymentOrder, package: SubscriptionPackage, data: PaymentOrderCreateRequest) -> dict:
        """
        get_pay_payload 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        微信支付服务对接外部平台，注释需要说明现网配置、回调和退款查询的风险边界。

        @param order: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param package: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
        """
        if data.payChannel != "wechat_virtual":
            raise HTTPException(status_code=400, detail="虚拟商品购买只能使用微信官方小程序虚拟支付")
        if data.scene != VIRTUAL_PAY_SCENE:
            raise HTTPException(status_code=400, detail="小程序虚拟商品必须使用官方小程序虚拟支付")
        if not settings.wechat_pay_enabled:
            raise HTTPException(status_code=503, detail="小程序虚拟支付未启用")
        return self._build_virtual_payment_payload(order, package, data)

    def query_virtual_order(self, order: PaymentOrder, package: SubscriptionPackage) -> dict:
        """
        query_virtual_order 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        微信支付服务对接外部平台，注释需要说明现网配置、回调和退款查询的风险边界。

        @param order: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param package: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises HTTPException, ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        extra_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
        openid = str(extra_payload.get("openId") or "")
        if not openid:
            raise HTTPException(status_code=400, detail="订单缺少 openId，无法查询微信虚拟支付订单")
        if not settings.wechat_virtual_pay_offer_id:
            raise HTTPException(status_code=500, detail="小程序虚拟支付 OfferID 未配置")

        body_payload = {
            "openid": openid,
            "order_id": order.order_no,
            "env": int(extra_payload.get("virtualPayEnv") or settings.wechat_virtual_pay_env or 0),
        }
        product_id = extra_payload.get("virtualProductId") or self._get_virtual_product_id(package)
        if product_id:
            body_payload["product_id"] = str(product_id)

        body = json.dumps(body_payload, ensure_ascii=False, separators=(",", ":"))
        response = requests.post(
            X_PAY_QUERY_ORDER_URL,
            params={
                "access_token": self._get_access_token(),
                "pay_sig": self._hmac_sha256(self._get_virtual_app_key(), f"{X_PAY_QUERY_ORDER_PATH}&{body}"),
            },
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=settings.wechat_pay_request_timeout,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"微信虚拟支付查单失败: HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信虚拟支付查单响应不是 JSON") from exc

        errcode = int(result.get("errcode") or result.get("err_code") or 0)
        if errcode:
            errmsg = result.get("errmsg") or result.get("err_msg") or "unknown error"
            raise HTTPException(status_code=502, detail=f"微信虚拟支付查单失败: {errcode} {errmsg}")
        return {
            "verified": self._virtual_order_is_paid(result),
            "transactionId": self._extract_virtual_order_id(result),
            "amountTotal": self._extract_virtual_order_amount(result),
            "paidAt": self._extract_virtual_paid_at(result),
            "raw": result,
            "request": body_payload,
        }

    def refund_virtual_order(self, order: PaymentOrder, refund_order_id: str, left_fee: int, refund_fee: int, refund_reason: str = "1", req_from: str = "1") -> dict:
        """
        refund_virtual_order 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

        微信支付服务对接外部平台，注释需要说明现网配置、回调和退款查询的风险边界。

        @param order: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param refund_order_id: 业务对象标识；用于跨接口追溯同一条记录，调用方应避免传入展示名。
        @param left_fee: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param refund_fee: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param refund_reason: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @param req_from: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
        @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
        @raises HTTPException, ValueError: 当输入、权限、外部服务或数据状态不满足业务边界时向上抛出。
        """
        extra_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
        openid = str(extra_payload.get("openId") or "")
        if not openid:
            raise HTTPException(status_code=400, detail="订单缺少 openId，无法发起退款")
        if not settings.wechat_virtual_pay_offer_id:
            raise HTTPException(status_code=500, detail="小程序虚拟支付 OfferID 未配置")

        env = int(extra_payload.get("virtualPayEnv") or settings.wechat_virtual_pay_env or 0)
        body_payload = {
            "openid": openid,
            "order_id": order.order_no,
            "refund_order_id": refund_order_id,
            "left_fee": left_fee,
            "refund_fee": refund_fee,
            "biz_meta": json.dumps({"username": order.username, "packageCode": order.package_code}, ensure_ascii=False, separators=(",", ":")),
            "refund_reason": refund_reason,
            "req_from": req_from,
            "env": env,
        }
        body = json.dumps(body_payload, ensure_ascii=False, separators=(",", ":"))
        app_key = self._get_virtual_app_key()
        pay_sig = self._hmac_sha256(app_key, f"{X_PAY_REFUND_ORDER_PATH}&{body}")
        response = requests.post(
            X_PAY_REFUND_ORDER_URL,
            params={
                "access_token": self._get_access_token(),
                "pay_sig": pay_sig,
            },
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=settings.wechat_pay_request_timeout,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"微信虚拟支付退款失败: HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信虚拟支付退款响应不是 JSON") from exc

        errcode = int(result.get("errcode") or result.get("err_code") or 0)
        if errcode:
            errmsg = result.get("errmsg") or result.get("err_msg") or "unknown error"
            raise HTTPException(status_code=502, detail=f"微信虚拟支付退款失败: {errcode} {errmsg}")
        return {
            "success": True,
            "refundOrderId": result.get("refund_order_id") or refund_order_id,
            "refundWxOrderId": result.get("refund_wx_order_id") or "",
            "payOrderId": result.get("pay_order_id") or order.order_no,
            "payWxOrderId": result.get("pay_wx_order_id") or "",
            "raw": result,
        }

    def _extract_virtual_left_fee(self, result: dict) -> int:
        candidates = [
            result.get("left_fee"),
            result.get("leftFee"),
        ]
        order_info = result.get("order") or result.get("orderInfo") or result.get("order_info")
        if isinstance(order_info, dict):
            candidates.extend([
                order_info.get("left_fee"),
                order_info.get("leftFee"),
            ])
        for value in candidates:
            if value in (None, ""):
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        amount = self._extract_virtual_order_amount(result)
        return amount if amount else 0

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

    def _get_access_token(self) -> str:
        now = int(time())
        if self._access_token and self._access_token_expires_at > now + 60:
            return self._access_token
        if not settings.wechat_pay_appid or not settings.wechat_miniprogram_app_secret:
            raise HTTPException(status_code=500, detail="小程序 AppID 或 AppSecret 未配置")
        response = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_pay_appid,
                "secret": settings.wechat_miniprogram_app_secret,
            },
            timeout=settings.wechat_pay_request_timeout,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"微信 access_token 获取失败: HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="微信 access_token 响应不是 JSON") from exc
        errcode = int(result.get("errcode") or 0)
        if errcode:
            errmsg = result.get("errmsg") or "unknown error"
            raise HTTPException(status_code=502, detail=f"微信 access_token 获取失败: {errcode} {errmsg}")
        token = result.get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="微信 access_token 响应缺少 access_token")
        self._access_token = str(token)
        self._access_token_expires_at = now + max(int(result.get("expires_in") or 7200), 300)
        return self._access_token

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

    def _virtual_order_is_paid(self, result: dict) -> bool:
        order_info = result.get("order") or result.get("orderInfo") or result.get("order_info")
        status_values = [
            result.get("trade_state"),
            result.get("tradeState"),
            result.get("status"),
            result.get("order_status"),
            result.get("orderStatus"),
            result.get("pay_status"),
            result.get("payStatus"),
        ]
        if isinstance(order_info, dict):
            status_values.extend([
                order_info.get("trade_state"),
                order_info.get("tradeState"),
                order_info.get("status"),
                order_info.get("order_status"),
                order_info.get("orderStatus"),
                order_info.get("pay_status"),
                order_info.get("payStatus"),
            ])
        paid_values = {"success", "paid", "complete", "completed", "finish", "finished", "1", "2", "3"}
        for value in status_values:
            if value is None:
                continue
            normalized = str(value).strip().lower()
            if normalized in paid_values or normalized == "success":
                return True
        if result.get("paid") is True or result.get("is_paid") is True or result.get("isPaid") is True:
            return True
        if isinstance(order_info, dict):
            try:
                return int(order_info.get("paid_fee") or 0) > 0
            except (TypeError, ValueError):
                return False
        return False

    def _extract_virtual_order_id(self, result: dict) -> str:
        candidates = [
            result.get("wxpay_order_id"),
            result.get("wxpayOrderId"),
            result.get("wx_order_id"),
            result.get("wxOrderId"),
            result.get("channel_order_id"),
            result.get("channelOrderId"),
            result.get("transaction_id"),
            result.get("transactionId"),
            result.get("wechat_order_id"),
            result.get("wechatOrderId"),
            result.get("payment_order_id"),
            result.get("paymentOrderId"),
            result.get("trade_no"),
            result.get("tradeNo"),
        ]
        order_info = result.get("order") or result.get("orderInfo") or result.get("order_info")
        if isinstance(order_info, dict):
            candidates.extend([
                order_info.get("wxpay_order_id"),
                order_info.get("wxpayOrderId"),
                order_info.get("wx_order_id"),
                order_info.get("wxOrderId"),
                order_info.get("channel_order_id"),
                order_info.get("channelOrderId"),
                order_info.get("transaction_id"),
                order_info.get("transactionId"),
                order_info.get("payment_order_id"),
                order_info.get("paymentOrderId"),
                order_info.get("order_id"),
                order_info.get("orderId"),
            ])
        for value in candidates:
            if value not in (None, ""):
                return str(value)
        return ""

    def _extract_virtual_order_amount(self, result: dict) -> int | None:
        candidates = [
            result.get("amount_total"),
            result.get("amountTotal"),
            result.get("total_fee"),
            result.get("totalFee"),
            result.get("goods_price"),
            result.get("goodsPrice"),
        ]
        amount = result.get("amount")
        if isinstance(amount, dict):
            candidates.extend([amount.get("total"), amount.get("payer_total"), amount.get("payerTotal")])
        order_info = result.get("order") or result.get("orderInfo") or result.get("order_info")
        if isinstance(order_info, dict):
            candidates.extend([
                order_info.get("paid_fee"),
                order_info.get("paidFee"),
                order_info.get("order_fee"),
                order_info.get("orderFee"),
                order_info.get("left_fee"),
                order_info.get("leftFee"),
            ])
        for value in candidates:
            if value in (None, ""):
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    def _extract_virtual_paid_at(self, result: dict) -> str:
        candidates = [
            result.get("success_time"),
            result.get("successTime"),
            result.get("paid_at"),
            result.get("paidAt"),
            result.get("pay_time"),
            result.get("payTime"),
            result.get("create_time"),
            result.get("createTime"),
        ]
        order_info = result.get("order") or result.get("orderInfo") or result.get("order_info")
        if isinstance(order_info, dict):
            candidates.extend([
                order_info.get("paid_time"),
                order_info.get("paidTime"),
                order_info.get("update_time"),
                order_info.get("updateTime"),
                order_info.get("create_time"),
                order_info.get("createTime"),
            ])
        for value in candidates:
            if value not in (None, ""):
                try:
                    numeric_value = int(value)
                    if numeric_value > 10_000_000_000:
                        numeric_value = numeric_value // 1000
                    return datetime.fromtimestamp(numeric_value, tz=timezone.utc).isoformat()
                except (TypeError, ValueError):
                    pass
                return str(value)
        return datetime.now(timezone.utc).isoformat()

wechat_pay_service = WechatPayService()
