"""
这个文件定义旧后端保存评测记录的数据结构；这些字段用于回归样本和历史结果追踪。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """


class EvaluationRecord(Base):
    """
    EvaluationRecord 数据模型承载已上线数据契约，字段调整会影响接口、脚本和历史记录的兼容性。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    __tablename__ = "evaluation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
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
