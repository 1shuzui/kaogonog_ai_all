"""
这个文件记录答题用时和扣减分钟数；把扣量留在服务端，是为了避免小程序端时间上报异常导致权益被绕过。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    report_usage 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
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
