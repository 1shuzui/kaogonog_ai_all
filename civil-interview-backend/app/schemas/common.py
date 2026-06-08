"""
这个文件放前后端共同使用的请求/响应模型；把字段集中在这里，是为了减少 PC 和小程序因为参数名不同而互相打架。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
from typing import Optional, List, Dict, Any
from pydantic import AliasChoices, BaseModel, Field


# ===== Auth =====
class Token(BaseModel):
    """
    Token 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """
    TokenData 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: Optional[str] = None

class AuthUser(BaseModel):
    """
    AuthUser 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    role: str = "user"
    isAdmin: bool = False
    permissions: Dict[str, bool] = Field(default_factory=dict)
    billing: Dict[str, Any] = Field(default_factory=dict)

class RegisterRequest(BaseModel):
    """
    RegisterRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: str
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("full_name", "fullName"))
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramLoginRequest(BaseModel):
    """
    WechatMiniProgramLoginRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    code: str
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramBindRequest(BaseModel):
    """
    WechatMiniProgramBindRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    code: str


class WechatMiniProgramAccountRequest(BaseModel):
    """
    WechatMiniProgramAccountRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: str
    password: str = Field(min_length=6)


class PasswordResetRequest(BaseModel):
    """
    PasswordResetRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: str
    contact: Optional[str] = ""


class PasswordResetVerifyRequest(BaseModel):
    """
    PasswordResetVerifyRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: str
    code: str


class PasswordResetConfirmRequest(PasswordResetVerifyRequest):
    """
    PasswordResetConfirmRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    newPassword: str = Field(min_length=6, validation_alias=AliasChoices("newPassword", "new_password"))


# ===== User =====
class UserProfileUpdate(BaseModel):
    """
    UserProfileUpdate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    province: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    """
    UserPasswordUpdate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    old_password: str = Field(validation_alias=AliasChoices("old_password", "oldPassword"))
    new_password: str = Field(min_length=6, validation_alias=AliasChoices("new_password", "newPassword"))

class UserPreferencesUpdate(BaseModel):
    """
    UserPreferencesUpdate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    defaultPrepTime: Optional[int] = None
    defaultAnswerTime: Optional[int] = None
    enableVideo: Optional[bool] = None
    enableAudio: Optional[bool] = None
    preferredQuestionDimensions: Optional[List[str]] = None
    practicePreferenceConfirmed: Optional[bool] = None
    examCategory: Optional[str] = None


class UserProvinceUpdate(BaseModel):
    """
    UserProvinceUpdate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    province: str


class UserTermsAgreementRequest(BaseModel):
    """
    UserTermsAgreementRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    version: str


class SubscriptionSwitchRequest(BaseModel):
    """
    SubscriptionSwitchRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    subscriptionId: int = Field(validation_alias=AliasChoices("subscriptionId", "subscription_id"))


# ===== Question =====
class QuestionCreate(BaseModel):
    """
    QuestionCreate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    stem: str
    dimension: str = "analysis"
    province: str = "national"
    prepTime: int = 90
    answerTime: int = 180
    scoringPoints: List[Dict] = []
    keywords: Dict = Field(default_factory=lambda: {"scoring": [], "deducting": [], "bonus": []})
    suiteId: Optional[str] = None
    suiteKey: Optional[str] = None
    suiteName: Optional[str] = None
    examDate: Optional[str] = None
    batch: Optional[str] = None
    position: Optional[str] = None
    questionNo: Optional[int] = None
    questionScore: Optional[float] = None
    answerScoreTotal: Optional[float] = None
    appearanceScore: Optional[float] = None
    suiteTotalScore: Optional[float] = None
    totalScore: Optional[float] = None
    hasAppearanceScore: Optional[bool] = None
    examCategory: Optional[str] = None
    examSubcategory: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory2: Optional[str] = None
    interviewFormat: Optional[str] = None
    questionTypeCategory: Optional[str] = None
    jobLevel: Optional[str] = None
    year: Optional[List[str]] = None
    timingMode: Optional[str] = None
    questionCount: Optional[int | str] = None
    classificationConfidence: Optional[str] = None
    reviewStatus: Optional[str] = None
    reviewReason: Optional[str] = None

class QuestionUpdate(QuestionCreate):
    """
    QuestionUpdate 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    pass


# ===== Exam =====
class ExamStartRequest(BaseModel):
    """
    ExamStartRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    questionIds: List[str]


class UsageReportRequest(BaseModel):
    """
    UsageReportRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    examId: str = Field(validation_alias=AliasChoices("examId", "exam_id"))
    questionId: Optional[str] = Field(default=None, validation_alias=AliasChoices("questionId", "question_id"))
    usageSeconds: int = Field(ge=0, validation_alias=AliasChoices("usageSeconds", "usage_seconds"))
    usageType: str = Field(default="practice", validation_alias=AliasChoices("usageType", "usage_type"))


# ===== Payment =====
class PaymentOrderCreateRequest(BaseModel):
    """
    PaymentOrderCreateRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    packageCode: str = Field(validation_alias=AliasChoices("packageCode", "package_code"))
    payChannel: str = Field(default="wechat_virtual", validation_alias=AliasChoices("payChannel", "pay_channel"))
    appId: Optional[str] = Field(default=None, validation_alias=AliasChoices("appId", "app_id"))
    code: Optional[str] = None
    openId: Optional[str] = Field(default=None, validation_alias=AliasChoices("openId", "open_id"))
    clientIp: Optional[str] = Field(default=None, validation_alias=AliasChoices("clientIp", "client_ip"))
    idempotencyKey: Optional[str] = Field(default=None, validation_alias=AliasChoices("idempotencyKey", "idempotency_key"))
    scene: str = Field(default="mini_program_virtual")


class PaymentVirtualConfirmRequest(BaseModel):
    """
    PaymentVirtualConfirmRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    scene: str = Field(default="mini_program_virtual")
    payResult: str = Field(default="success", validation_alias=AliasChoices("payResult", "pay_result"))
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    outTradeNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("outTradeNo", "out_trade_no"))
    rawResult: Dict = Field(default_factory=dict, validation_alias=AliasChoices("rawResult", "raw_result"))


class RefundBalanceStatsRequest(BaseModel):
    """
    RefundBalanceStatsRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    username: Optional[str] = None
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))


class RefundApplyRequest(BaseModel):
    """
    RefundApplyRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    orderNo: str = Field(validation_alias=AliasChoices("orderNo", "order_no"))
    refundedHours: Optional[float] = Field(default=None, ge=0, validation_alias=AliasChoices("refundedHours", "refunded_hours"))
    refundReason: Optional[str] = Field(default="", validation_alias=AliasChoices("refundReason", "refund_reason"))
    refundRemark: Optional[str] = Field(default="", validation_alias=AliasChoices("refundRemark", "refund_remark"))


# ===== Support =====
class SupportFeedbackCreateRequest(BaseModel):
    """
    SupportFeedbackCreateRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    type: str = "其他建议"
    questionId: Optional[str] = Field(default="", validation_alias=AliasChoices("questionId", "question_id"))
    summary: str = Field(min_length=1, max_length=5000)
    contact: Optional[str] = None
    routePath: Optional[str] = Field(default="", validation_alias=AliasChoices("routePath", "route_path"))
    province: Optional[str] = ""
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class SupportFeedbackUpdateRequest(BaseModel):
    """
    SupportFeedbackUpdateRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    status: Optional[str] = None
    adminNote: Optional[str] = Field(default=None, validation_alias=AliasChoices("adminNote", "admin_note"))


# ===== Scoring =====
class EvaluateRequest(BaseModel):
    """
    EvaluateRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    questionId: str
    transcript: str = Field(max_length=5000)
    examId: Optional[str] = None


# ===== Targeted =====
class FocusAnalysisRequest(BaseModel):
    """
    FocusAnalysisRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    province: str = "national"
    position: str = ""
    examCategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examCategory", "exam_category"))
    examSubcategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examSubcategory", "exam_subcategory"))
    subcategory: Optional[str] = ""
    subcategory2: Optional[str] = ""
    year: Optional[str | List[str]] = ""
    targetCode: Optional[str] = Field(default="", validation_alias=AliasChoices("targetCode", "target_code"))
    targetName: Optional[str] = Field(default="", validation_alias=AliasChoices("targetName", "target_name"))
    interviewFormat: Optional[str] = Field(default="", validation_alias=AliasChoices("interviewFormat", "interview_format"))
    timingMode: Optional[str] = Field(default="", validation_alias=AliasChoices("timingMode", "timing_mode"))
    questionCount: Optional[str | int] = Field(default="", validation_alias=AliasChoices("questionCount", "question_count"))
    prepTime: Optional[int] = Field(default=None, validation_alias=AliasChoices("prepTime", "prep_time"))
    answerTime: Optional[int] = Field(default=None, validation_alias=AliasChoices("answerTime", "answer_time"))

class GenerateQuestionsRequest(BaseModel):
    """
    GenerateQuestionsRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    province: str = "national"
    position: str = ""
    count: int = 5
    sourceMode: str = "local"
    examCategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examCategory", "exam_category"))
    examSubcategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examSubcategory", "exam_subcategory"))
    subcategory: Optional[str] = ""
    subcategory2: Optional[str] = ""
    year: Optional[str | List[str]] = ""
    targetCode: Optional[str] = Field(default="", validation_alias=AliasChoices("targetCode", "target_code"))
    targetName: Optional[str] = Field(default="", validation_alias=AliasChoices("targetName", "target_name"))
    interviewFormat: Optional[str] = Field(default="", validation_alias=AliasChoices("interviewFormat", "interview_format"))
    timingMode: Optional[str] = Field(default="", validation_alias=AliasChoices("timingMode", "timing_mode"))
    questionCount: Optional[str | int] = Field(default="", validation_alias=AliasChoices("questionCount", "question_count"))
    prepTime: Optional[int] = Field(default=None, validation_alias=AliasChoices("prepTime", "prep_time"))
    answerTime: Optional[int] = Field(default=None, validation_alias=AliasChoices("answerTime", "answer_time"))

class TrainingGenerateRequest(BaseModel):
    """
    TrainingGenerateRequest 请求/响应模型固定端侧契约，集中定义可避免 PC 与小程序各自猜测字段含义。

    Schema 层固定端侧契约，注释用于说明字段兼容和错误边界，避免页面直接猜测后端结构。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    dimension: str
    count: int = 3
    sourceMode: str = "local"
    province: Optional[str] = "national"
    examCategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examCategory", "exam_category"))
    examSubcategory: Optional[str] = Field(default="", validation_alias=AliasChoices("examSubcategory", "exam_subcategory"))
    subcategory: Optional[str] = ""
    subcategory2: Optional[str] = ""
    year: Optional[str | List[str]] = ""
