"""
江苏题库测试守住事业单位岗位筛选和年份兜底提取。

江苏事业单位统考首页只展示岗位名称，不再把 A/B/C/D/E 当作用户可见分类；同时题号或考试日期里带年份的题目必须能被年份筛选命中。
这些用例防止题库展示回到“省份、岗位、题型混在一起”的旧口径。

@param: 无；setUp 写入江苏事业单位代表题和日期字段。
@return: 无直接返回；断言通过表示岗位和年份筛选仍符合当前分类规则。
@raises ImportError: 题库服务、ORM 模型或数据库依赖缺失时会失败。
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import list_questions


class TestJiangsuQuestionFiltering(unittest.TestCase):
    """
    江苏题库筛选用例集合，确认岗位标签和年份来源不会回到旧分类口径。

    江苏事业单位入口用户侧隐藏 A/B/C/D/E 文案，但内部仍需要用 positionTags 精准筛题；
    同时年份可能来自题号、套题名或 examDate，不能只看单一字段。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 江苏岗位或年份筛选口径退化时由断言报告。
    """
    def setUp(self):
        """
        准备江苏岗位标签题和一条只靠套题日期识别年份的事业单位题。

        用户侧已经不展示 A/B/C/D/E，但内部筛选还要靠旧 key 命中真实题；
        年份筛选也要覆盖 `examDate`，否则类似连云港 2025 真题会在年份下拉里消失。

        @param: 无；由 unittest 在每个用例前调用。
        @return: None；江苏代表题写入内存数据库。
        @raises AssertionError: 测试数据无法提交或题目元数据不兼容时由后续断言暴露。
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
        释放江苏题库筛选用例的数据库会话。

        岗位和年份筛选都依赖同一张 questions 表；每个用例独立清理可以避免旧题干影响新断言。

        @param: 无；由 unittest 在每个用例后调用。
        @return: None；数据库会话和引擎被释放。
        @raises: 不主动抛出业务异常；底层连接关闭异常会按测试失败暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_jiangsu_position_filter_prefers_explicit_position_tags(self):
        """
        江苏岗位筛选优先使用显式 positionTags。

        题干或维度里可能出现相似词，不能靠关键词猜岗位；显式标签可以避免 A/B 岗位互串，也能让不存在的 D 岗返回空。

        @param: 无；使用 setUp 中的 A/B 岗位题和一条无岗位标签题。
        @return: None；A/B 各自只命中自己的题，D 岗为空时通过。
        @raises AssertionError: 岗位标签筛选串题或无题岗位返回伪数据时失败。
        """
        a_result = list_questions(self.db, province="jiangsu", position="jiangsu_a", page_size=20)
        b_result = list_questions(self.db, province="jiangsu", position="jiangsu_b", page_size=20)
        d_result = list_questions(self.db, province="jiangsu", position="jiangsu_d", page_size=20)

        self.assertEqual([item["id"] for item in a_result["list"]], ["js_a_1"])
        self.assertEqual([item["id"] for item in b_result["list"]], ["js_b_1"])
        self.assertEqual(d_result["list"], [])

    def test_year_filter_falls_back_to_exam_date(self):
        """
        年份筛选必须能从套题考试日期兜底提取年份。

        导入资产里不一定有显式 year 字段；如果只查题号或固定 year 列，
        `JS-LYG-LYQ20250705-01` 这类真题会在 2025 年筛选中漏掉。

        @param: 无；使用 setUp 中的连云港事业单位题。
        @return: None；年份筛选命中该题并返回 `["2025"]` 时通过。
        @raises AssertionError: 年份兜底提取或返回字段格式退化时失败。
        """
        result = list_questions(self.db, province="jiangsu", year="2025", page_size=20)

        self.assertEqual([item["id"] for item in result["list"]], ["JS-LYG-LYQ20250705-01"])
        self.assertEqual(result["list"][0]["year"], ["2025"])


if __name__ == "__main__":
    unittest.main()
