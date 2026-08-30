"""
线上 MySQL ORM 模型，定义用户、题目、考试、答题、历史成绩、支付订单、权益、反馈和管理员权益调整流水。

这些类不是普通数据容器，而是 PC、小程序、导入脚本、支付回调、评分结果和后台管理共同依赖的数据契约。
字段名、长度、外键和 collation 必须和 `database_setup.py` 的 MySQL DDL 对齐；尤其是新增外键表时，
MySQL 会要求引用列和被引用列的类型、长度、字符集与排序规则一致。支付订单只记录真实支付链路，
人工补发/扣减写入 `EntitlementAdjustment`，避免售后处理污染微信虚拟支付审计口径。

@param: 无；服务层和测试通过 SQLAlchemy Session 创建、查询和提交这些模型实例。
@return: 暴露 SQLAlchemy declarative model 类，供路由、服务、脚本和数据迁移复用。
@raises ImportError: SQLAlchemy、数据库基类或依赖模块缺失时导入失败；约束错误通常在数据库提交时暴露。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


MYSQL_BIGINT = BigInteger().with_variant(Integer, "sqlite")


def gen_id(prefix=""):
    """
    生成短业务 ID，用在仍需要字符串主键或人工可读前缀的旧表。

    这里没有改成数据库自增，是为了不破坏已经暴露给前端、历史报告和导入资产的题目/考试/订单编号口径。
    8 位 UUID 适合当前规模的展示 ID，但不应被用于需要强幂等或金融级唯一性的外部交易号。

    @param prefix: 业务前缀，例如题目、考试或订单的类型标记。
    @return: 带前缀的短随机 ID。
    @raises: 不主动抛出业务异常。
    """
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class User(Base):
    """
    平台账号主表，兼容 PC 账号密码登录、小程序 openId 绑定、管理员权限和用户活跃统计。

    `preferences` 继续保留 JSON，是为了让小程序登录状态、订阅快照、偏好引导等轻量配置可以渐进升级，
    不必每次调整端侧展示都新增列。`last_login_at`、`last_active_at` 和 `registered_at` 分开记录，
    是为了区分“新注册”“当天回来浏览”和“真正重新登录”三类运营口径。

    @param: 无；由 SQLAlchemy 在服务层、脚本或测试中实例化。
    @return: 用户 ORM 实例，可关联订单、权益、用量和人工调整流水。
    @raises: 类定义阶段不主动抛出异常；唯一索引、外键和非空约束错误会在数据库提交时暴露。
    """
    __tablename__ = "users"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(64), default="")
    email = Column(String(128), default="")
    avatar = Column(String(256), default="")
    province = Column(String(32), default="national")
    disabled = Column(Boolean, default=False)
    preferences = Column(JSON, default=dict)
    agreed_terms_version = Column(String(20), default="")
    agreed_terms_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)
    last_login_device = Column(String(200), default="")
    login_device_history = Column(JSON, default=list)
    invite_code = Column(String(32), default="", index=True)
    invite_partner_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_bound_at = Column(DateTime, nullable=True)
    invite_source = Column(String(40), default="")
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment_orders = relationship("PaymentOrder", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    entitlement_adjustments = relationship("EntitlementAdjustment", back_populates="user", cascade="all, delete-orphan")


class PasswordResetCase(Base):
    """
    当前有效的人工密码重置申请。

    用户侧只创建待处理申请；管理员核对账号和联系方式后才生成一次性验证码。验证码仅保存哈希，
    明文只在管理员签发响应中出现一次；重置完成后整条记录删除，因此本表不承担历史审计用途。

    @param: 无；由认证服务创建、签发、验证并在完成时删除。
    @return: 当前密码重置申请 ORM 实例。
    @raises: 唯一用户约束或用户外键错误在数据库提交时暴露。
    """
    __tablename__ = "password_reset_cases"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(MYSQL_BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    username_snapshot = Column(String(64), nullable=False, index=True)
    contact = Column(String(255), default="")
    status = Column(String(24), nullable=False, default="pending", index=True)
    code_hash = Column(String(255), default="")
    delivery_channel = Column(String(24), default="manual")
    handled_by = Column(String(64), default="")
    failed_attempts = Column(Integer, nullable=False, default=0)
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)


class InvitePartner(Base):
    """
    邀请码合作公司 / 渠道表。

    合作公司承载联系人和启停状态，一个合作公司可以配置多个全站唯一的邀请码。
    """
    __tablename__ = "invite_partners"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    remark = Column(Text, default="")
    contact_name = Column(String(100), default="")
    contact_phone = Column(String(50), default="")
    contact_wechat = Column(String(100), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class InviteCode(Base):
    """
    全站唯一邀请码表。

    邀请码只支持启停，不做有效期和次数限制；归属合作公司用于注册、活跃和付费报表聚合。
    """
    __tablename__ = "invite_codes"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    partner_id = Column(MYSQL_BIGINT, ForeignKey("invite_partners.id"), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    remark = Column(Text, default="")
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    partner = relationship("InvitePartner")


class InviteRegistrationEvent(Base):
    """
    新用户注册时的邀请码快照表。

    这张表只记录创建账号时的来源快照，管理员后续修正当前归因时不回写这里，以保证历史报表不回算。
    """
    __tablename__ = "invite_registration_events"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    registered_date = Column(Date, nullable=False, index=True)
    invite_code_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_partner_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_code_snapshot = Column(String(32), default="", index=True)
    invite_partner_snapshot = Column(String(100), default="", index=True)
    source = Column(String(40), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class InviteActivityDaily(Base):
    """
    邀请来源日活快照表。

    登录或鉴权触达时按自然日写入一次，保存当时用户的邀请码归因快照，避免后续纠错影响历史 DAU。
    """
    __tablename__ = "invite_activity_daily"
    __table_args__ = (
        Index("uq_iad_username_active_date", "username", "active_date", unique=True),
        Index("idx_iad_date_partner_code", "active_date", "invite_partner_id", "invite_code_id"),
    )
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, index=True)
    active_date = Column(Date, nullable=False, index=True)
    invite_code_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_partner_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_code_snapshot = Column(String(32), default="", index=True)
    invite_partner_snapshot = Column(String(100), default="", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class InvitePaymentEvent(Base):
    """
    支付订单的邀请码归因快照表。

    支付成功时写入一条订单快照，退款只更新 refunded_amount 和 net_amount，不改变原始邀请码归因。
    """
    __tablename__ = "invite_payment_events"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    order_no = Column(String(100), nullable=False, unique=True, index=True)
    username = Column(String(64), nullable=False, index=True)
    paid_date = Column(Date, nullable=False, index=True)
    invite_code_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_partner_id = Column(MYSQL_BIGINT, nullable=True, index=True)
    invite_code_snapshot = Column(String(32), default="", index=True)
    invite_partner_snapshot = Column(String(100), default="", index=True)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    refunded_amount = Column(Numeric(10, 2), nullable=False, default=0)
    net_amount = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class InviteAuditLog(Base):
    """
    邀请码后台操作审计表。

    管理员创建、编辑、启停邀请码和修正用户归因时写入前后快照与原因，便于渠道结算复盘。
    """
    __tablename__ = "invite_audit_logs"
    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    action_type = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(String(100), default="", index=True)
    operator = Column(String(64), default="", index=True)
    before_snapshot = Column(JSON, default=dict)
    after_snapshot = Column(JSON, default=dict)
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class SystemMetricSnapshot(Base):
    """
    管理员数据看板的服务器资源采样快照。

    这张表只保存低敏资源指标和连接状态，不保存日志正文或用户请求内容。采样按 5 分钟时间桶去重，
    用于后台查看近 30 天系统趋势。
    """
    __tablename__ = "system_metric_snapshots"
    __table_args__ = (
        Index("uq_sms_bucket_start", "bucket_start", unique=True),
        Index("idx_sms_created_at", "created_at"),
    )

    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    bucket_start = Column(DateTime, nullable=False)
    cpu_percent = Column(Float, nullable=False, default=0)
    memory_percent = Column(Float, nullable=False, default=0)
    memory_used_mb = Column(Integer, nullable=False, default=0)
    memory_total_mb = Column(Integer, nullable=False, default=0)
    disk_percent = Column(Float, nullable=False, default=0)
    disk_used_gb = Column(Float, nullable=False, default=0)
    disk_total_gb = Column(Float, nullable=False, default=0)
    load_1m = Column(Float, nullable=False, default=0)
    load_5m = Column(Float, nullable=False, default=0)
    load_15m = Column(Float, nullable=False, default=0)
    backend_pid = Column(Integer, nullable=False, default=0)
    backend_status = Column(String(30), nullable=False, default="running")
    db_ok = Column(Boolean, nullable=False, default=False)
    redis_ok = Column(Boolean, nullable=False, default=False)
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class ServerErrorEvent(Base):
    """
    应用级错误计数事件。

    看板只展示错误数量和最后发生时间，因此这里只记录状态码、路径和错误类型等排障索引信息，不写入日志正文。
    """
    __tablename__ = "server_error_events"
    __table_args__ = (
        Index("idx_see_created_status", "created_at", "status_code"),
        Index("idx_see_path_created", "path", "created_at"),
    )

    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    status_code = Column(Integer, nullable=False, default=500, index=True)
    method = Column(String(10), nullable=False, default="")
    path = Column(String(255), nullable=False, default="")
    request_id = Column(String(80), default="")
    error_type = Column(String(120), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class UserActivitySession(Base):
    """
    PC / 小程序心跳事件流水。

    事件级流水用于幂等去重和单用户明细核查；真正的每日汇总写入 `user_activity_daily`。
    """
    __tablename__ = "user_activity_sessions"
    __table_args__ = (
        Index("uq_uas_event_id", "event_id", unique=True),
        Index("idx_uas_username_active", "username", "active_at"),
        Index("idx_uas_session", "session_id"),
    )

    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    event_id = Column(String(80), nullable=False)
    username = Column(String(100, collation="utf8mb4_0900_ai_ci"), ForeignKey("users.username"), nullable=False, index=True)
    session_id = Column(String(80), nullable=False, default="")
    client_type = Column(String(30), nullable=False, default="pc", index=True)
    route_path = Column(String(255), default="")
    duration_seconds = Column(Integer, nullable=False, default=0)
    active_at = Column(DateTime, nullable=False, index=True)
    active_date = Column(Date, nullable=False, index=True)
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User")


class UserActivityDaily(Base):
    """
    用户每日真实活跃时长汇总。

    只统计心跳上线后的活跃秒数，历史数据不回填，避免把最后活跃时间误当成真实停留时长。
    """
    __tablename__ = "user_activity_daily"
    __table_args__ = (
        Index("uq_uad_username_active_date", "username", "active_date", unique=True),
        Index("idx_uad_active_date", "active_date"),
    )

    id = Column(MYSQL_BIGINT, primary_key=True, autoincrement=True)
    username = Column(String(100, collation="utf8mb4_0900_ai_ci"), ForeignKey("users.username"), nullable=False, index=True)
    active_date = Column(Date, nullable=False, index=True)
    active_seconds = Column(Integer, nullable=False, default=0)
    heartbeat_count = Column(Integer, nullable=False, default=0)
    last_active_at = Column(DateTime, nullable=True)
    client_types = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User")


class Question(Base):
    """
    结构化面试题目的最小运行表，保存题干、训练分类、省份、计时和评分辅助信息。

    更完整的真实考试体系、套题、岗位和复核字段主要存放在题库 JSON 资产与题目服务归一化结果中；
    这里保留较窄的表结构，是为了兼容早期接口和已生成的考试记录。`dimension` 表示题型/训练分类，
    不等同于考生能力维度，调用方不能用它去填充能力雷达或薄弱能力分析。

    @param: 无；由 SQLAlchemy 在导入、生成或测试场景中实例化。
    @return: 题目 ORM 实例，可供抽题、评分和历史记录引用。
    @raises: 类定义阶段不主动抛出异常；主键冲突或非空约束错误会在数据库提交时暴露。
    """
    __tablename__ = "questions"
    __table_args__ = (
        Index("idx_questions_province_dimension", "province", "dimension"),
        Index("idx_questions_dimension_province", "dimension", "province"),
    )
    id = Column(String(32), primary_key=True, default=lambda: gen_id("q_"))
    stem = Column(Text, nullable=False)
    dimension = Column(String(32), default="analysis")
    province = Column(String(32), default="national")
    prep_time = Column(Integer, default=90)
    answer_time = Column(Integer, default=180)
    scoring_points = Column(JSON, default=list)
    keywords = Column(JSON, default=lambda: {"scoring": [], "deducting": [], "bonus": []})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Exam(Base):
    """
    一次练习或模拟考试的题本记录，负责把用户、题目列表、答题记录和计费流水串起来。

    `question_ids` 使用 JSON 而不是拆中间表，是为了保留抽题时的原始顺序和兼容早期考试接口；
    真正的逐题文字稿、评分结果和媒体信息放在 `ExamAnswer`，这样未完成考试也能先落库题本。

    @param: 无；由 SQLAlchemy 在开始考试或测试夹具中实例化。
    @return: 考试 ORM 实例，可关联答题和权益消耗记录。
    @raises: 类定义阶段不主动抛出异常；状态或外键相关错误会在服务校验或数据库提交时暴露。
    """
    __tablename__ = "exams"
    id = Column(String(32), primary_key=True, default=lambda: gen_id("exam_"))
    user_id = Column(String(64), nullable=False, index=True)
    question_ids = Column(JSON, default=list)
    status = Column(String(16), default="in_progress")
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    answers = relationship("ExamAnswer", back_populates="exam", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="exam", cascade="all, delete-orphan")


class ExamAnswer(Base):
    """
    单题作答结果表，用来保存 ASR 文字稿、评分 JSON 和音视频分析摘要。

    评分后才展示题目分数和维度结果，所以原始作答阶段只需要保存 transcript 与媒体上下文；
    `score_result` 保持 JSON，是为了兼容 LLM 评分结构迭代和两阶段评分的回归字段。

    @param: 无；由 SQLAlchemy 在提交作答或测试夹具中实例化。
    @return: 单题答题 ORM 实例，可回挂到所属考试。
    @raises: 类定义阶段不主动抛出异常；考试外键缺失会在数据库提交时暴露。
    """
    __tablename__ = "exam_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=False)
    transcript = Column(Text, default="")
    score_result = Column(JSON, default=dict)
    media_record = Column(JSON, default=dict)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exam = relationship("Exam", back_populates="answers")


class HistoryRecord(Base):
    """
    考试完成后的摘要快照，支撑历史列表、成绩趋势、薄弱分析和复盘入口。

    这里保存的是评分完成时的展示快照，而不是重新计算入口；这样题库、评分规则或题目元数据后续调整时，
    用户历史成绩仍能按当时结果稳定展示。`dimensions` 应保存能力维度结果，不应混入题型分类。

    @param: 无；由 SQLAlchemy 在考试完成或测试夹具中实例化。
    @return: 历史成绩 ORM 实例，可按用户、考试和省份检索。
    @raises: 类定义阶段不主动抛出异常；唯一考试编号冲突会在数据库提交时暴露。
    """
    __tablename__ = "history_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=False, index=True)
    question_count = Column(Integer, default=0)
    total_score = Column(Float, default=0)
    max_score = Column(Float, default=100)
    grade = Column(String(4), default="B")
    dimensions = Column(JSON, default=list)
    province = Column(String(32), default="national")
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SubscriptionPackage(Base):
    """
    套餐配置表，描述可购买或可发放的训练权益模板。

    微信虚拟支付道具价格和审核口径不允许后台随意改写，所以本表主要作为后端到账和权益生成模板；
    管理员人工补发会写入 `manual_grant` 类权益，但不应伪造成支付订单。

    @param: 无；由 SQLAlchemy 在种子脚本、套餐查询或测试夹具中实例化。
    @return: 套餐 ORM 实例，可用于创建订单或权益。
    @raises: 类定义阶段不主动抛出异常；套餐编码唯一性错误会在数据库提交时暴露。
    """
    __tablename__ = "subscription_packages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    package_code = Column(String(100), unique=True, nullable=False, index=True)
    package_name = Column(String(100), nullable=False)
    package_type = Column(String(30), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    total_minutes = Column(Integer, nullable=False, default=0)
    daily_limit_minutes = Column(Integer, nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), default="")
    extra_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PaymentOrder(Base):
    """
    真实支付订单表，只记录微信小程序虚拟支付等外部支付链路产生的订单。

    审核和退款都依赖订单字段能追溯到微信侧交易号、openId、虚拟支付 env 和原始回调。
    人工补偿、活动赠送和售后扣减不写这里，避免把客服处理误认为用户真实付款。

    @param: 无；由 SQLAlchemy 在下单、支付确认或退款测试中实例化。
    @return: 支付订单 ORM 实例，可关联用户并驱动权益到账。
    @raises: 类定义阶段不主动抛出异常；订单号唯一性和用户外键错误会在数据库提交时暴露。
    """
    __tablename__ = "payment_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    package_code = Column(String(100), nullable=False, index=True)
    package_type = Column(String(30), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    pay_channel = Column(String(30), nullable=False, default="wechat_virtual")
    status = Column(String(30), nullable=False, default="pending", index=True)
    third_party_order_no = Column(String(100), default="")
    paid_at = Column(DateTime, nullable=True)
    callback_payload = Column(JSON, default=dict)
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payment_orders")


class SupportFeedback(Base):
    """
    用户反馈和客服处理表，承接小程序、PC 的题目纠错、支付问题和功能建议。

    反馈允许附带页面路径、省份、题号和联系方式，是为了管理员能复现问题；处理状态和备注留在同一表中，
    方便第一版后台直接闭环，不额外引入工单系统。

    @param: 无；由 SQLAlchemy 在提交反馈、管理员处理或测试夹具中实例化。
    @return: 反馈 ORM 实例，可按用户、状态、省份和创建时间查询。
    @raises: 类定义阶段不主动抛出异常；必填摘要缺失会在数据库提交时暴露。
    """
    __tablename__ = "support_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, index=True)
    feedback_type = Column(String(64), nullable=False, default="其他建议", index=True)
    question_id = Column(String(64), default="")
    summary = Column(Text, nullable=False)
    contact = Column(String(255), default="")
    route_path = Column(String(255), default="")
    province = Column(String(64), default="", index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    admin_note = Column(Text, default="")
    handled_by = Column(String(64), default="")
    handled_at = Column(DateTime, nullable=True)
    attachments = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TargetedFocusConfig(Base):
    """
    管理员发布的定向备面重点分析覆盖表。

    普通用户默认看到题库真实统计；当某个考试体系/地区/岗位需要运营校正时，管理员可用本表发布覆盖结果。
    停用后应回到自动统计或空态，不能回退到伪造通用分析。

    @param: 无；由 SQLAlchemy 在管理员保存重点分析配置时实例化。
    @return: 定向重点配置 ORM 实例，payload 保存兼容前端的分析结构。
    @raises: 类定义阶段不主动抛出异常；target_key 唯一性错误会在数据库提交时暴露。
    """
    __tablename__ = "targeted_focus_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_key = Column(String(255), unique=True, nullable=False, index=True)
    target_code = Column(String(100), default="", index=True)
    target_name = Column(String(255), default="")
    province = Column(String(64), default="", index=True)
    position = Column(String(64), default="", index=True)
    payload = Column(JSON, default=dict)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    updated_by = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserSubscription(Base):
    """
    用户权益实例表，记录某个用户实际拥有、已消耗和每日限额的训练时长。

    权益和支付订单分开，是为了同时支持微信到账、试用、管理员补发和退款扣减。扣减剩余时长通过增加
    `used_minutes` 完成，不回写历史 `UsageRecord`，避免把客服操作伪装成真实答题消耗。

    @param: 无；由 SQLAlchemy 在支付到账、试用创建、人工补发或测试夹具中实例化。
    @return: 用户权益 ORM 实例，可关联用户、用量和人工调整流水。
    @raises: 类定义阶段不主动抛出异常；用户外键或数值边界问题会在服务校验或数据库提交时暴露。
    """
    __tablename__ = "user_subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    package_code = Column(String(100), nullable=False, index=True)
    plan_type = Column(String(30), nullable=False, index=True)
    plan_name = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="active", index=True)
    is_trial = Column(Boolean, nullable=False, default=False)
    trial_completed = Column(Boolean, nullable=False, default=False)
    total_minutes = Column(Integer, nullable=False, default=0)
    used_minutes = Column(Integer, nullable=False, default=0)
    daily_limit_minutes = Column(Integer, nullable=False, default=0)
    daily_used_minutes = Column(Integer, nullable=False, default=0)
    last_reset_date = Column(Date, nullable=True)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    source_order_no = Column(String(100), default="")
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscriptions")


class EntitlementAdjustment(Base):
    """
    EntitlementAdjustment 记录人工权益调整流水；它不替代订单和用量记录，只负责让管理员补发、扣减有账可查。

    人工补偿和售后扣减不能混进微信支付订单，否则支付审核、退款和客服核查都会失去边界。

    @param: 无；SQLAlchemy 根据字段声明映射数据库表。
    @return: 人工权益调整 ORM 模型，可被服务层用于审计查询和余额快照追踪。
    @raises: 字段约束或外键约束错误会在数据库提交时暴露。
    """
    __tablename__ = "entitlement_adjustments"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    target_username = Column(
        String(100, collation="utf8mb4_0900_ai_ci"),
        ForeignKey("users.username"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(BigInteger, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    action_type = Column(String(30), nullable=False, index=True)
    minutes_delta = Column(Integer, nullable=False, default=0)
    before_snapshot = Column(JSON, default=dict)
    after_snapshot = Column(JSON, default=dict)
    reason_type = Column(String(64), nullable=False, default="其他", index=True)
    remark = Column(Text, default="")
    operator = Column(String(100, collation="utf8mb4_0900_ai_ci"), nullable=False, default="", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="entitlement_adjustments")
    subscription = relationship("UserSubscription")


class UsageRecord(Base):
    """
    真实训练消耗流水表，用来解释权益分钟数为什么减少。

    它只记录用户答题、模拟考试等业务动作产生的消耗；管理员扣减不写入这里，而写入 `EntitlementAdjustment`。
    这样用户用量、客服调整和支付退款三类账目可以分开核对。

    @param: 无；由 SQLAlchemy 在上报训练用时或测试夹具中实例化。
    @return: 用量流水 ORM 实例，可关联用户和考试。
    @raises: 类定义阶段不主动抛出异常；用户或考试外键缺失会在数据库提交时暴露。
    """
    __tablename__ = "usage_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), ForeignKey("users.username"), nullable=False, index=True)
    exam_id = Column(String(32), ForeignKey("exams.id"), nullable=False, index=True)
    question_id = Column(String(32), nullable=True)
    usage_type = Column(String(30), nullable=False, default="practice", index=True)
    usage_seconds = Column(Integer, nullable=False, default=0)
    billed_minutes = Column(Integer, nullable=False, default=0)
    reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extra_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="usage_records")
    exam = relationship("Exam", back_populates="usage_records")
