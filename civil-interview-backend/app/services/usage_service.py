"""
用量上报服务层，负责把一次练习/考试消耗的秒数折算为计费分钟并扣减当前用户权益。

端侧会提供作答时长，但真正扣量必须在服务端完成：这里会确认考试归属、选择当前可用权益、跨天重置每日限额、
写入 `usage_records`，再同步用户 preferences 里的权益快照。它不会伪造考试答案，也不会处理管理员扣减；
后台人工扣减应走权益调整服务，保证审计口径独立。

@param: 服务函数接收数据库 Session、当前用户和用量上报请求。
@return: 返回扣减后的权益状态、计费分钟和用量记录摘要。
@raises HTTPException: 用户不存在、考试不属于当前用户、权益不足或上报时长不合法时抛出 HTTP 错误。
"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, UsageRecord, User, UserSubscription
from app.schemas.common import AuthUser, UsageReportRequest
from app.services.subscription_service import _ensure_daily_reset, _latest_subscription, _sync_user_preferences_subscription
from app.services.user_service import get_user_or_404

DEFAULT_TRIAL_TOTAL_MINUTES = 180


def _ensure_default_trial_subscription(db: Session, username: str) -> UserSubscription:
    subscription = _latest_subscription(db, username)
    if subscription:
        _ensure_daily_reset(subscription)
        return subscription

    subscription = UserSubscription(
        username=username,
        package_code="trial_3h",
        plan_type="trial",
        plan_name="试用版",
        status="active",
        is_trial=True,
        trial_completed=False,
        total_minutes=DEFAULT_TRIAL_TOTAL_MINUTES,
        used_minutes=0,
        daily_limit_minutes=DEFAULT_TRIAL_TOTAL_MINUTES,
        daily_used_minutes=0,
        last_reset_date=date.today(),
        extra_payload={"autoCreated": True},
    )
    db.add(subscription)
    db.flush()
    return subscription


def report_usage(db: Session, current_user: AuthUser, data: UsageReportRequest) -> dict:
    """
    上报一次答题用量并扣减当前权益。

    端侧上报的是秒数，服务端按向上取整折算分钟，并同时更新总用量和每日用量。这里会校验考试归属，
    防止用户用别人的 examId 消耗或写入自己的权益记录。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 用量上报请求，包含 examId、questionId、usageSeconds 和 usageType。
    @return: 扣减结果、计费分钟、剩余权益和 usageRecordId。
    @raises HTTPException: 用户不存在、考试不存在/不属于当前用户或用量参数非法时抛出。
    """
    user = get_user_or_404(db, current_user.username)
    exam = db.query(Exam).filter(Exam.id == data.examId, Exam.user_id == current_user.username).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")

    subscription = _ensure_default_trial_subscription(db, current_user.username)
    _ensure_daily_reset(subscription)

    additional_minutes = max(int((data.usageSeconds + 59) // 60), 0)
    total_minutes = int(subscription.total_minutes or 0)
    used_minutes = int(subscription.used_minutes or 0)
    daily_limit_minutes = int(subscription.daily_limit_minutes or 0)
    daily_used_minutes = int(subscription.daily_used_minutes or 0)

    remaining_minutes_before = max(total_minutes - used_minutes, 0)
    remaining_daily_quota = max(daily_limit_minutes - daily_used_minutes, 0) if daily_limit_minutes > 0 else remaining_minutes_before
    remaining_daily_before = min(remaining_minutes_before, remaining_daily_quota)
    if total_minutes <= 0 or remaining_minutes_before <= 0 or (daily_limit_minutes > 0 and remaining_daily_before <= 0):
        snapshot = _sync_user_preferences_subscription(user, subscription)
        db.commit()
        return {
            "success": False,
            "examId": data.examId,
            "questionId": data.questionId or "",
            "usageType": data.usageType,
            "usageSeconds": data.usageSeconds,
            "addedMinutes": 0,
            "usedMinutes": subscription.used_minutes,
            "dailyUsedMinutes": subscription.daily_used_minutes,
            "remainingMinutes": snapshot["remainingMinutes"],
            "remainingDailyMinutes": snapshot["remainingDailyMinutes"],
            "allowed": False,
            "reason": "当前订阅额度不足",
            "subscriptionId": int(subscription.id or 0),
            "packageCode": subscription.package_code,
        }

    billable_minutes = min(additional_minutes, remaining_minutes_before)
    if daily_limit_minutes > 0:
        billable_minutes = min(billable_minutes, remaining_daily_before)

    subscription.used_minutes = used_minutes + billable_minutes
    subscription.daily_used_minutes = daily_used_minutes + billable_minutes
    if subscription.used_minutes >= total_minutes:
        subscription.status = "inactive"

    record = UsageRecord(
        username=current_user.username,
        exam_id=data.examId,
        question_id=data.questionId,
        usage_type=data.usageType,
        usage_seconds=data.usageSeconds,
        billed_minutes=billable_minutes,
        extra_payload={"reportedMinutes": additional_minutes},
    )
    db.add(record)

    snapshot = _sync_user_preferences_subscription(user, subscription)
    db.commit()

    return {
        "success": True,
        "examId": data.examId,
        "questionId": data.questionId or "",
        "usageType": data.usageType,
        "usageSeconds": data.usageSeconds,
        "addedMinutes": billable_minutes,
        "usedMinutes": subscription.used_minutes,
        "dailyUsedMinutes": subscription.daily_used_minutes,
        "remainingMinutes": snapshot["remainingMinutes"],
        "remainingDailyMinutes": snapshot["remainingDailyMinutes"],
        "allowed": snapshot["canUse"],
        "subscriptionStatus": subscription.status,
        "subscriptionId": int(subscription.id or 0),
        "packageCode": subscription.package_code,
    }
