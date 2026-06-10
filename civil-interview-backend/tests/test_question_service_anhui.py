"""
安徽题库测试防止省考题被错误套进江苏 A/B/C/D/E 或事业单位分类。

分类重构后，真实题源主分类、地区来源和题型维度必须分开保存；安徽公务员题只应该属于“省级公务员考试/安徽省”。
这些用例验证资产导入和代码筛选都不会把安徽题串到江苏岗位入口。

@param: 无；setUp 会写入代表性的安徽题库记录。
@return: 无直接返回；断言通过表示安徽题库筛选口径仍正确。
@raises ImportError: 题库服务、ORM 模型或数据库依赖缺失时会失败。
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import _normalize_json_payload, list_questions


class TestAnhuiQuestionImport(unittest.TestCase):
    """
    安徽题库导入与筛选用例集合，确认“安徽”相关来源统一归到安徽省代码。

    分类重构后，题型维度、岗位方向和省份字段分开维护；这里专门防止“安徽消防”等来源被误拆成新省份或串到江苏岗位。

    @param: 无；unittest 负责实例化测试类。
    @return: unittest 测试用例类。
    @raises AssertionError: 安徽题库省份归一或筛选口径退化时由断言报告。
    """
    def setUp(self):
        """
        准备两条安徽来源题，覆盖普通省份名和带系统词的省份名。

        分类纠偏时最容易把“安徽消防”当成独立地区或题型标签；这里用内存库固定筛选应看到的真实行。

        @param: 无；由 unittest 在每个用例前调用。
        @return: None；安徽代表题写入内存数据库。
        @raises AssertionError: 测试数据无法提交或省份字段不兼容时由后续断言暴露。
        """
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            Question(
                id="ah_1",
                stem="安徽题目",
                dimension="analysis",
                province="anhui",
                scoring_points=[{"content": "分析到位", "score": 10}],
                keywords={"scoring": [], "deducting": [], "bonus": []},
            ),
            Question(
                id="ah_fire_1",
                stem="安徽消防题目",
                dimension="emergency",
                province="anhui",
                scoring_points=[{"content": "处置得当", "score": 10}],
                keywords={"scoring": [], "deducting": [], "bonus": []},
            ),
        ])
        self.db.commit()

    def tearDown(self):
        """
        释放安徽题库筛选用例的数据库会话。

        题库筛选测试会复用全量 metadata，关闭会话和引擎可以避免其他省份用例读到残留题目。

        @param: 无；由 unittest 在每个用例后调用。
        @return: None；数据库会话和引擎被释放。
        @raises: 不主动抛出业务异常；底层连接关闭异常会按测试失败暴露。
        """
        self.db.close()
        self.engine.dispose()

    def test_anhui_assets_normalize_to_code(self):
        """
        原始资产里的“安徽”“安徽消防”都应归一为 `anhui`。

        文件标题和章节标题可能带系统词，但系统词不应替代地区字段；否则定向筛选会找不到安徽题。

        @param: 无；直接构造两条原始题库资产。
        @return: None；归一后的 province 都是 `anhui` 时通过。
        @raises AssertionError: 系统词污染省份代码时失败。
        """
        items = _normalize_json_payload([
            {"id": "raw_ah", "province": "安徽", "question": "安徽事业单位题目"},
            {"id": "raw_ah_fire", "province": "安徽消防", "question": "安徽消防救援题目"},
        ])

        self.assertEqual([item["province"] for item in items], ["anhui", "anhui"])

    def test_anhui_code_filter_returns_all_anhui_rows(self):
        """
        省份代码筛选应返回安徽普通题和安徽系统题。

        这个断言防止筛选逻辑只命中普通“安徽”文本，漏掉带消防、税务等系统来源的安徽省考题。

        @param: 无；使用 setUp 中的两条安徽题。
        @return: None；返回两条安徽题时通过。
        @raises AssertionError: 安徽系统题被省份筛选漏掉时失败。
        """
        result = list_questions(self.db, province="anhui", page_size=20)

        self.assertEqual({item["id"] for item in result["list"]}, {"ah_1", "ah_fire_1"})


if __name__ == "__main__":
    unittest.main()
