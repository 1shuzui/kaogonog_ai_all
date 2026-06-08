"""
这个测试文件守住 `test_auth_and_payment_missing_endpoints` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    DummyAuthUser 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def __init__(self, username="admin", is_admin=True):
        self.username = username
        self.isAdmin = is_admin
        self.permissions = {}


class AuthAndPaymentEndpointTestCase(unittest.TestCase):
    """
    AuthAndPaymentEndpointTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def setUp(self):
        """
        setUp 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        """
        tearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.db.close()
        self.engine.dispose()

    def test_missing_frontend_routes_are_registered(self):
        """
        test_missing_frontend_routes_are_registered 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_wechat_login_creates_account_and_account_setup_renames_it 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_password_reset_generates_verifies_and_confirms_code 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_admin_refund_stats_and_apply_refund_update_order_and_subscription 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
