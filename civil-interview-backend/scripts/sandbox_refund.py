"""
虚拟支付退款沙箱脚本，用来人工核对“微信订单查询、退款、权益置失效”这一整条链路。

脚本会扫描当前数据库里的 paid 订单，并可能调用微信 XPay 接口或把无 openId 的 mock/PC 订单标记为本地退款。
运行前必须确认 `.env` 指向的是预期数据库和虚拟支付环境；它不是批量售后工具，也不应该在未知现网库上直接跑。

@param: 无；执行时读取当前数据库配置、支付配置和 paid 订单。
@return: 无直接返回；执行结果通过标准输出、订单状态和权益状态体现。
@raises ImportError: 数据库、支付服务或 ORM 模型导入失败时中断。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.entities import PaymentOrder, SubscriptionPackage, UserSubscription
from app.services.wechat_pay_service import wechat_pay_service
from datetime import datetime, timezone
import uuid


def main():
    """
    扫描已支付订单并尝试执行沙箱退款或本地清理。

    这个脚本会修改订单和权益状态，运行前必须确认数据库、微信虚拟支付环境和订单范围都是预期环境。
    没有 openId 的 PC/mock 订单不会调用微信退款，只做数据库侧清理，避免把非真实支付订单送到微信接口。

    @param: 无；读取当前数据库配置并查询 paid 订单。
    @return: 无返回值；执行结果通过 stdout 和数据库状态体现。
    @raises: 数据库连接或提交异常会沿调用栈上抛；微信查询/退款异常按单笔订单捕获并跳过。
    """
    db = SessionLocal()
    try:
        orders = db.query(PaymentOrder).filter(PaymentOrder.status == "paid").all()
        if not orders:
            print("No paid orders found in sandbox.")
            return

        print(f"Found {len(orders)} paid order(s):")
        for order in orders:
            package = db.query(SubscriptionPackage).filter(
                SubscriptionPackage.package_code == order.package_code
            ).first()
            if not package:
                print(f"  SKIP {order.order_no}: package {order.package_code} not found")
                continue

            extra = order.extra_payload if isinstance(order.extra_payload, dict) else {}
            openid = str(extra.get("openId") or "")
            scene = str(extra.get("scene") or "")

            if not openid:
                # PC-created or mock order — no real WeChat payment, just mark as refunded
                print(f"  MARK {order.order_no} ({order.username}): no openId (scene={scene}), DB-only cleanup")

                order.status = "refunded"
                callback = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
                callback["refund"] = {
                    "refundedAmount": float(order.amount or 0),
                    "refundFee": 0,
                    "refundedAt": datetime.now(timezone.utc).isoformat(),
                    "mode": "db_cleanup_no_wechat_txn",
                    "note": "PC/mock order, no real WeChat payment to refund",
                }
                order.callback_payload = callback

                sub = db.query(UserSubscription).filter(
                    UserSubscription.username == order.username,
                    UserSubscription.source_order_no == order.order_no,
                ).first()
                if sub:
                    sub.status = "refunded"
                    sub.used_minutes = int(sub.total_minutes or 0)

                db.commit()
                continue

            try:
                query_result = wechat_pay_service.query_virtual_order(order, package)
            except Exception as exc:
                print(f"  SKIP {order.order_no}: query failed — {exc}")
                continue

            left_fee = wechat_pay_service._extract_virtual_left_fee(query_result.get("raw") or {})
            if left_fee <= 0:
                print(f"  SKIP {order.order_no}: left_fee={left_fee}, nothing to refund")
                continue

            refund_order_id = f"RFND{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

            try:
                refund_result = wechat_pay_service.refund_virtual_order(
                    order=order,
                    refund_order_id=refund_order_id,
                    left_fee=left_fee,
                    refund_fee=left_fee,
                    refund_reason="3",
                    req_from="1",
                )
            except Exception as exc:
                print(f"  FAIL {order.order_no}: refund API call failed — {exc}")
                continue

            order.status = "refunded"
            callback = dict(order.callback_payload) if isinstance(order.callback_payload, dict) else {}
            callback["refund"] = {
                "refundedAmount": float(order.amount or 0),
                "refundFee": left_fee,
                "leftFee": left_fee,
                "refundOrderId": refund_order_id,
                "refundWxOrderId": refund_result.get("refundWxOrderId") or "",
                "refundedAt": datetime.now(timezone.utc).isoformat(),
                "mode": "sandbox_cleanup",
            }
            order.callback_payload = callback

            sub = db.query(UserSubscription).filter(
                UserSubscription.username == order.username,
                UserSubscription.source_order_no == order.order_no,
            ).first()
            if sub:
                sub.status = "refunded"
                sub.used_minutes = int(sub.total_minutes or 0)

            db.commit()
            print(f"  OK  {order.order_no}: refunded {left_fee} fen — refundOrderId={refund_order_id}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
