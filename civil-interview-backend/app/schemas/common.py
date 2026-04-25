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
    clientIp: Optional[str] = Field(default=None, validation_alias=AliasChoices("clientIp", "client_ip"))
    scene: str = Field(default="mini_program")


class PaymentCallbackRequest(BaseModel):
    mode: str = "mock"
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))
    status: str = "paid"
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    amountTotal: Optional[int] = Field(default=None, validation_alias=AliasChoices("amountTotal", "amount_total"))
    callbackPayload: Dict = Field(default_factory=dict, validation_alias=AliasChoices("callbackPayload", "callback_payload"))
    resourcePlain: Optional[Dict] = Field(default=None, validation_alias=AliasChoices("resourcePlain", "resource_plain"))


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
