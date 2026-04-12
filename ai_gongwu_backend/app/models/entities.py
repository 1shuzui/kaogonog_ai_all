"""数据库 ORM 模型。

当前先做最核心的一张表：测评记录表。
设计原则是：
1. 必要的可检索字段单独成列，方便后续查询。
2. 完整的模型原始输出和最终结果以 JSON 形式保留，方便复盘。
3. 先满足本地 SQLite 落地，后续再迁移到 MySQL/PostgreSQL。
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


class EvaluationRecord(Base):
    """测评记录表。

    这张表同时保存：
    - 输入侧关键信息
    - 调模型时的 Prompt
    - 模型原始输出
    - 后处理后的最终结果
    """

    __tablename__ = "evaluation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    visual_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_llm_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_llm_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    final_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    validation_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
