"""
这个文件处理试用版资格和完成状态；试用题也要求登录，是为了防止同一用户反复领取免费权益。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Question, User, UserSubscription
from app.schemas.common import AuthUser

from app.services.user_service import get_user_or_404


DEFAULT_TRIAL_TOTAL_MINUTES = 180


def _question_meta(question: Question) -> dict:
    keywords = question.keywords if isinstance(question.keywords, dict) else {}
    meta = keywords.get("_meta")
    return meta if isinstance(meta, dict) else {}


TRIAL_QUESTION_ID = "q001"


def _pick_trial_question(db: Session) -> Question | None:
    trial = db.query(Question).filter(Question.id == TRIAL_QUESTION_ID).first()
    if trial:
        return trial
    questions = db.query(Question).all()
    tagged = []
    for question in questions:
        meta = _question_meta(question)
        tags = meta.get("tags", []) if isinstance(meta.get("tags"), list) else []
        source = meta.get("source", "")
        if "trial" in tags or source == "trial":
            tagged.append(question)
    if tagged:
        tagged.sort(key=lambda item: item.id)
        return tagged[0]
    return db.query(Question).order_by(Question.created_at.asc(), Question.id.asc()).first()


def _get_or_create_trial_subscription(db: Session, username: str) -> UserSubscription:
    subscription = db.query(UserSubscription).filter(
        UserSubscription.username == username,
    ).order_by(UserSubscription.created_at.desc(), UserSubscription.id.desc()).first()
    if subscription:
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


def _sync_preferences_trial(user: User, subscription: UserSubscription):
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    prefs["subscription"] = {
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": int(subscription.total_minutes or 0),
        "usedMinutes": int(subscription.used_minutes or 0),
        "dailyLimitMinutes": int(subscription.daily_limit_minutes or 0),
        "dailyUsedMinutes": int(subscription.daily_used_minutes or 0),
        "expiresAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "packageCode": subscription.package_code,
    }
    user.preferences = prefs


def get_trial_status(db: Session, current_user: AuthUser) -> dict:
    """
    get_trial_status 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, current_user.username)
    subscription = _get_or_create_trial_subscription(db, user.username)
    trial_completed = bool(subscription.trial_completed)
    trial_question = _pick_trial_question(db)
    _sync_preferences_trial(user, subscription)
    db.commit()
    return {
        "isNewUser": not trial_completed,
        "isTrialUser": bool(subscription.is_trial),
        "shouldStartTrial": not trial_completed and trial_question is not None,
        "trialCompleted": trial_completed,
        "trialQuestionId": trial_question.id if trial_question else "",
    }


def get_trial_question(db: Session, current_user: AuthUser) -> dict:
    """
    get_trial_question 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    get_user_or_404(db, current_user.username)
    question = _pick_trial_question(db)
    if not question:
        return {}
    return {
        "id": question.id,
        "stem": question.stem,
        "dimension": question.dimension,
        "province": question.province,
        "prepTime": question.prep_time,
        "answerTime": question.answer_time,
        "scoringPoints": question.scoring_points or [],
    }


def complete_trial(db: Session, current_user: AuthUser) -> dict:
    """
    complete_trial 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    服务层承载核心业务规则，注释聚焦为什么在后端兜底而不是交给 PC 或小程序端。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param current_user: 已通过鉴权解析出的当前用户；用于把权限判断固定在服务端可信身份上。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    user = get_user_or_404(db, current_user.username)
    subscription = _get_or_create_trial_subscription(db, user.username)
    subscription.is_trial = True
    subscription.trial_completed = True
    subscription.plan_type = subscription.plan_type or "trial"
    subscription.plan_name = subscription.plan_name or "试用版"
    subscription.status = subscription.status or "active"
    if not subscription.total_minutes:
        subscription.total_minutes = DEFAULT_TRIAL_TOTAL_MINUTES
    if not subscription.daily_limit_minutes:
        subscription.daily_limit_minutes = DEFAULT_TRIAL_TOTAL_MINUTES
    if not subscription.last_reset_date:
        subscription.last_reset_date = date.today()

    _sync_preferences_trial(user, subscription)
    db.commit()
    return {
        "success": True,
        "trialCompleted": True,
        "message": "试用体验已完成",
    }
