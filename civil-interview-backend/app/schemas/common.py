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
    agreed_terms_version: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("agreed_terms_version", "agreedTermsVersion"),
    )


class WechatMiniLoginRequest(BaseModel):
    code: str
    agreed_terms_version: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("agreed_terms_version", "agreedTermsVersion"),
    )


class WechatWebLoginConfigResponse(BaseModel):
    configured: bool
    loginUrl: str = ""
    message: str = ""
    requiredEnv: List[str] = Field(default_factory=list)


class PasswordResetRequest(BaseModel):
    username: str
    contact: Optional[str] = None


class PasswordResetVerifyRequest(BaseModel):
    username: str
    code: str


class PasswordResetConfirmRequest(BaseModel):
    username: str
    code: str
    new_password: str = Field(min_length=6, validation_alias=AliasChoices("new_password", "newPassword"))


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


class UserProvinceUpdate(BaseModel):
    province: str


class UserTermsAgreementRequest(BaseModel):
    version: str


class SupportFeedbackCreateRequest(BaseModel):
    type: str
    questionId: Optional[str] = Field(default="", validation_alias=AliasChoices("questionId", "question_id"))
    summary: str
    contact: Optional[str] = ""
    routePath: Optional[str] = Field(default="", validation_alias=AliasChoices("routePath", "route_path"))
    province: Optional[str] = ""


class SupportFeedbackUpdateRequest(BaseModel):
    status: Optional[str] = None
    adminNote: Optional[str] = Field(default="", validation_alias=AliasChoices("adminNote", "admin_note"))


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
    openId: Optional[str] = Field(default=None, validation_alias=AliasChoices("openId", "open_id"))
    code: Optional[str] = None
    appId: Optional[str] = Field(default=None, validation_alias=AliasChoices("appId", "app_id", "appid"))
    clientIp: Optional[str] = Field(default=None, validation_alias=AliasChoices("clientIp", "client_ip"))
    idempotencyKey: Optional[str] = Field(default=None, validation_alias=AliasChoices("idempotencyKey", "idempotency_key"))
    scene: str = Field(default="mini_program")


class PaymentCallbackRequest(BaseModel):
    mode: Optional[str] = None
    eventType: Optional[str] = Field(default=None, validation_alias=AliasChoices("eventType", "event_type"))
    resource: Optional[Dict] = None
    summary: Optional[str] = None
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))
    status: str = "paid"
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    amountTotal: Optional[int] = Field(default=None, validation_alias=AliasChoices("amountTotal", "amount_total"))
    callbackPayload: Dict = Field(default_factory=dict, validation_alias=AliasChoices("callbackPayload", "callback_payload"))


class PaymentRefundStatsRequest(BaseModel):
    username: Optional[str] = None
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))


class PaymentRefundApplyRequest(BaseModel):
    orderNo: str = Field(validation_alias=AliasChoices("orderNo", "order_no"))
    refundedHours: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("refundedHours", "refunded_hours"))
    refundRemark: Optional[str] = Field(default=None, validation_alias=AliasChoices("refundRemark", "refund_remark"))
    refundReason: Optional[str] = Field(default=None, validation_alias=AliasChoices("refundReason", "refund_reason"))


# ===== Scoring =====
class EvaluateRequest(BaseModel):
    questionId: str
    transcript: str = Field(max_length=5000)
    examId: Optional[str] = None


# ===== Targeted =====
class FocusAnalysisRequest(BaseModel):
    province: str = "national"
    position: str = "general"

class GenerateQuestionsRequest(BaseModel):
    province: str = "national"
    position: str = "general"
    count: int = 5
    sourceMode: str = "local"

class TrainingGenerateRequest(BaseModel):
    dimension: str
    count: int = 3
    sourceMode: str = "local"
