"""
这个测试文件守住 `test_support_feedback_service` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    DummyAuthUser 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

    测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """
    def __init__(self, username="alice", is_admin=False):
        self.username = username
        self.isAdmin = is_admin


class SupportFeedbackServiceTestCase(unittest.TestCase):
    """
    SupportFeedbackServiceTestCase 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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
        self.db.add_all([
            User(username="alice", hashed_password="x"),
            User(username="bob", hashed_password="x"),
            User(username="admin", hashed_password="x"),
        ])
        self.db.commit()

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

    def test_support_routes_are_registered(self):
        """
        test_support_routes_are_registered 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        route_paths = {route.path for route in api_router.routes}

        self.assertIn("/support/feedback", route_paths)
        self.assertIn("/support/feedback/attachments", route_paths)
        self.assertIn("/support/feedback/{feedback_id}", route_paths)

    def test_feedback_create_list_update_delete_uses_database_records(self):
        """
        test_feedback_create_list_update_delete_uses_database_records 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
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
        test_non_admin_cannot_update_feedback_status 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises HTTPException: 请求参数、权限或数据状态不符合当前业务规则时抛出。
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
