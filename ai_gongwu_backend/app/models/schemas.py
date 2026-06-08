"""
这个文件定义旧后端的请求和响应结构；它让评分、题库和媒体接口在迁移期间仍有固定数据形状。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionDimension(BaseModel):
    """
    QuestionDimension 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    name: str
    score: float = Field(..., ge=0)


class ScoreBand(BaseModel):
    """
    ScoreBand 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    label: str
    min_score: float = Field(..., ge=0)
    max_score: float = Field(..., ge=0)
    description: str = ""


class RegressionCase(BaseModel):
    """
    RegressionCase 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    label: str
    sample_path: str
    expected_min: float = Field(..., ge=0)
    expected_max: float = Field(..., ge=0)
    llmExpectedMin: Optional[float] = Field(default=None, ge=0)
    llmExpectedMax: Optional[float] = Field(default=None, ge=0)
    notes: str = ""


class QuestionDefinition(BaseModel):
    """
    QuestionDefinition 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
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
    """
    MediaExtractionResult 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    # transcript 是后续内容评分的核心依据
    transcript: str

    # source 用来标记数据来源，方便日志排查与后续统计
    source: Literal["text", "audio", "video"]

    # source_filename 保留用户上传时的原始文件名，便于后续审计或排错
    source_filename: Optional[str] = None

    # duration_seconds 记录真实媒体时长，文本提交通道没有该值
    duration_seconds: Optional[float] = Field(default=None, ge=0)

    # visual_observation 只用于“表达状态”弱补充，不作为内容事实来源
    visual_observation: Optional[str] = None


class LLMGenerationResult(BaseModel):
    """
    LLMGenerationResult 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    raw_content: str = ""
    parsed_payload: Dict[str, Any] = Field(default_factory=dict)


class ViolationCheckPayload(BaseModel):
    """
    ViolationCheckPayload 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    model_config = ConfigDict(extra="ignore")

    is_violation: bool = False
    category: str = ""
    matched_terms: List[str] = Field(default_factory=list)
    reason: str = ""


class EvidenceItem(BaseModel):
    """
    EvidenceItem 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    id: str
    dimension_hint: str = ""
    claim: str
    evidence_text: str
    evidence_type: Literal["quote", "absence"] = "quote"
    stance: Literal["positive", "negative", "language", "neutral"] = "neutral"


class EvidenceExtractionPayload(BaseModel):
    """
    EvidenceExtractionPayload 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    model_config = ConfigDict(extra="ignore")

    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    coverage_notes: List[str] = Field(default_factory=list)
    summary: str = ""


class ReasonedScoreItem(BaseModel):
    """
    ReasonedScoreItem 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    model_config = ConfigDict(extra="ignore")

    reason: str
    dimension: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_texts: List[str] = Field(default_factory=list)


class StageTwoScoringPayload(BaseModel):
    """
    StageTwoScoringPayload 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    model_config = ConfigDict(extra="ignore")

    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    deduction_items: List[ReasonedScoreItem] = Field(default_factory=list)
    bonus_items: List[ReasonedScoreItem] = Field(default_factory=list)
    rationale: str = ""
    total_score: float = 0.0


class LLMEvaluationPayload(BaseModel):
    """
    LLMEvaluationPayload 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
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
    """
    EvaluationResult 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    # 补充回题目与原始输入信息，方便前端展示和后续追踪
    question_id: str
    question_type: str = ""
    transcript: str
    source: Literal["text", "audio", "video"] = "text"
    source_filename: Optional[str] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0)
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

    # 语速相关字段仅在真实媒体提交时可用
    speech_rate_chars_per_minute: Optional[float] = Field(default=None, ge=0)
    speech_rate_level: Optional[str] = None
    speech_rate_advice: str = ""

    # 针对本次答案的后续改动建议
    answer_revision_suggestion: str = ""

    # validation_notes 会记录系统对模型输出做过哪些修正
    validation_notes: List[str] = Field(default_factory=list)


class EvaluationAPIResponse(BaseModel):
    """
    EvaluationAPIResponse 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    code: int = 200
    message: str = "success"
    data: EvaluationResult


class QuestionSummary(BaseModel):
    """
    QuestionSummary 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    id: str
    type: str = ""
    province: str = ""
    question: str
    full_score: float
    dimension_count: int
    score_band_count: int = 0
    regression_case_count: int = 0


class QuestionDetail(BaseModel):
    """
    QuestionDetail 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

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
    """
    EvaluationRecordSummary 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    id: int
    question_id: str
    question_type: str = ""
    source: str
    source_filename: Optional[str] = None
    total_score: float
    validation_issue_count: int = 0
    created_at: datetime


class EvaluationRecordDetail(BaseModel):
    """
    EvaluationRecordDetail 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    旧后端模型用于历史数据和迁移脚本兼容，注释说明字段保留的业务依据。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    id: int
    question_id: str
    question_type: str = ""
    source: str
    source_filename: Optional[str] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0)
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
