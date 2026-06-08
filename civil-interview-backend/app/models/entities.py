"""
这个文件定义线上 MySQL 的核心表：用户、题目、考试、订单、权益和反馈；这里的字段名字会被接口、脚本和旧数据一起依赖，改动要格外保守。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_id(prefix=""):
    """
    gen_id 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param prefix: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class User(Base):
    """
    User 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(64), default="")
    email = Column(String(128), default="")
    avatar = Column(String(256), default="")
    province = Column(String(32), default="national")
    disabled = Column(Boolean, default=False)
    preferences = Column(JSON, default=dict)
    agreed_terms_version = Column(String(20), default="")
    agreed_terms_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)
    last_login_device = Column(String(200), default="")
    login_device_history = Column(JSON, default=list)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment_orders = relationship("PaymentOrder", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    """
    Question 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "questions"
    __table_args__ = (
        Index("idx_questions_province_dimension", "province", "dimension"),
        Index("idx_questions_dimension_province", "dimension", "province"),
    )
    id = Column(String(32), primary_key=True, default=lambda: gen_id("q_"))
    stem = Column(Text, nullable=False)
    dimension = Column(String(32), default="analysis")
    province = Column(String(32), default="national")
    prep_time = Column(Integer, default=90)
    answer_time = Column(Integer, default=180)
    scoring_points = Column(JSON, default=list)
    keywords = Column(JSON, default=lambda: {"scoring": [], "deducting": [], "bonus": []})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Exam(Base):
    """
    Exam 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "exams"
    id = Column(String(32), primary_key=True, default=lambda: gen_id("exam_"))
    user_id = Column(String(64), nullable=False, index=True)
    question_ids = Column(JSON, default=list)
    status = Column(String(16), default="in_progress")
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    answers = relationship("ExamAnswer", back_populates="exam", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="exam", cascade="all, delete-orphan")


class ExamAnswer(Base):
    """
    ExamAnswer 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "exam_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=False)
    transcript = Column(Text, default="")
    score_result = Column(JSON, default=dict)
    media_record = Column(JSON, default=dict)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exam = relationship("Exam", back_populates="answers")


class HistoryRecord(Base):
    """
    HistoryRecord 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "history_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=False, index=True)
    question_count = Column(Integer, default=0)
    total_score = Column(Float, default=0)
    max_score = Column(Float, default=100)
    grade = Column(String(4), default="B")
    dimensions = Column(JSON, default=list)
    province = Column(String(32), default="national")
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SubscriptionPackage(Base):
    """
    SubscriptionPackage 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "subscription_packages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    package_code = Column(String(100), unique=True, nullable=False, index=True)
    package_name = Column(String(100), nullable=False)
    package_type = Column(String(30), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    total_minutes = Column(Integer, nullable=False, default=0)
    daily_limit_minutes = Column(Integer, nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), default="")
    extra_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PaymentOrder(Base):
    """
    PaymentOrder 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "payment_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    package_code = Column(String(100), nullable=False, index=True)
    package_type = Column(String(30), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    pay_channel = Column(String(30), nullable=False, default="wechat_virtual")
    status = Column(String(30), nullable=False, default="pending", index=True)
    third_party_order_no = Column(String(100), default="")
    paid_at = Column(DateTime, nullable=True)
    callback_payload = Column(JSON, default=dict)
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payment_orders")


class SupportFeedback(Base):
    """
    SupportFeedback 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "support_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, index=True)
    feedback_type = Column(String(64), nullable=False, default="其他建议", index=True)
    question_id = Column(String(64), default="")
    summary = Column(Text, nullable=False)
    contact = Column(String(255), default="")
    route_path = Column(String(255), default="")
    province = Column(String(64), default="", index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    admin_note = Column(Text, default="")
    handled_by = Column(String(64), default="")
    handled_at = Column(DateTime, nullable=True)
    attachments = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TargetedFocusConfig(Base):
    """
    TargetedFocusConfig 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "targeted_focus_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_key = Column(String(255), unique=True, nullable=False, index=True)
    target_code = Column(String(100), default="", index=True)
    target_name = Column(String(255), default="")
    province = Column(String(64), default="", index=True)
    position = Column(String(64), default="", index=True)
    payload = Column(JSON, default=dict)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    updated_by = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserSubscription(Base):
    """
    UserSubscription 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "user_subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    package_code = Column(String(100), nullable=False, index=True)
    plan_type = Column(String(30), nullable=False, index=True)
    plan_name = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="active", index=True)
    is_trial = Column(Boolean, nullable=False, default=False)
    trial_completed = Column(Boolean, nullable=False, default=False)
    total_minutes = Column(Integer, nullable=False, default=0)
    used_minutes = Column(Integer, nullable=False, default=0)
    daily_limit_minutes = Column(Integer, nullable=False, default=0)
    daily_used_minutes = Column(Integer, nullable=False, default=0)
    last_reset_date = Column(Date, nullable=True)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    source_order_no = Column(String(100), default="")
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscriptions")


class UsageRecord(Base):
    """
    UsageRecord 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    数据模型需要兼容已经上线的 MySQL 数据和多端接口，注释重点说明字段存在的业务原因。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    __tablename__ = "usage_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=True)
    usage_type = Column(String(30), nullable=False, default="practice", index=True)
    usage_seconds = Column(Integer, nullable=False, default=0)
    billed_minutes = Column(Integer, nullable=False, default=0)
    reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="usage_records")
    exam = relationship("Exam", back_populates="usage_records")
