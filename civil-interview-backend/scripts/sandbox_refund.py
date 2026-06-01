"""One-shot script: refund all sandbox paid orders via WeChat virtual payment API."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.entities import PaymentOrder, SubscriptionPackage, UserSubscription
from app.services.wechat_pay_service import wechat_pay_service
from datetime import datetime, timezone
import uuid


def main():
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
