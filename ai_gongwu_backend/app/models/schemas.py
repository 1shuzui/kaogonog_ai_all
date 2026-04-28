"""数据模型定义。

这一层的作用可以理解为“数据合同”：
1. 题库长什么样
2. LLM 返回结果长什么样
3. API 最终响应长什么样
都在这里被显式定义出来。

这样做的好处是：
- 少写很多 if/else 防御代码
- 数据一旦不符合结构，能更早发现问题
- 对弱基础同学来说，读这里能快速理解系统到底在传什么数据
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionDimension(BaseModel):
    """题目中的单个评分维度。

    例如：
    - 现象解读：8 分
    - 创新思维：2 分
    """

    name: str
    score: float = Field(..., ge=0)


class ScoreBand(BaseModel):
    """题目分档配置。

    用于把连续分数映射成更容易理解的档位，
    例如“低分 / 中档 / 通用高分 / 河南省直高分”。
    """

    label: str
    min_score: float = Field(..., ge=0)
    max_score: float = Field(..., ge=0)
    description: str = ""


class RegressionCase(BaseModel):
    """题目的回归测试样本配置。"""

    label: str
    sample_path: str
    expected_min: float = Field(..., ge=0)
    expected_max: float = Field(..., ge=0)
    llmExpectedMin: Optional[float] = Field(default=None, ge=0)
    llmExpectedMax: Optional[float] = Field(default=None, ge=0)
    notes: str = ""


class QuestionDefinition(BaseModel):
    """题库中一整道题的结构。

    这里基本对应 question.json 里的字段。
    model_config = ConfigDict(extra="ignore") 表示：
    即使 JSON 多出一些未声明字段，也不会直接报错。
    对接外部数据时会更宽容。
    """

    model_config = ConfigDict(extra="ignore")

    # 题目基础信息
    id: str
    type: str = ""
    province: str = ""
    fullScore: float = Field(..., ge=0)
    question: str
    dimensions: List[QuestionDimension]

    # 评分辅助词库
    coreKeywords: List[str] = Field(default_factory=list)
    strongKeywords: List[str] = Field(default_factory=list)
    weakKeywords: List[str] = Field(default_factory=list)
    bonusKeywords: List[str] = Field(default_factory=list)
    penaltyKeywords: List[str] = Field(default_factory=list)

    # 评分标准与扣分规则
    scoringCriteria: List[str] = Field(default_factory=list)
    deductionRules: List[str] = Field(default_factory=list)

    # 题库来源与高分参考答案
    sourceDocument: str = ""
    referenceAnswer: str = ""
    tags: List[str] = Field(default_factory=list)

    # 分档与批量回归辅助配置
    scoreBands: List[ScoreBand] = Field(default_factory=list)
    regressionCases: List[RegressionCase] = Field(default_factory=list)


class MediaExtractionResult(BaseModel):
    """媒体解析后的统一结果。

    不管上传的是：
    - 纯文本
    - 音频
    - 视频
    最后都会被整理成这一个结构，方便后面统一评分。
    """

    # transcript 是后续内容评分的核心依据
    transcript: str

    # source 用来标记数据来源，方便日志排查与后续统计
    source: Literal["text", "audio", "video"]

    # source_filename 保留用户上传时的原始文件名，便于后续审计或排错
    source_filename: Optional[str] = None

    # visual_observation 只用于“表达状态”弱补充，不作为内容事实来源
    visual_observation: Optional[str] = None


class LLMGenerationResult(BaseModel):
    """一次模型调用的结构化结果。

    raw_content 保留模型返回原文，
    parsed_payload 是解析后的 JSON 数据。
    """

    raw_content: str = ""
    parsed_payload: Dict[str, Any] = Field(default_factory=dict)


class ViolationCheckPayload(BaseModel):
    """违规检测阶段的结构化结果。"""

    model_config = ConfigDict(extra="ignore")

    is_violation: bool = False
    category: str = ""
    matched_terms: List[str] = Field(default_factory=list)
    reason: str = ""


class EvidenceItem(BaseModel):
    """单条评分证据。"""

    id: str
    dimension_hint: str = ""
    claim: str
    evidence_text: str
    evidence_type: Literal["quote", "absence"] = "quote"
    stance: Literal["positive", "negative", "language", "neutral"] = "neutral"


class EvidenceExtractionPayload(BaseModel):
    """第一阶段：证据抽取结果。"""

    model_config = ConfigDict(extra="ignore")

    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    coverage_notes: List[str] = Field(default_factory=list)
    summary: str = ""


class ReasonedScoreItem(BaseModel):
    """绑定证据的加分 / 扣分理由。"""

    model_config = ConfigDict(extra="ignore")

    reason: str
    dimension: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_texts: List[str] = Field(default_factory=list)


class StageTwoScoringPayload(BaseModel):
    """第二阶段：基于证据的评分结果。"""

    model_config = ConfigDict(extra="ignore")

    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    deduction_items: List[ReasonedScoreItem] = Field(default_factory=list)
    bonus_items: List[ReasonedScoreItem] = Field(default_factory=list)
    rationale: str = ""
    total_score: float = 0.0


class LLMEvaluationPayload(BaseModel):
    """大模型理论上应该返回的结构。

    注意：这是“期望结构”，并不代表模型一定老老实实遵守。
    所以后面还会有一层 post-processing 再做校验。
    """

    model_config = ConfigDict(extra="ignore")

    # 每个维度的得分
    dimension_scores: Dict[str, float] = Field(default_factory=dict)

    # 扣分说明 / 加分说明
    deduction_details: List[str] = Field(default_factory=list)
    bonus_details: List[str] = Field(default_factory=list)

    # 证据引用：要求模型尽量给出考生原文中的依据
    evidence_quotes: List[str] = Field(default_factory=list)

    # 总体评价与总分
    rationale: str = ""
    total_score: float = 0.0


class EvaluationResult(LLMEvaluationPayload):
    """系统最终返回给前端/调用方的结果。

    它是在 LLM 原始结果基础上，再经过：
    - 维度校正
    - 分数收敛
    - 引语核验
    - 关键词补充
    之后得到的“更可信版本”。
    """

    # 补充回题目与原始输入信息，方便前端展示和后续追踪
    question_id: str
    question_type: str = ""
    transcript: str
    source: Literal["text", "audio", "video"] = "text"
    source_filename: Optional[str] = None
    visual_observation: Optional[str] = None
    record_id: Optional[int] = None
    evaluated_at: Optional[datetime] = None

    # 两阶段评分后的结构化证据与理由链
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    deduction_items: List[ReasonedScoreItem] = Field(default_factory=list)
    bonus_items: List[ReasonedScoreItem] = Field(default_factory=list)

    # matched_keywords 是系统自己匹配出来的，不完全依赖模型
    matched_keywords: Dict[str, List[str]] = Field(default_factory=dict)

    # 违规检测命中后，前端可以直接据此整页拦截展示
    violation_detected: bool = False
    violation_category: str = ""
    violation_reason: str = ""
    violation_terms: List[str] = Field(default_factory=list)

    # validation_notes 会记录系统对模型输出做过哪些修正
    validation_notes: List[str] = Field(default_factory=list)


class EvaluationAPIResponse(BaseModel):
    """统一的接口响应外壳。

    这样前端接收时更稳定：
    - code 看状态
    - message 看消息
    - data 看真正业务数据
    """

    code: int = 200
    message: str = "success"
    data: EvaluationResult


class QuestionSummary(BaseModel):
    """题目摘要，用于题目列表接口。"""

    id: str
    type: str = ""
    province: str = ""
    question: str
    full_score: float
    dimension_count: int
    score_band_count: int = 0
    regression_case_count: int = 0


class QuestionDetail(BaseModel):
    """题目详情，用于前端查看完整题目配置。"""

    id: str
    type: str = ""
    province: str = ""
    full_score: float
    question: str
    dimensions: List[QuestionDimension]
    core_keywords: List[str] = Field(default_factory=list)
    strong_keywords: List[str] = Field(default_factory=list)
    weak_keywords: List[str] = Field(default_factory=list)
    bonus_keywords: List[str] = Field(default_factory=list)
    penalty_keywords: List[str] = Field(default_factory=list)
    scoring_criteria: List[str] = Field(default_factory=list)
    deduction_rules: List[str] = Field(default_factory=list)
    source_document: str = ""
    reference_answer: str = ""
    tags: List[str] = Field(default_factory=list)
    score_bands: List[ScoreBand] = Field(default_factory=list)
    regression_cases: List[RegressionCase] = Field(default_factory=list)


class EvaluationRecordSummary(BaseModel):
    """测评记录列表项。"""

    id: int
    question_id: str
    question_type: str = ""
    source: str
    source_filename: Optional[str] = None
    total_score: float
    validation_issue_count: int = 0
    created_at: datetime


class EvaluationRecordDetail(BaseModel):
    """单条测评记录详情。"""

    id: int
    question_id: str
    question_type: str = ""
    source: str
    source_filename: Optional[str] = None
    total_score: float
    transcript: str
    visual_observation: Optional[str] = None
    llm_provider: str
    llm_model_name: str
    prompt_text: str
    raw_llm_content: str = ""
    raw_llm_payload: Dict[str, Any] = Field(default_factory=dict)
    final_result: EvaluationResult
    validation_issue_count: int = 0
    created_at: datetime
