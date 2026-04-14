"""Database models"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
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


class ExamAnswer(Base):
    __tablename__ = "exam_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=False)
    transcript = Column(Text, default="")
    score_result = Column(JSON, default=dict)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exam = relationship("Exam", back_populates="answers")


class HistoryRecord(Base):
    __tablename__ = "history_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=False, index=True)
    question_count = Column(Integer, default=0)
    total_score = Column(Float, default=0)
    max_score = Column(Float, default=100)
    grade = Column(String(4), default="B")
    province = Column(String(32), default="national")
    dimensions = Column(JSON, default=list)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
