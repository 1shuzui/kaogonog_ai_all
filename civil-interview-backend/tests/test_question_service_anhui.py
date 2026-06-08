"""
这个测试文件守住 `test_question_service_anhui` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import _normalize_json_payload, list_questions


class TestAnhuiQuestionImport(unittest.TestCase):
    """
    TestAnhuiQuestionImport 作为公共类型保留，是为了让调用方共享同一套业务语义和数据边界。

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
        tearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.db.close()
        self.engine.dispose()

    def test_anhui_assets_normalize_to_code(self):
        """
        test_anhui_assets_normalize_to_code 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        items = _normalize_json_payload([
            {"id": "raw_ah", "province": "安徽", "question": "安徽事业单位题目"},
            {"id": "raw_ah_fire", "province": "安徽消防", "question": "安徽消防救援题目"},
        ])

        self.assertEqual([item["province"] for item in items], ["anhui", "anhui"])

    def test_anhui_code_filter_returns_all_anhui_rows(self):
        """
        test_anhui_code_filter_returns_all_anhui_rows 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块记录曾经踩过的业务边界，注释说明为什么这些场景必须防回归。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        result = list_questions(self.db, province="anhui", page_size=20)

        self.assertEqual({item["id"] for item in result["list"]}, {"ah_1", "ah_fire_1"})


if __name__ == "__main__":
    unittest.main()
