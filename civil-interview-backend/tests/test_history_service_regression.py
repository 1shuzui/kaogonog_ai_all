"""
历史服务测试确认评分落库后，首页、错题和历史页面能读到同一份结果。

评分链路会同时生成题目维度、能力维度、文字稿和建议，前端展示依赖的是持久化记录而不是当次内存返回值。
这里把完整分数写进数据库再通过接口读取，防止字段改名后页面只剩空态。

@param: 无；测试库在 setUp 中准备用户、题目和评分记录。
@return: 无直接返回；断言通过表示历史查询仍能读取已保存评分。
@raises ImportError: 历史服务、路由或 ORM 依赖缺失时会失败。
"""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.services.history_service import get_history_list, get_history_stats, get_history_trend


class TestHistoryServiceRegression(unittest.TestCase):
    """
    历史查询回归用例集合，确认评分持久化后能被列表、统计和趋势共同读取。

    前端首页、历史页和能力概览读取的是不同接口；字段变更时容易出现某个接口仍有数据、另一个接口变空态。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 历史列表、统计或趋势读取口径不一致时由断言报告。
    """
    def setUp(self):
        """
        为历史服务准备一套完整的“题目-考试-答题-历史快照”数据。

        历史接口不应该依赖考试完成时的内存返回，所以这里故意把评分结果和历史记录都写进数据库，
        用隔离库模拟用户刷新页面后的读取场景。

        @param: 无；由 unittest 在每个用例前调用。
        @return: None；测试数据写入内存数据库。
        @raises AssertionError: 测试数据无法提交或关系字段不兼容时由后续断言暴露。
        """
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        now = datetime.now(timezone.utc)
        question = Question(
            id="q_history_1",
            stem="请谈谈基层治理中的沟通协调。",
            dimension="analysis",
            province="national",
        )
        exam = Exam(
            id="exam_history_1",
            user_id="tester",
            question_ids=["q_history_1"],
            status="completed",
            start_time=now - timedelta(minutes=10),
            end_time=now,
        )
        answer = ExamAnswer(
            exam_id="exam_history_1",
            question_id="q_history_1",
            transcript="我的作答内容",
            score_result={
                "totalScore": 82.5,
                "maxScore": 100,
                "grade": "B",
                "dimensions": [{"name": "综合分析", "score": 16.5, "maxScore": 20}],
                "mediaRecord": {"fileUrl": "/uploads/demo.webm"},
            },
            answered_at=now,
        )
        record = HistoryRecord(
            exam_id="exam_history_1",
            username="tester",
            question_count=1,
            total_score=82.5,
            max_score=100,
            grade="B",
            province="national",
            dimensions=[{"name": "综合分析", "score": 16.5, "maxScore": 20}],
            completed_at=now,
        )

        self.db.add_all([question, exam, answer, record])
        self.db.commit()

    def tearDown(self):
        """
        关闭历史服务用例的内存数据库连接。

        这些用例会创建完整 SQLAlchemy metadata；每次释放连接可以避免表结构或会话缓存影响下一组回归。

        @param: 无；由 unittest 在每个用例后调用。
        @return: None；数据库会话和引擎被释放。
        @raises: 不主动抛出业务异常；底层连接关闭异常会按测试失败暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_history_endpoints_can_read_persisted_scores(self):
        """
        已落库的评分必须同时出现在历史列表、统计和趋势里。

        这条断言防止后端只修复某个页面接口，却遗漏首页趋势或平均分统计。

        @param: 无；使用 setUp 中准备的考试、答题和历史记录。
        @return: None；三类历史接口都读到同一分数时通过。
        @raises AssertionError: 任一历史接口漏读或分数不一致时失败。
        """
        listing = get_history_list(self.db, "tester", current=1, page_size=10)
        stats = get_history_stats(self.db, "tester")
        trend = get_history_trend(self.db, "tester", days=30)

        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["list"][0]["totalScore"], 82.5)
        self.assertEqual(listing["list"][0]["status"], "completed")
        self.assertEqual(stats["totalExams"], 1)
        self.assertEqual(stats["avgScore"], 82.5)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["score"], 82.5)


if __name__ == "__main__":
    unittest.main()
