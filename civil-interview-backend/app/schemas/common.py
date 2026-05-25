from typing import Optional, List, Dict, Any
from pydantic import AliasChoices, BaseModel, Field


# ===== Auth =====
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class AuthUser(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    role: str = "user"
    isAdmin: bool = False
    permissions: Dict[str, bool] = Field(default_factory=dict)
    billing: Dict[str, Any] = Field(default_factory=dict)

class RegisterRequest(BaseModel):
    username: str
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("full_name", "fullName"))
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramLoginRequest(BaseModel):
    code: str
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramBindRequest(BaseModel):
    code: str


class WechatMiniProgramAccountRequest(BaseModel):
    username: str
    password: str = Field(min_length=6)


class PasswordResetRequest(BaseModel):
    username: str
    contact: Optional[str] = ""


class PasswordResetVerifyRequest(BaseModel):
    username: str
    code: str


class PasswordResetConfirmRequest(PasswordResetVerifyRequest):
    newPassword: str = Field(min_length=6, validation_alias=AliasChoices("newPassword", "new_password"))


# ===== User =====
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    province: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    old_password: str = Field(validation_alias=AliasChoices("old_password", "oldPassword"))
    new_password: str = Field(min_length=6, validation_alias=AliasChoices("new_password", "newPassword"))

class UserPreferencesUpdate(BaseModel):
    defaultPrepTime: Optional[int] = None
    defaultAnswerTime: Optional[int] = None
    enableVideo: Optional[bool] = None
    preferredQuestionDimensions: Optional[List[str]] = None
    practicePreferenceConfirmed: Optional[bool] = None


class UserProvinceUpdate(BaseModel):
    province: str


class UserTermsAgreementRequest(BaseModel):
    version: str


class SubscriptionSwitchRequest(BaseModel):
    subscriptionId: int = Field(validation_alias=AliasChoices("subscriptionId", "subscription_id"))


# ===== Question =====
class QuestionCreate(BaseModel):
    stem: str
    dimension: str = "analysis"
    province: str = "national"
    prepTime: int = 90
    answerTime: int = 180
    scoringPoints: List[Dict] = []
    keywords: Dict = Field(default_factory=lambda: {"scoring": [], "deducting": [], "bonus": []})

class QuestionUpdate(QuestionCreate):
    pass


# ===== Exam =====
class ExamStartRequest(BaseModel):
    questionIds: List[str]


class UsageReportRequest(BaseModel):
    examId: str = Field(validation_alias=AliasChoices("examId", "exam_id"))
    questionId: Optional[str] = Field(default=None, validation_alias=AliasChoices("questionId", "question_id"))
    usageSeconds: int = Field(ge=0, validation_alias=AliasChoices("usageSeconds", "usage_seconds"))
    usageType: str = Field(default="practice", validation_alias=AliasChoices("usageType", "usage_type"))


# ===== Payment =====
class PaymentOrderCreateRequest(BaseModel):
    packageCode: str = Field(validation_alias=AliasChoices("packageCode", "package_code"))
    payChannel: str = Field(default="wechat", validation_alias=AliasChoices("payChannel", "pay_channel"))
    appId: Optional[str] = Field(default=None, validation_alias=AliasChoices("appId", "app_id"))
    code: Optional[str] = None
    openId: Optional[str] = Field(default=None, validation_alias=AliasChoices("openId", "open_id"))
    clientIp: Optional[str] = Field(default=None, validation_alias=AliasChoices("clientIp", "client_ip"))
    idempotencyKey: Optional[str] = Field(default=None, validation_alias=AliasChoices("idempotencyKey", "idempotency_key"))
    scene: str = Field(default="mini_program")


class PaymentVirtualConfirmRequest(BaseModel):
    scene: str = Field(default="mini_program_virtual")
    payResult: str = Field(default="success", validation_alias=AliasChoices("payResult", "pay_result"))
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    outTradeNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("outTradeNo", "out_trade_no"))
    rawResult: Dict = Field(default_factory=dict, validation_alias=AliasChoices("rawResult", "raw_result"))


class PaymentCallbackRequest(BaseModel):
    mode: str = "wechat"
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))
    status: str = "paid"
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    amountTotal: Optional[int] = Field(default=None, validation_alias=AliasChoices("amountTotal", "amount_total"))
    callbackPayload: Dict = Field(default_factory=dict, validation_alias=AliasChoices("callbackPayload", "callback_payload"))
    resourcePlain: Optional[Dict] = Field(default=None, validation_alias=AliasChoices("resourcePlain", "resource_plain"))


class RefundBalanceStatsRequest(BaseModel):
    username: Optional[str] = None
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))


class RefundApplyRequest(BaseModel):
    orderNo: str = Field(validation_alias=AliasChoices("orderNo", "order_no"))
    refundedHours: Optional[float] = Field(default=None, ge=0, validation_alias=AliasChoices("refundedHours", "refunded_hours"))
    refundReason: Optional[str] = Field(default="", validation_alias=AliasChoices("refundReason", "refund_reason"))
    refundRemark: Optional[str] = Field(default="", validation_alias=AliasChoices("refundRemark", "refund_remark"))


# ===== Support =====
class SupportFeedbackCreateRequest(BaseModel):
    type: str = "其他建议"
    questionId: Optional[str] = Field(default="", validation_alias=AliasChoices("questionId", "question_id"))
    summary: str = Field(min_length=1, max_length=5000)
    contact: Optional[str] = None
    routePath: Optional[str] = Field(default="", validation_alias=AliasChoices("routePath", "route_path"))
    province: Optional[str] = ""
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class SupportFeedbackUpdateRequest(BaseModel):
    status: Optional[str] = None
    adminNote: Optional[str] = Field(default=None, validation_alias=AliasChoices("adminNote", "admin_note"))


# ===== Scoring =====
class EvaluateRequest(BaseModel):
    questionId: str
    transcript: str = Field(max_length=5000)
    examId: Optional[str] = None


# ===== Targeted =====
class FocusAnalysisRequest(BaseModel):
    province: str = "national"
    position: str = "general"

class TargetedFocusAdminRequest(FocusAnalysisRequest):
    pass

class TargetedFocusConfigUpdate(BaseModel):
    province: str = "national"
    position: str = "general"
    publishedResult: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("publishedResult", "published_result"))
    publishMode: str = Field(default="manual", validation_alias=AliasChoices("publishMode", "publish_mode"))
    isActive: bool = Field(default=True, validation_alias=AliasChoices("isActive", "is_active"))

class GenerateQuestionsRequest(BaseModel):
    province: str = "national"
    position: str = "general"
    count: int = 5
    sourceMode: str = "local"

class TrainingGenerateRequest(BaseModel):
    dimension: str
    count: int = 3
    sourceMode: str = "local"
