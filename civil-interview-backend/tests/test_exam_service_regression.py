"""
考试服务回归测试守住“重复提交不会重复扣时长或覆盖结果”的边界。

全真模拟和专项练习都可能因为网络抖动、用户连点或小程序重试而二次提交；后端必须把同一场考试的完成动作当作幂等操作，
否则历史记录、权益消耗和评分结果会互相打架。

@param: 无；测试库在 setUp 中创建题目、考试和答题记录。
@return: 无直接返回；断言通过表示考试完成流程仍可安全重试。
@raises ImportError: 考试服务、ORM 模型或数据库依赖缺失时会失败。
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
    考试完成回归用例集合，专门验证提交完成动作可以安全重试。

    小程序端可能因为网络重试或用户连点把同一场考试提交两次；服务层必须返回同一份完成结果，
    不能重复生成历史记录，也不能让第二次提交覆盖第一次的评分。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 考试完成幂等性、历史记录数量或分数字段退化时由断言报告。
    """
    def setUp(self):
        """
        准备一场已经有答题评分、但考试状态仍未完成的模拟考试。

        重复提交问题通常发生在“评分已经写入、完成接口还在重试”的中间态；
        这里把状态固定在 `in_progress`，才能验证服务层是否会复用既有评分并只生成一条历史记录。

        @param: 无；由 unittest 在每个用例前调用。
        @return: None；题目、考试和答题评分写入内存数据库。
        @raises AssertionError: 测试数据无法提交或考试关联字段不兼容时由后续断言暴露。
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
        释放考试完成幂等性用例的数据库会话。

        考试完成会写入历史记录；每个用例独立销毁内存库可以避免重复记录影响下一次断言。

        @param: 无；由 unittest 在每个用例后调用。
        @return: None；数据库会话和引擎被释放。
        @raises: 不主动抛出业务异常；底层连接关闭异常会按测试失败暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_complete_exam_is_idempotent_for_repeated_submit(self):
        """
        同一场考试重复完成时只能保留一条历史记录。

        这个用例防止二次提交把历史列表刷出重复记录，或把前一次评分结果重算成不同分数。

        @param: 无；使用 setUp 中已经准备好的考试和答题记录。
        @return: None；两次完成都成功且历史记录唯一时通过。
        @raises AssertionError: 重复提交产生多条历史记录或分数不一致时失败。
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
