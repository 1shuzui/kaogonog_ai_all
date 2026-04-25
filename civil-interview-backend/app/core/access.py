from __future__ import annotations

from time import time

from fastapi import HTTPException, status

ADMIN_USERNAME = "admin"
TRIAL_QUESTION_ID = "q001"
BILLING_PLAN_TRIAL = "trial"
BILLING_PLAN_HOURLY = "hourly"
BILLING_PLAN_MONTHLY = "monthly"
VALID_BILLING_PLANS = {
    BILLING_PLAN_TRIAL,
    BILLING_PLAN_HOURLY,
    BILLING_PLAN_MONTHLY,
}


def normalize_billing_state(raw_state: dict | None = None) -> dict:
    raw_state = raw_state if isinstance(raw_state, dict) else {}
    plan_type = str(raw_state.get("planType") or BILLING_PLAN_TRIAL)
    if plan_type not in VALID_BILLING_PLANS:
        plan_type = BILLING_PLAN_TRIAL

    order_history = []
    if isinstance(raw_state.get("orderHistory"), list):
        for order in raw_state["orderHistory"][:20]:
            if not isinstance(order, dict):
                continue
            order_history.append(
                {
                    "id": str(order.get("id") or ""),
                    "planType": str(order.get("planType") or ""),
                    "title": str(order.get("title") or ""),
                    "amount": max(0, int(float(order.get("amount") or 0))),
                    "status": str(order.get("status") or "paid"),
                    "summary": str(order.get("summary") or ""),
                    "createdAt": max(0, int(float(order.get("createdAt") or 0))),
                }
            )

    return {
        "planType": plan_type,
        "remainingSeconds": max(0, int(float(raw_state.get("remainingSeconds") or 0))),
        "monthlyExpireAt": max(0, int(float(raw_state.get("monthlyExpireAt") or 0))),
        "activatedAt": max(0, int(float(raw_state.get("activatedAt") or 0))),
        "orderHistory": order_history,
    }


def is_admin_username(username: str | None) -> bool:
    return str(username or "").strip().lower() == ADMIN_USERNAME


def has_paid_access_from_billing(billing_state: dict | None, now_ms: int | None = None) -> bool:
    state = normalize_billing_state(billing_state)
    current_ms = int(now_ms if now_ms is not None else time() * 1000)

    if state["planType"] == BILLING_PLAN_MONTHLY:
        return state["monthlyExpireAt"] > current_ms
    if state["planType"] == BILLING_PLAN_HOURLY:
        return state["remainingSeconds"] > 0
    return False


def build_access_context(user) -> dict:
    preferences = user.preferences if isinstance(getattr(user, "preferences", None), dict) else {}
    billing_state = normalize_billing_state(preferences.get("billing"))
    is_admin = is_admin_username(getattr(user, "username", ""))
    is_paid = is_admin or has_paid_access_from_billing(billing_state)

    return {
        "role": "admin" if is_admin else "user",
        "isAdmin": is_admin,
        "billing": {
            **billing_state,
            "isPaid": is_paid,
        },
        "permissions": {
            "canManageQuestionBank": is_admin,
            "canAccessPremiumModules": is_paid,
        },
    }


def ensure_admin_access(current_user) -> None:
    if getattr(current_user, "isAdmin", False):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="仅管理员可使用题库管理功能",
    )


def ensure_paid_access(current_user, detail: str = "当前功能需付费开通后使用") -> None:
    if getattr(current_user, "isAdmin", False):
        return
    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_question_read_access(current_user, question_id: str) -> None:
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    if str(question_id or "").strip() == TRIAL_QUESTION_ID:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅可查看指定试用题，开通后可使用完整题目",
    )


def ensure_exam_start_access(current_user, question_ids: list[str] | None) -> None:
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    normalized_ids = [str(question_id or "").strip() for question_id in (question_ids or []) if str(question_id or "").strip()]
    if normalized_ids == [TRIAL_QUESTION_ID]:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅可体验指定试用题，开通后可使用完整模考功能",
    )


def ensure_random_question_access(current_user, count: int) -> None:
    if getattr(current_user, "isAdmin", False):
        return

    permissions = getattr(current_user, "permissions", {}) or {}
    if permissions.get("canAccessPremiumModules"):
        return

    if int(count or 0) <= 1:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="试用版仅支持单题体验，开通后可抽取完整模考试题",
    )
