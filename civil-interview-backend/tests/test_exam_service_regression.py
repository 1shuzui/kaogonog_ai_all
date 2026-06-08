"""
这个测试文件守住 `test_exam_service_regression` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.services.exam_service import complete_exam


class TestExamServiceRegression(unittest.TestCase):
    """
    TestExamServiceRegression 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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

        now = datetime.now(timezone.utc)
        self.db.add(
            Question(
                id="q_complete_1",
                stem="请谈谈基层治理中的沟通协调。",
                dimension="analysis",
                province="jiangsu",
            )
        )
        self.db.add(
            Exam(
                id="exam_complete_1",
                user_id="tester",
                question_ids=["q_complete_1"],
                status="in_progress",
                start_time=now,
            )
        )
        self.db.add(
            ExamAnswer(
                exam_id="exam_complete_1",
                question_id="q_complete_1",
                transcript="作答内容",
                score_result={
                    "totalScore": 82.5,
                    "dimensions": [{"name": "综合分析", "score": 16.5, "maxScore": 20}],
                },
                answered_at=now,
            )
        )
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

    def test_complete_exam_is_idempotent_for_repeated_submit(self):
        """
        test_complete_exam_is_idempotent_for_repeated_submit 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        first = complete_exam(self.db, "exam_complete_1")
        second = complete_exam(self.db, "exam_complete_1")
        records = self.db.query(HistoryRecord).filter(HistoryRecord.exam_id == "exam_complete_1").all()

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(len(records), 1)
        self.assertEqual(second["finalScore"], 82.5)
        self.assertEqual(second["questionCount"], 1)


if __name__ == "__main__":
    unittest.main()
