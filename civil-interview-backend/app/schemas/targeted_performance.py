"""Additive contracts for personal performance and fixed targeted practice."""
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import FocusAnalysisRequest

QuestionType = Literal["综合分析", "组织管理", "应急应变", "人际沟通", "情景模拟", "岗位认知"]


class PerformanceRequest(BaseModel):
    target: FocusAnalysisRequest
    period: Literal["recent30", "all"] = "recent30"


class PerformanceAnswersRequest(PerformanceRequest):
    questionType: QuestionType
    recordFilter: Literal["all", "low_score"] = "all"
    current: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)
    analysisRevision: str = ""


class TargetedPracticeRequest(PerformanceRequest):
    questionType: QuestionType
    mode: Literal["new", "low_score", "review"] = "new"
    count: Literal[1, 3, 5] = 3


class TargetedPracticeContext(TargetedPracticeRequest):
    version: Literal[1] = 1
    rulesVersion: Literal["targeted-performance-v1"] = "targeted-performance-v1"
