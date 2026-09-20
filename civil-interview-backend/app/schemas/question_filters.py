"""题库级联筛选元数据的只读响应契约。"""

from pydantic import BaseModel, Field


class QuestionFilterOptions(BaseModel):
    year: list[str]
    subcategory: list[str]
    subcategory2: list[str]


class QuestionFilterOptionsResponse(BaseModel):
    options: QuestionFilterOptions
    unclassifiedYearCount: int = Field(ge=0)
    questionCount: int = Field(ge=0)
