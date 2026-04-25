"""Database models"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class User(Base):
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment_orders = relationship("PaymentOrder", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
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
    __tablename__ = "exam_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=False)
    transcript = Column(Text, default="")
    media_record = Column(JSON, default=dict)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exam = relationship("Exam", back_populates="answers")


class HistoryRecord(Base):
    __tablename__ = "history_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=False, index=True)
    question_count = Column(Integer, default=0)
    province = Column(String(32), default="national")
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SubscriptionPackage(Base):
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
    __tablename__ = "payment_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    package_code = Column(String(100), nullable=False, index=True)
    package_type = Column(String(30), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    pay_channel = Column(String(30), nullable=False, default="wechat")
    status = Column(String(30), nullable=False, default="pending", index=True)
    third_party_order_no = Column(String(100), default="")
    paid_at = Column(DateTime, nullable=True)
    callback_payload = Column(JSON, default=dict)
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payment_orders")


class UserSubscription(Base):
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
