"""
管理员权益调整测试，专门验证人工补发/扣减不会伪造成微信支付订单。

客服补偿、测试账号、退款扣减和误操作修正都要通过 `entitlement_adjustments` 留痕；用户余额需要立即刷新，
但历史答题记录和真实虚拟支付订单不能被篡改。这里使用本机 MySQL 临时库，是为了覆盖 collation、外键和审计表这些 SQLite 测不出来的现网风险。

@param: 无；测试用例自己创建临时库、用户、权益和管理员身份。
@return: 无直接返回；断言通过表示人工权益调整和审计边界仍符合当前设计。
@raises ImportError: MySQL、ORM 模型、schema 或权益服务导入失败时中断。
"""
import unittest
from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base
from app.models.entities import EntitlementAdjustment, PaymentOrder, User, UserSubscription
from app.schemas.common import AuthUser, EntitlementDeductRequest, EntitlementGrantRequest
from app.services.entitlement_admin_service import (
    deduct_user_entitlement,
    grant_user_entitlement,
    list_admin_users,
)
from app.services.subscription_service import get_subscription_status
import database_setup


class EntitlementAdminServiceTestCase(unittest.TestCase):
    """
    EntitlementAdminServiceTestCase 用临时 MySQL 库验证售后权益调整；这里关注支付隔离和审计完整性。

    人工权益是给管理员纠错和补偿用的，不应改写历史答题用量，也不应生成假的支付订单。

    @param: 无；unittest 负责实例化测试类。
    @return: 管理员权益服务回归测试用例类。
    @raises AssertionError: MySQL 环境不安全、权益余额错误或审计流水缺失时由测试报告。
    """
    def setUp(self):
        """
        setUp 每个用例重建临时 MySQL 库，是为了让补发、扣减和反向调整互不污染。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示该回归边界仍被守住。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        database_url = make_url(settings.database_url)
        if not database_url.drivername.startswith("mysql"):
            self.fail(f"权益管理测试必须使用 MySQL，当前配置为 {database_url.drivername}")
        if database_url.host not in {"127.0.0.1", "localhost"}:
            self.fail("权益管理测试默认只允许连接本机 MySQL，避免误碰远程数据库。")

        self.test_database = f"kaogong_ai_test_entitlement_{uuid4().hex[:8]}"
        self.admin_engine = create_engine(database_url.set(database=None))
        with self.admin_engine.begin() as conn:
            conn.exec_driver_sql(
                f"CREATE DATABASE `{self.test_database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

        mysql_config = database_setup.get_mysql_config()
        mysql_config["database"] = self.test_database
        database_setup.create_tables(mysql_config)
        self.engine = create_engine(database_url.set(database=self.test_database))
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.admin = AuthUser(username="admin", isAdmin=True)
        self.normal_user = AuthUser(username="staff", isAdmin=False)
        self.target = User(username="ssy", hashed_password="x", preferences={})
        self.db.add(self.target)
        self.db.commit()

    def tearDown(self):
        """
        tearDown 删除临时 MySQL 库，避免测试进程复用连接时拿到旧状态。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示该回归边界仍被守住。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        self.db.close()
        self.engine.dispose()
        with self.admin_engine.begin() as conn:
            conn.exec_driver_sql(f"DROP DATABASE IF EXISTS `{self.test_database}`")
        self.admin_engine.dispose()

    def test_admin_grant_creates_manual_subscription_without_payment_order(self):
        """
        test_admin_grant_creates_manual_subscription_without_payment_order 防止客服补偿被误记成真实微信订单。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示人工补发、审计和权益快照都符合预期。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        start_at = datetime.now() - timedelta(minutes=5)
        end_at = datetime.now() + timedelta(days=7)

        result = grant_user_entitlement(
            self.db,
            self.admin,
            "ssy",
            EntitlementGrantRequest(
                totalMinutes=120,
                dailyLimitMinutes=60,
                startAt=start_at.isoformat(),
                endAt=end_at.isoformat(),
                reasonType="客服补偿",
                remark="ASR异常补偿",
            ),
        )

        subscription = self.db.query(UserSubscription).filter_by(username="ssy", package_code="manual_grant").one()
        adjustment = self.db.query(EntitlementAdjustment).one()
        self.assertTrue(result["success"])
        self.assertEqual(subscription.plan_type, "manual")
        self.assertEqual(subscription.source_order_no, "")
        self.assertEqual(self.db.query(PaymentOrder).count(), 0)
        self.assertEqual(adjustment.action_type, "grant")
        self.assertEqual(adjustment.minutes_delta, 120)
        self.assertEqual(adjustment.operator, "admin")

        status = get_subscription_status(self.db, AuthUser(username="ssy"))
        self.assertEqual(status["packageCode"], "manual_grant")
        self.assertEqual(status["remainingMinutes"], 120)
        self.assertEqual(status["remainingDailyMinutes"], 60)

    def test_admin_deduct_updates_selected_subscription_and_writes_adjustment(self):
        """
        test_admin_deduct_updates_selected_subscription_and_writes_adjustment 约束扣减只动指定权益余额。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示扣减没有伪造答题用量流水。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        subscription = self._create_subscription(total_minutes=100, used_minutes=20, daily_limit_minutes=100, daily_used_minutes=10)

        result = deduct_user_entitlement(
            self.db,
            self.admin,
            "ssy",
            EntitlementDeductRequest(
                subscriptionId=subscription.id,
                deductMinutes=30,
                reasonType="退款扣减",
                remark="用户申请部分退款",
            ),
        )

        self.db.refresh(subscription)
        adjustment = self.db.query(EntitlementAdjustment).one()
        self.assertTrue(result["success"])
        self.assertEqual(subscription.used_minutes, 50)
        self.assertEqual(subscription.daily_used_minutes, 40)
        self.assertEqual(subscription.status, "active")
        self.assertEqual(adjustment.action_type, "deduct")
        self.assertEqual(adjustment.minutes_delta, -30)
        self.assertEqual(adjustment.before_snapshot["remainingMinutes"], 80)
        self.assertEqual(adjustment.after_snapshot["remainingMinutes"], 50)

    def test_admin_deduct_rejects_minutes_above_remaining(self):
        """
        test_admin_deduct_rejects_minutes_above_remaining 防止后台把权益扣成负数。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示服务层兜住了越界输入。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        subscription = self._create_subscription(total_minutes=60, used_minutes=45)

        with self.assertRaises(HTTPException) as ctx:
            deduct_user_entitlement(
                self.db,
                self.admin,
                "ssy",
                EntitlementDeductRequest(
                    subscriptionId=subscription.id,
                    deductMinutes=16,
                    reasonType="误操作修正",
                    remark="越界测试",
                ),
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(self.db.query(EntitlementAdjustment).count(), 0)

    def test_non_admin_cannot_adjust_entitlements(self):
        """
        test_non_admin_cannot_adjust_entitlements 确认按钮隐藏之外，后端也会挡住普通用户。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示管理员接口不能被普通账号直接调用。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        with self.assertRaises(HTTPException) as ctx:
            grant_user_entitlement(
                self.db,
                self.normal_user,
                "ssy",
                EntitlementGrantRequest(
                    totalMinutes=30,
                    dailyLimitMinutes=30,
                    startAt=datetime.now().isoformat(),
                    endAt=(datetime.now() + timedelta(days=1)).isoformat(),
                    reasonType="测试账号",
                    remark="普通用户不应通过",
                ),
            )

        self.assertEqual(ctx.exception.status_code, 403)

    def test_reverse_adjustment_uses_new_record_instead_of_deleting_audit(self):
        """
        test_reverse_adjustment_uses_new_record_instead_of_deleting_audit 记录误操作纠正的推荐路径。

        先扣减再补发会留下两条流水，余额恢复靠反向调整完成，历史处理过程仍可追溯。

        @param: 无；由测试框架直接调用，前置数据在 fixture、monkeypatch 或 setUp 中准备。
        @return: None；断言通过表示反向调整不会抹掉旧流水。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        subscription = self._create_subscription(total_minutes=100, used_minutes=60)
        deduct_user_entitlement(
            self.db,
            self.admin,
            "ssy",
            EntitlementDeductRequest(
                subscriptionId=subscription.id,
                deductMinutes=20,
                reasonType="误操作修正",
                remark="先模拟一次误扣",
            ),
        )
        grant_user_entitlement(
            self.db,
            self.admin,
            "ssy",
            EntitlementGrantRequest(
                totalMinutes=20,
                dailyLimitMinutes=20,
                startAt=datetime.now().isoformat(),
                endAt=(datetime.now() + timedelta(days=3)).isoformat(),
                reasonType="误操作修正",
                remark="用反向补发纠正误扣",
            ),
        )

        adjustments = self.db.query(EntitlementAdjustment).order_by(EntitlementAdjustment.id.asc()).all()
        users = list_admin_users(self.db, self.admin, username="ssy")
        self.assertEqual([item.action_type for item in adjustments], ["deduct", "grant"])
        self.assertEqual(users["list"][0]["remainingMinutes"], 40)

    def _create_subscription(
        self,
        total_minutes: int,
        used_minutes: int,
        daily_limit_minutes: int = 0,
        daily_used_minutes: int = 0,
    ) -> UserSubscription:
        """
        _create_subscription 建测试权益时显式写分钟字段，避免用默认值掩盖扣减边界。

        @param total_minutes: 权益总分钟。
        @param used_minutes: 已用分钟。
        @param daily_limit_minutes: 每日限额，0 表示不限。
        @param daily_used_minutes: 今日已用分钟。
        @return: 已提交到临时 MySQL 库的权益记录。
        @raises: 不主动包装底层错误；数据库异常会沿调用栈向上传递。
        """
        subscription = UserSubscription(
            username="ssy",
            package_code="trial_3h",
            plan_type="hourly",
            plan_name="3小时套餐",
            status="active",
            is_trial=False,
            total_minutes=total_minutes,
            used_minutes=used_minutes,
            daily_limit_minutes=daily_limit_minutes,
            daily_used_minutes=daily_used_minutes,
            last_reset_date=date.today(),
            start_at=datetime.now() - timedelta(days=1),
            end_at=datetime.now() + timedelta(days=10),
        )
        self.db.add(subscription)
        self.db.commit()
        return subscription


if __name__ == "__main__":
    unittest.main()
