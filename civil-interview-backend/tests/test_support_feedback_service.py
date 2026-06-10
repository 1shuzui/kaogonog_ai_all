"""
反馈服务测试确认用户提交的问题能被管理员看见并维护状态。

客服反馈同时服务小程序“我的”页面和 PC 管理员工作台；如果接口只保存本地临时状态，
管理员就无法追踪审核、支付或 ASR 问题。这里验证反馈创建、列表、更新和非管理员拦截都走数据库记录。

@param: 无；setUp 创建隔离数据库和测试用户。
@return: 无直接返回；断言通过表示反馈接口和管理员权限仍匹配。
@raises ImportError: 反馈服务、路由或 ORM 依赖缺失时会失败。
"""
import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import api_router
from app.db.session import Base
from app.models.entities import SupportFeedback, User
from app.schemas.common import SupportFeedbackCreateRequest, SupportFeedbackUpdateRequest
from app.services.support_service import (
    create_support_feedback,
    delete_support_feedback,
    list_support_feedback,
    update_support_feedback,
)


class DummyAuthUser:
    """
    构造最小鉴权用户，模拟普通用户和管理员两种反馈操作身份。

    反馈服务只读取 username 和 isAdmin；使用轻量对象能避免把测试焦点带到登录、token 或权限构造细节上。

    @param username: 操作反馈的用户名称。
    @param is_admin: 是否管理员，用于验证反馈状态维护权限。
    @return: 可传给反馈服务函数的鉴权用户替身。
    @raises: 不主动抛出异常；权限不足由被测服务抛出 HTTPException。
    """
    def __init__(self, username="alice", is_admin=False):
        self.username = username
        self.isAdmin = is_admin


class SupportFeedbackServiceTestCase(unittest.TestCase):
    """
    客服反馈用例集合，覆盖用户提交、管理员查看处理和普通用户越权拦截。

    这条链路是运营排查审核、支付、ASR 和题库问题的入口；如果只测接口返回不测数据库记录，
    管理员工作台就可能看不到真实用户反馈。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 反馈持久化、路由注册或权限边界退化时由断言报告。
    """
    def setUp(self):
        """
        创建隔离反馈库和三类账号，避免不同反馈用例互相串数据。

        alice/bob/admin 分别代表本人反馈、其他用户反馈和管理员视角，足够覆盖列表过滤和状态维护边界。

        @param: 无；测试框架自动调用。
        @return: None；数据库会话写入实例字段供用例使用。
        @raises AssertionError: 建库或建表失败时由测试框架报告。
        """
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            User(username="alice", hashed_password="x"),
            User(username="bob", hashed_password="x"),
            User(username="admin", hashed_password="x"),
        ])
        self.db.commit()

    def tearDown(self):
        """
        关闭反馈测试库连接，确保下一条用例从空库开始。

        这里不做业务断言，只清理 SQLAlchemy 会话和内存库连接。

        @param: 无；测试框架自动调用。
        @return: None；关闭会话和引擎。
        @raises: 不主动抛出业务异常；连接释放异常会由测试框架暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_support_routes_are_registered(self):
        """
        小程序和 PC 管理端依赖的反馈路由必须挂在 v1 router 上。

        路由拆分或管理员工作台重构时，最常见的问题是 service 还在但 router 漏注册，页面会直接 404。

        @param: 无；直接读取 `api_router.routes`。
        @return: None；反馈列表、附件和详情维护路由都存在时通过。
        @raises AssertionError: 任一前端依赖路由缺失时失败。
        """
        route_paths = {route.path for route in api_router.routes}

        self.assertIn("/support/feedback", route_paths)
        self.assertIn("/support/feedback/attachments", route_paths)
        self.assertIn("/support/feedback/{feedback_id}", route_paths)

    def test_feedback_create_list_update_delete_uses_database_records(self):
        """
        反馈创建、列表、处理和删除都必须围绕数据库记录流转。

        管理员端需要看到所有用户反馈，普通用户只看自己的反馈；状态变更和处理备注也必须持久化，
        否则客服排查会丢失上下文。

        @param: 无；构造本人反馈、其他用户反馈和管理员操作。
        @return: None；过滤、汇总、处理备注和删除都符合预期时通过。
        @raises AssertionError: 反馈没有进库、权限视图错误或状态维护失败时失败。
        """
        alice = DummyAuthUser("alice")
        admin = DummyAuthUser("admin", is_admin=True)

        created = create_support_feedback(
            self.db,
            alice,
            SupportFeedbackCreateRequest(
                type="页面显示问题",
                summary="筛选反馈接口返回 404",
                questionId="q001",
                contact="wechat",
                routePath="/pages/support/index",
                province="江苏",
                attachments=[{"url": "/uploads/support-feedback/demo.png", "filename": "demo.png"}],
            ),
        )
        self.db.add(
            SupportFeedback(
                username="bob",
                feedback_type="支付或权益问题",
                summary="支付状态未同步",
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

        mine = list_support_feedback(
            self.db,
            alice,
            current=1,
            page_size=200,
            feedback_type="undefined",
            status="undefined",
            province="undefined",
            keyword="undefined",
            scope="all",
        )
        self.assertEqual(mine["total"], 1)
        self.assertEqual(mine["list"][0]["summary"], "筛选反馈接口返回 404")
        self.assertEqual(mine["summary"]["mine"], 1)

        all_records = list_support_feedback(self.db, admin, current=1, page_size=200, scope="all")
        self.assertEqual(all_records["total"], 2)

        handled = update_support_feedback(
            self.db,
            admin,
            created["id"],
            SupportFeedbackUpdateRequest(status="handled", adminNote="已修复"),
        )
        self.assertEqual(handled["status"], "handled")
        self.assertEqual(handled["adminNote"], "已修复")
        self.assertTrue(handled["handledAt"])

        deleted = delete_support_feedback(self.db, admin, created["id"])
        self.assertTrue(deleted["success"])
        self.assertEqual(list_support_feedback(self.db, admin, scope="all")["total"], 1)

    def test_non_admin_cannot_update_feedback_status(self):
        """
        普通用户不能把自己的反馈标记为已处理。

        反馈状态是客服/管理员处理结果，不是用户侧可编辑字段；否则运营台会失去真实待处理队列。

        @param: 无；先由普通用户创建反馈，再尝试更新状态。
        @return: None；服务抛出权限异常时通过。
        @raises HTTPException: 被测服务按预期拒绝普通用户更新状态。
        """
        created = create_support_feedback(
            self.db,
            DummyAuthUser("alice"),
            SupportFeedbackCreateRequest(type="其他建议", summary="请帮忙处理"),
        )

        with self.assertRaises(HTTPException):
            update_support_feedback(
                self.db,
                DummyAuthUser("alice"),
                created["id"],
                SupportFeedbackUpdateRequest(status="handled"),
            )


if __name__ == "__main__":
    unittest.main()
