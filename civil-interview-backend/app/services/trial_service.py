"""
试用权益服务层，负责查询试用资格、发放试用题和标记试用完成。

微信审核要求用户能先浏览功能，但试用本身必须登录，因为它依赖用户身份记录领取状态，防止同一账号重复领取。
试用权益和付费权益都落在 `user_subscriptions`，这样练习入口可以用同一套权益判断；试用题完成后只更新试用状态，
不绕过正式用量和历史记录链路。

@param: 服务函数接收数据库 Session 和当前用户。
@return: 返回试用状态、试用题或试用完成结果。
@raises HTTPException: 用户不存在、试用已完成、题库没有可用试用题或权益状态异常时抛出 HTTP 错误。
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
    计算当前用户是否还可以使用试用题。

    试用状态既要看是否已完成，也要兼容自动创建的试用订阅；集中在服务层可以避免首页、套餐页和训练入口判断不一致。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @return: 试用可用状态、完成状态和剩余提示。
    @raises HTTPException: 当前用户不存在时抛出。
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
    返回当前用户可领取的试用题。

    试用题不是公开题库浏览，必须登录后领取，便于记录一次性试用状态并防止重复消耗。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @return: 试用题详情和试用状态。
    @raises HTTPException: 用户不存在、已完成试用或题目不可用时抛出。
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
    标记当前用户试用流程完成。

    完成后不删除试用记录，而是写完成标记，方便后续客服核查和端侧展示“已体验”。

    @param db: 请求级数据库会话。
    @param current_user: 当前登录用户。
    @param data: 试用完成请求。
    @return: 更新后的试用状态。
    @raises HTTPException: 用户不存在或试用状态不合法时抛出。
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
