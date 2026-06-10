"""
登录、找回密码和退款测试锁定前端已经依赖的补齐接口。

这些接口曾经容易因为 PC、小程序发布节奏不同而缺失：小程序微信登录后要能补全 PC 用户名，
密码重置要在无短信服务的本地环境可回归，管理员退款还要同时更新订单和权益状态。这里用隔离库验证这些路径不再“页面有入口、后端没接口”。

@param: 无；每个用例在内存库中准备账号、订单、套餐和权益。
@return: 无直接返回；断言通过表示路由注册和核心服务行为仍匹配前端入口。
@raises ImportError: FastAPI 路由、SQLAlchemy 模型或认证/支付服务导入失败时会暴露。
"""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import api_router
from app.core.config import settings
from app.core.security import verify_password
from app.db.session import Base
from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RefundApplyRequest,
    RefundBalanceStatsRequest,
    WechatMiniProgramAccountRequest,
    WechatMiniProgramLoginRequest,
)
from app.services.auth_service import (
    confirm_password_reset,
    login_wechat_miniprogram,
    request_password_reset,
    setup_wechat_miniprogram_account,
    verify_password_reset,
)
from app.services.payment_service import apply_refund, get_refund_balance_stats


class DummyAuthUser:
    """
    测试用认证用户，模拟路由层已经完成管理员鉴权后的身份对象。

    退款服务只关心 username、isAdmin 和 permissions；用轻量替身可以把测试重点放在订单和权益状态同步上。

    @param username: 要模拟的登录用户名。
    @param is_admin: 是否模拟管理员身份。
    @return: 测试用认证用户对象。
    @raises: 不主动抛出异常；字段值由具体测试场景控制。
    """
    def __init__(self, username="admin", is_admin=True):
        self.username = username
        self.isAdmin = is_admin
        self.permissions = {}


class AuthAndPaymentEndpointTestCase(unittest.TestCase):
    """
    登录、找回密码和退款补齐接口的回归用例集合。

    这些路径都曾经表现为“前端已有入口，但后端路由或服务还没补齐”。测试直接覆盖路由注册和核心服务，
    防止 PC、小程序、管理员工作台发布节奏不同导致用户点到 404 或退款状态不同步。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 路由缺失、账号绑定失败、密码重置失败或退款状态不同步时由断言报告。
    """
    def setUp(self):
        """
        为认证和退款回归测试创建隔离内存库。

        这些用例验证路由注册和服务闭环，不需要现网 MySQL 数据；内存库能让用户、套餐、订单和权益状态互不污染。

        @param: 无；由 unittest 在每个用例前调用。
        @return: None；SQLAlchemy 会话和表结构准备完成。
        @raises AssertionError: 数据库初始化失败会由测试框架报告。
        """
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        """
        释放认证和退款回归测试使用的内存库。

        显式关闭会话和 engine，避免同一进程内后续测试复用已经废弃的连接状态。

        @param: 无；由 unittest 在每个用例后调用。
        @return: None；数据库会话关闭且 engine 释放。
        @raises AssertionError: 资源释放失败会由测试框架报告。
        """
        self.db.close()
        self.engine.dispose()

    def test_missing_frontend_routes_are_registered(self):
        """
        PC 和小程序已经调用的认证/退款路由必须全部注册。

        这里不测业务结果，只守住路由存在性；这样路由拆分、重命名或挂载遗漏会在构建前暴露。

        @param: 无；直接读取 `api_router.routes`。
        @return: None；所有前端依赖路径存在时通过。
        @raises AssertionError: 任一必需路由没有挂载到 v1 router 时失败。
        """
        route_paths = {route.path for route in api_router.routes}

        for path in {
            "/auth/wechat/miniprogram",
            "/auth/wechat/miniprogram/bind",
            "/auth/wechat/miniprogram/account",
            "/password-reset/request",
            "/password-reset/verify",
            "/password-reset/confirm",
            "/payment/admin/refund-stats",
            "/payment/admin/refund",
        }:
            self.assertIn(path, route_paths)

    def test_wechat_login_creates_account_and_account_setup_renames_it(self):
        """
        小程序微信登录创建的临时账号必须能补全为 PC 可登录账号。

        审核要求用户先浏览后主动登录，但真正登录后还要打通 PC 账号体系；
        这个用例防止 openId 绑定成功后，用户名和密码补全链路断掉。

        @param: 无；用 fake code2session 隔离微信网络请求。
        @return: None；临时账号创建、协议版本保存、账号重命名和密码写入都成功时通过。
        @raises AssertionError: 微信身份绑定、账号补全或密码校验任一环节失败时报告。
        """
        old_appid = settings.wechat_pay_appid
        old_secret = settings.wechat_miniprogram_app_secret
        settings.wechat_pay_appid = "wx_test"
        settings.wechat_miniprogram_app_secret = "secret"
        try:
            import app.services.auth_service as auth_service

            original = auth_service._code_to_session
            auth_service._code_to_session = lambda code: {
                "openid": "openid_1",
                "unionid": "union_1",
                "session_key": "session_key_1",
            }
            try:
                login = login_wechat_miniprogram(
                    self.db,
                    WechatMiniProgramLoginRequest(code="wx_code", agreedTermsVersion="v1.0"),
                )
            finally:
                auth_service._code_to_session = original
        finally:
            settings.wechat_pay_appid = old_appid
            settings.wechat_miniprogram_app_secret = old_secret

        self.assertTrue(login["access_token"])
        self.assertTrue(login["requiresPcAccountSetup"])
        generated_username = login["username"]
        user = self.db.query(User).filter(User.username == generated_username).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.agreed_terms_version, "v1.0")
        self.assertEqual(user.preferences["wechatMiniProgram"]["openId"], "openid_1")

        setup = setup_wechat_miniprogram_account(
            self.db,
            DummyAuthUser(generated_username),
            WechatMiniProgramAccountRequest(username="pc_user", password="new_password"),
        )

        self.assertEqual(setup["username"], "pc_user")
        self.assertFalse(setup["requiresPcAccountSetup"])
        renamed = self.db.query(User).filter(User.username == "pc_user").first()
        self.assertIsNotNone(renamed)
        self.assertTrue(verify_password("new_password", renamed.hashed_password))

    def test_password_reset_generates_verifies_and_confirms_code(self):
        """
        本地密码重置要覆盖“生成、校验、确认”完整闭环。

        当前没有接入真实短信服务，debugCode 是本地和测试环境排查账号问题的兜底；确认成功后必须清掉临时重置状态。

        @param: 无；先写入测试用户，再执行三步重置流程。
        @return: None；新密码可校验且 preferences 中不残留 passwordReset 时通过。
        @raises AssertionError: 验证码、密码更新或临时状态清理失败时报告。
        """
        self.db.add(User(username="alice", hashed_password="old"))
        self.db.commit()

        requested = request_password_reset(self.db, PasswordResetRequest(username="alice", contact="phone"))
        code = requested["debugCode"]

        verified = verify_password_reset(self.db, PasswordResetVerifyRequest(username="alice", code=code))
        self.assertTrue(verified["success"])

        confirmed = confirm_password_reset(
            self.db,
            PasswordResetConfirmRequest(username="alice", code=code, newPassword="new_password"),
        )
        self.assertTrue(confirmed["success"])
        user = self.db.query(User).filter(User.username == "alice").first()
        self.assertTrue(verify_password("new_password", user.hashed_password))
        self.assertNotIn("passwordReset", user.preferences)

    def test_admin_refund_stats_and_apply_refund_update_order_and_subscription(self):
        """
        管理员退款必须同时更新订单状态和对应权益状态。

        用户看到的可退余额来自订单和权益共同计算；只退订单、不关停权益会让用户继续消耗已退款时长。

        @param: 无；构造一笔 paid 虚拟支付订单和对应 active 权益。
        @return: None；退款统计、退款申请、订单状态和权益状态都符合预期时通过。
        @raises AssertionError: 可退时长计算错误、退款未落库或权益未同步失效时失败。
        """
        user = User(username="buyer", hashed_password="x")
        admin = User(username="admin", hashed_password="x")
        package = SubscriptionPackage(
            package_code="trial_3h",
            package_name="3小时体验包",
            package_type="hourly",
            price=Decimal("0.01"),
            total_minutes=180,
            daily_limit_minutes=180,
            duration_days=0,
            is_active=True,
        )
        order = PaymentOrder(
            order_no="PAY_REFUND_1",
            username="buyer",
            package_code="trial_3h",
            package_type="hourly",
            amount=Decimal("0.01"),
            status="paid",
            paid_at=datetime.now(timezone.utc),
            extra_payload={
                "openId": "openid_buyer",
                "virtualPayEnv": 0,
                "virtualProductId": "trial_3h",
            },
        )
        subscription = UserSubscription(
            username="buyer",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时体验包",
            status="active",
            total_minutes=180,
            used_minutes=60,
            daily_limit_minutes=180,
            daily_used_minutes=60,
            source_order_no="PAY_REFUND_1",
        )
        self.db.add_all([user, admin, package, order, subscription])
        self.db.commit()

        stats = get_refund_balance_stats(
            self.db,
            DummyAuthUser("admin", is_admin=True),
            RefundBalanceStatsRequest(username="buyer"),
        )
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["summary"]["refundableHours"], 2)

        import app.services.payment_service as payment_service

        original_query = payment_service.wechat_pay_service.query_virtual_order
        original_refund = payment_service.wechat_pay_service.refund_virtual_order
        payment_service.wechat_pay_service.query_virtual_order = lambda order, package: {
            "verified": True,
            "transactionId": "WX_ORDER_1",
            "raw": {"left_fee": 1},
            "request": {"openid": "openid_buyer"},
        }
        payment_service.wechat_pay_service.refund_virtual_order = lambda **kwargs: {
            "success": True,
            "refundOrderId": kwargs["refund_order_id"],
            "refundWxOrderId": "WX_REFUND_1",
            "raw": {"errcode": 0},
        }
        try:
            refunded = apply_refund(
                self.db,
                DummyAuthUser("admin", is_admin=True),
                RefundApplyRequest(orderNo="PAY_REFUND_1", refundedHours=2, refundRemark="用户申请"),
            )
        finally:
            payment_service.wechat_pay_service.query_virtual_order = original_query
            payment_service.wechat_pay_service.refund_virtual_order = original_refund

        self.assertTrue(refunded["success"])
        self.assertEqual(order.status, "refunded")
        self.assertEqual(subscription.status, "refunded")
        self.assertEqual(order.callback_payload["refund"]["refundedHours"], 2)


if __name__ == "__main__":
    unittest.main()
