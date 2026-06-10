"""
后端公开请求/响应 Schema 集合，负责固定 PC、小程序、管理员端和脚本之间交换数据的字段形状。

这里集中放登录、题库、考试、评分、支付、权益、反馈和定向备面的 Pydantic 模型。许多字段同时兼容旧驼峰命名和新语义字段，
是为了让已发布的小程序、网页缓存和后台工具在后端升级时不断线。新增接口字段时优先在这里声明别名和默认值，
不要让页面直接猜后端 JSON 结构；涉及能力维度、题型分类、考试分类和权益口径的字段尤其要保持语义分离。

@param: 无；路由函数由 FastAPI 根据请求体、查询参数或响应模型自动实例化这些类。
@return: 暴露 Pydantic 模型，供路由、服务层和测试构造稳定的数据契约。
@raises ImportError: Pydantic 或类型依赖缺失时导入失败；字段校验错误由 FastAPI 转成 422 响应。
"""
from typing import Optional, List, Dict, Any
from pydantic import AliasChoices, BaseModel, Field


# ===== Auth =====
class Token(BaseModel):
    """
    登录成功后的令牌响应，保持 OAuth2 常见的 `access_token/token_type` 形状。

    PC 和小程序都按 bearer token 存储会话；这里不附带用户资料，是为了避免登录响应和 `/user/me`
    的权限、权益快照口径互相漂移。

    @param: 无；FastAPI/Pydantic 根据服务层返回值实例化。
    @return: 令牌响应模型。
    @raises: 字段缺失或类型不匹配时由 Pydantic 校验暴露。
    """
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """
    JWT 解析后的最小身份载荷，只保留用户名。

    权限、管理员状态和权益快照都从数据库实时读取，避免 token 长期有效时携带过期权限。

    @param: 无；安全模块根据 JWT payload 实例化。
    @return: 解析后的认证身份数据。
    @raises: 字段类型不匹配时由 Pydantic 校验暴露。
    """
    username: Optional[str] = None

class AuthUser(BaseModel):
    """
    当前登录用户的接口视图，合并账号资料、角色、权限和权益摘要。

    `isAdmin`、`permissions` 和 `billing` 保持在同一响应里，是为了让 PC 路由守卫、小程序入口和套餐中心
    不必分别请求多个接口。这里的 billing 是展示快照，不替代真实权益扣减逻辑。

    @param: 无；用户服务或认证依赖根据数据库用户组装。
    @return: 当前用户响应模型。
    @raises: 字段类型不匹配时由 Pydantic 校验暴露。
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
    PC 用户注册请求，兼容 `full_name/fullName` 和协议版本字段。

    协议版本在注册时写入，是为了满足后续审核和用户协议追溯；字段别名保留是为了旧网页表单不被后端升级打断。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 注册请求模型。
    @raises: 密码过短、字段缺失或类型错误时由 Pydantic 校验暴露。
    """
    username: str
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("full_name", "fullName"))
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramLoginRequest(BaseModel):
    """
    小程序主动登录请求，只接收微信 code 和可选协议版本。

    审核要求先浏览后登录，所以该请求只会在用户主动点击登录后出现；协议版本随登录一起提交，
    可以避免未补全 PC 账号的微信临时用户缺少同意记录。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 小程序登录请求模型。
    @raises: code 缺失或类型错误时由 Pydantic 校验暴露。
    """
    code: str
    agreedTermsVersion: Optional[str] = Field(default=None, validation_alias=AliasChoices("agreedTermsVersion", "agreed_terms_version"))


class WechatMiniProgramBindRequest(BaseModel):
    """
    已登录 PC 账号绑定小程序 openId 的请求。

    只传微信 code，openId 由后端 code2session 换取，避免前端伪造绑定目标。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 小程序绑定请求模型。
    @raises: code 缺失或类型错误时由 Pydantic 校验暴露。
    """
    code: str


class WechatMiniProgramAccountRequest(BaseModel):
    """
    小程序临时账号补全为 PC 可登录账号的请求。

    微信登录会先生成临时用户名；补全用户名和密码后，用户才能在网页端继续使用同一套权益与历史记录。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 小程序账号补全请求模型。
    @raises: 密码过短、用户名缺失或类型错误时由 Pydantic 校验暴露。
    """
    username: str
    password: str = Field(min_length=6)


class PasswordResetRequest(BaseModel):
    """
    找回密码第一步请求，记录目标账号和可选联系方式。

    当前本地和测试环境没有短信服务，服务层会生成 debug code；保留 contact 是为了未来接短信或人工客服核验。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 密码重置发起请求模型。
    @raises: 用户名缺失或类型错误时由 Pydantic 校验暴露。
    """
    username: str
    contact: Optional[str] = ""


class PasswordResetVerifyRequest(BaseModel):
    """
    找回密码验证码校验请求。

    校验和确认分开，是为了前端能先提示“验证码有效”，再让用户输入新密码，减少误改密码的操作成本。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 密码重置验证码校验模型。
    @raises: 用户名或验证码缺失时由 Pydantic 校验暴露。
    """
    username: str
    code: str


class PasswordResetConfirmRequest(PasswordResetVerifyRequest):
    """
    找回密码最终确认请求，在验证码有效后写入新密码。

    继承校验请求是为了复用 username/code 口径；`newPassword/new_password` 双别名保留给 PC 和脚本兼容。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 密码重置确认模型。
    @raises: 新密码过短、验证码或用户名缺失时由 Pydantic 校验暴露。
    """
    newPassword: str = Field(min_length=6, validation_alias=AliasChoices("newPassword", "new_password"))


# ===== User =====
class UserProfileUpdate(BaseModel):
    """
    用户资料更新请求，限定普通资料字段，避免前端把权限、权益或微信身份混进个人信息更新。

    PC 和小程序都会展示昵称、头像、省份等信息；这些字段只影响展示和默认备考地区，不应承担登录凭证或管理员状态的修改职责。

    @param: 无；FastAPI 根据请求体实例化，所有字段均为可选以支持局部更新。
    @return: 用户资料更新模型。
    @raises: 字段类型不符合声明时由 Pydantic 校验暴露。
    """
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    province: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    """
    用户主动修改密码请求。

    `old_password/oldPassword` 和 `new_password/newPassword` 双别名保留，是为了兼容 PC 表单、小程序请求和早期脚本的不同命名。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 密码修改请求模型。
    @raises: 新密码少于 6 位或字段缺失时由 Pydantic 校验暴露。
    """
    old_password: str = Field(validation_alias=AliasChoices("old_password", "oldPassword"))
    new_password: str = Field(min_length=6, validation_alias=AliasChoices("new_password", "newPassword"))

class UserPreferencesUpdate(BaseModel):
    """
    用户备考偏好更新请求，承载默认时间、媒体开关和考试体系偏好。

    偏好会影响首页推荐、定向备面默认筛选和考场默认读题/答题时间；这里不保存真实题库分类结果，避免用户偏好反向污染题库元数据。

    @param: 无；FastAPI 根据请求体实例化，未传字段保持原偏好。
    @return: 用户备考偏好更新模型。
    @raises: 时间字段、布尔字段或维度列表类型不合法时由 Pydantic 校验暴露。
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
    用户默认省份更新请求。

    默认省份只用于用户侧筛选和推荐起点，不能替代题目的真实考试体系分类；这条边界对江苏事业单位、省考和特色入口纠偏很重要。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 默认省份更新模型。
    @raises: 省份字段缺失或类型错误时由 Pydantic 校验暴露。
    """
    province: str


class UserTermsAgreementRequest(BaseModel):
    """
    用户协议确认请求，记录用户主动同意的协议版本。

    小程序审核要求授权和登录都由用户主动触发；协议版本单独落库，便于证明用户是在登录页或相关操作前主动确认。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 用户协议确认模型。
    @raises: 协议版本缺失或类型错误时由 Pydantic 校验暴露。
    """
    version: str


class SubscriptionSwitchRequest(BaseModel):
    """
    用户切换当前使用权益的请求。

    用户可能同时拥有试用、月卡和人工补发权益；显式传 `subscriptionId` 可以避免系统自动选择时扣错权益。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 权益切换请求模型。
    @raises: 权益 ID 缺失或类型错误时由 Pydantic 校验暴露。
    """
    subscriptionId: int = Field(validation_alias=AliasChoices("subscriptionId", "subscription_id"))


class EntitlementGrantRequest(BaseModel):
    """
    EntitlementGrantRequest 固定管理员补发权益的输入边界，避免人工补偿被误写成微信支付订单。

    补发必须写清时长、每日限额、有效期和原因，方便后续客服复盘；它只生成人工权益和审计流水，不生成支付订单。

    @param: 无；FastAPI 根据管理员请求体实例化。
    @return: 管理员人工补发权益请求模型。
    @raises: 分钟数、有效期、原因或备注为空时由 Pydantic 校验暴露。
    """
    totalMinutes: int = Field(gt=0, validation_alias=AliasChoices("totalMinutes", "total_minutes"))
    dailyLimitMinutes: int = Field(ge=0, validation_alias=AliasChoices("dailyLimitMinutes", "daily_limit_minutes"))
    startAt: str = Field(min_length=1, validation_alias=AliasChoices("startAt", "start_at"))
    endAt: str = Field(min_length=1, validation_alias=AliasChoices("endAt", "end_at"))
    reasonType: str = Field(min_length=1, validation_alias=AliasChoices("reasonType", "reason_type"))
    remark: str = Field(min_length=1, max_length=1000)


class EntitlementDeductRequest(BaseModel):
    """
    EntitlementDeductRequest 固定管理员扣减权益的输入边界，扣减只作用于指定权益，不改历史用量流水。

    售后扣减用于退款、误操作修正等场景；不伪造 `usage_records`，是为了让答题历史和客服处理流水保持两条独立账。

    @param: 无；FastAPI 根据管理员请求体实例化。
    @return: 管理员扣减权益请求模型。
    @raises: 权益 ID、扣减分钟、原因或备注为空时由 Pydantic 校验暴露。
    """
    subscriptionId: int = Field(gt=0, validation_alias=AliasChoices("subscriptionId", "subscription_id"))
    deductMinutes: int = Field(gt=0, validation_alias=AliasChoices("deductMinutes", "deduct_minutes"))
    reasonType: str = Field(min_length=1, validation_alias=AliasChoices("reasonType", "reason_type"))
    remark: str = Field(min_length=1, max_length=1000)


# ===== Question =====
class QuestionCreate(BaseModel):
    """
    题库新增请求，承载真实题源分类、题型维度、套题信息和评分依据。

    字段较多是因为题库导入和管理员编辑要同时保留“考试体系”和“训练分类”两套口径；
    不得用省份、题型或特色入口替代真实题源分类，否则全真模拟和重点分析会产生伪匹配。

    @param: 无；FastAPI 根据题库编辑或导入请求实例化。
    @return: 题库新增请求模型。
    @raises: 题干缺失、字段类型不合法或时间/分值字段格式错误时由 Pydantic 校验暴露。
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
    题库更新请求沿用新增题目的完整字段口径。

    管理员编辑题目时需要能纠偏分类、补评分点和修套题信息；继承 `QuestionCreate` 可以避免新增和编辑出现两套分类字段。

    @param: 无；FastAPI 根据题库编辑请求实例化。
    @return: 题库更新请求模型。
    @raises: 字段类型或约束不符合 `QuestionCreate` 约定时由 Pydantic 校验暴露。
    """
    pass


# ===== Exam =====
class ExamStartRequest(BaseModel):
    """
    开始考试请求，锁定本次考试使用的题目 ID 顺序。

    全真模拟需要按真实套题组卷，专项练习也要稳定复现抽题结果；前端传入题目顺序后，后续提交和历史记录都以这份顺序为准。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 开始考试请求模型。
    @raises: 题目 ID 列表缺失或类型错误时由 Pydantic 校验暴露。
    """
    questionIds: List[str]


class UsageReportRequest(BaseModel):
    """
    练习用时上报请求，用于权益分钟扣减和用量审计。

    上报支持驼峰和下划线别名，是为了 PC、小程序和旧脚本都能复用同一接口；服务层再决定是否真正扣减权益。

    @param: 无；FastAPI 根据请求体实例化。
    @return: 用时上报请求模型。
    @raises: 用时为负数或必需字段缺失时由 Pydantic 校验暴露。
    """
    examId: str = Field(validation_alias=AliasChoices("examId", "exam_id"))
    questionId: Optional[str] = Field(default=None, validation_alias=AliasChoices("questionId", "question_id"))
    usageSeconds: int = Field(ge=0, validation_alias=AliasChoices("usageSeconds", "usage_seconds"))
    usageType: str = Field(default="practice", validation_alias=AliasChoices("usageType", "usage_type"))


# ===== Payment =====
class PaymentOrderCreateRequest(BaseModel):
    """
    支付下单请求，当前付费虚拟训练权益统一走微信小程序官方虚拟支付。

    `code/openId` 同时保留，是为了兼容手机端 code2session 和已绑定 openId 的复用场景；
    普通微信支付、PC mock 支付都不能在虚拟商品链路里回退使用。

    @param: 无；FastAPI 根据套餐中心下单请求实例化。
    @return: 支付下单请求模型。
    @raises: 套餐编码缺失或字段类型不合法时由 Pydantic 校验暴露。
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
    微信虚拟支付前端确认请求。

    前端支付结果只能说明用户完成了一次拉起流程，不能作为到账依据；后端仍需用微信查单结果确认后再发放权益。

    @param: 无；FastAPI 根据小程序支付回传结果实例化。
    @return: 虚拟支付确认请求模型。
    @raises: rawResult 类型不合法或字段别名类型错误时由 Pydantic 校验暴露。
    """
    scene: str = Field(default="mini_program_virtual")
    payResult: str = Field(default="success", validation_alias=AliasChoices("payResult", "pay_result"))
    thirdPartyOrderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("thirdPartyOrderNo", "third_party_order_no"))
    paidAt: Optional[str] = Field(default=None, validation_alias=AliasChoices("paidAt", "paid_at"))
    outTradeNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("outTradeNo", "out_trade_no"))
    rawResult: Dict = Field(default_factory=dict, validation_alias=AliasChoices("rawResult", "raw_result"))


class RefundBalanceStatsRequest(BaseModel):
    """
    管理员退款余额查询请求。

    售后排查可以按用户名或订单号定位，统计结果需要同时看订单和权益，避免只看支付订单而忽略用户已消耗时长。

    @param: 无；FastAPI 根据管理员查询请求实例化。
    @return: 退款余额查询请求模型。
    @raises: 订单号别名类型错误时由 Pydantic 校验暴露。
    """
    username: Optional[str] = None
    orderNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("orderNo", "order_no"))


class RefundApplyRequest(BaseModel):
    """
    管理员退款处理请求。

    退款处理必须绑定订单号，并可记录退款小时数、原因和备注；这些信息会和权益状态一起用于后续客服核查。

    @param: 无；FastAPI 根据管理员退款请求实例化。
    @return: 退款处理请求模型。
    @raises: 订单号缺失、退款小时数为负或字段别名类型错误时由 Pydantic 校验暴露。
    """
    orderNo: str = Field(validation_alias=AliasChoices("orderNo", "order_no"))
    refundedHours: Optional[float] = Field(default=None, ge=0, validation_alias=AliasChoices("refundedHours", "refunded_hours"))
    refundReason: Optional[str] = Field(default="", validation_alias=AliasChoices("refundReason", "refund_reason"))
    refundRemark: Optional[str] = Field(default="", validation_alias=AliasChoices("refundRemark", "refund_remark"))


# ===== Support =====
class SupportFeedbackCreateRequest(BaseModel):
    """
    用户反馈创建请求，收集问题摘要、联系方式、页面路径和附件。

    反馈入口要同时覆盖 PC 和小程序；保留 routePath/province/attachments 是为了让管理员能从页面、题目和地区上下文判断问题来源。

    @param: 无；FastAPI 根据用户反馈请求实例化。
    @return: 用户反馈创建请求模型。
    @raises: 摘要为空、摘要过长或附件类型不合法时由 Pydantic 校验暴露。
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
    管理员更新反馈处理状态的请求。

    后台只允许更新状态和管理员备注，避免客服处理时误改用户原始反馈内容，保留可追溯性。

    @param: 无；FastAPI 根据管理员处理请求实例化。
    @return: 反馈处理更新请求模型。
    @raises: 状态或备注字段类型错误时由 Pydantic 校验暴露。
    """
    status: Optional[str] = None
    adminNote: Optional[str] = Field(default=None, validation_alias=AliasChoices("adminNote", "admin_note"))


# ===== Scoring =====
class EvaluateRequest(BaseModel):
    """
    答案评分请求，提交题目 ID、文字稿和可选考试 ID。

    文字稿可能来自手动输入或 ASR，后端会继续根据题干、采分点和 LLM 评分；占位提示文本不应被当作可靠作答内容。

    @param: 无；FastAPI 根据评分请求体实例化。
    @return: 答案评分请求模型。
    @raises: 题目 ID 缺失或文字稿超过长度限制时由 Pydantic 校验暴露。
    """
    questionId: str
    transcript: str = Field(max_length=5000)
    examId: Optional[str] = None


# ===== Targeted =====
class FocusAnalysisRequest(BaseModel):
    """
    定向备面重点分析请求。

    请求同时携带考试体系、地区、方向和时间模式，是为了支持动态层级和“方向不限”；
    重点分析必须基于真实题库统计或管理员发布内容，没有数据时不能回退成通用模板。

    @param: 无；FastAPI 根据定向备面筛选请求实例化。
    @return: 重点分析请求模型。
    @raises: 时间、题量或列表字段类型不合法时由 Pydantic 校验暴露。
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
    定向备面抽题请求。

    抽题筛选和重点分析共用分类口径，但结果不同：抽题返回真实题目，重点分析返回统计和管理员内容；
    `sourceMode` 保留给本地题库与后续生成模式切换，默认仍优先使用真实题库。

    @param: 无；FastAPI 根据定向抽题请求实例化。
    @return: 定向抽题请求模型。
    @raises: 抽题数量、时间、题量或筛选字段类型不合法时由 Pydantic 校验暴露。
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
    专项训练抽题请求，按训练分类筛选题目。

    `dimension` 在这里表示题型/训练分类，不表示考生能力维度；能力雷达、薄弱维度和评分维度另有独立口径，不能混用。

    @param: 无；FastAPI 根据专项训练请求实例化。
    @return: 专项训练抽题请求模型。
    @raises: 训练分类缺失、抽题数量或筛选字段类型不合法时由 Pydantic 校验暴露。
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
