"""
这个测试文件守住 `test_question_service_jiangsu` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import list_questions


class TestJiangsuQuestionFiltering(unittest.TestCase):
    """
    TestJiangsuQuestionFiltering 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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
            Question(
                id="js_a_1",
                stem="江苏基层综合管理岗题目",
                dimension="analysis",
                province="jiangsu",
                scoring_points=[{"content": "分析到位", "score": 10}],
                keywords={"scoring": [], "deducting": [], "bonus": [], "_meta": {"positionTags": ["jiangsu_a"]}},
            ),
            Question(
                id="js_b_1",
                stem="江苏社会科学专技岗题目",
                dimension="legal",
                province="jiangsu",
                scoring_points=[{"content": "依法分析", "score": 10}],
                keywords={"scoring": [], "deducting": [], "bonus": [], "_meta": {"positionTags": ["jiangsu_b"]}},
            ),
            Question(
                id="JS-LYG-LYQ20250705-01",
                stem="连云港连云区事业单位题目",
                dimension="analysis",
                province="jiangsu",
                scoring_points=[{"content": "分析到位", "score": 10}],
                keywords={
                    "scoring": [],
                    "deducting": [],
                    "bonus": [],
                    "_meta": {
                        "suiteName": "2025年7月5日江苏省连云港市连云区事业单位面试题",
                        "examDate": "2025-07-05",
                    },
                },
            ),
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

    def test_jiangsu_position_filter_prefers_explicit_position_tags(self):
        """
        test_jiangsu_position_filter_prefers_explicit_position_tags 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        a_result = list_questions(self.db, province="jiangsu", position="jiangsu_a", page_size=20)
        b_result = list_questions(self.db, province="jiangsu", position="jiangsu_b", page_size=20)
        d_result = list_questions(self.db, province="jiangsu", position="jiangsu_d", page_size=20)

        self.assertEqual([item["id"] for item in a_result["list"]], ["js_a_1"])
        self.assertEqual([item["id"] for item in b_result["list"]], ["js_b_1"])
        self.assertEqual(d_result["list"], [])

    def test_year_filter_falls_back_to_exam_date(self):
        """
        test_year_filter_falls_back_to_exam_date 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        result = list_questions(self.db, province="jiangsu", year="2025", page_size=20)

        self.assertEqual([item["id"] for item in result["list"]], ["JS-LYG-LYQ20250705-01"])
        self.assertEqual(result["list"][0]["year"], ["2025"])


if __name__ == "__main__":
    unittest.main()
