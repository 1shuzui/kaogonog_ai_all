"""
这个测试文件守住 `test_question_bank` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import settings
from app.services.question_bank import QuestionBank, QuestionNotFoundError


class QuestionBankTestCase(unittest.TestCase):
    """
    验证题库加载与查询的基本行为。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    @classmethod
    def setUpClass(cls):
        # setUpClass 只在整个测试类开始前执行一次，适合做共享初始化。
        """
        setUpClass 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        cls.bank = QuestionBank(settings.QUESTION_DB_PATH)

    def test_get_existing_question(self):
        # 验证：一个真实存在的 question_id 应该能拿到题目对象。
        """
        test_get_existing_question 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        question = self.bank.get_question("HN-LX-20200606-01")
        self.assertEqual(question.id, "HN-LX-20200606-01")
        self.assertGreater(len(question.dimensions), 0)

    def test_imported_question_exposes_reference_metadata(self):
        # 验证：自动导入的湖南题库也能被题库服务正常读取。
        """
        test_imported_question_exposes_reference_metadata 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        question = self.bank.get_question("HN-20200816-01")
        self.assertEqual(question.sourceDocument, "湖南-税务系统补录-2020-816.doc")
        self.assertTrue(question.referenceAnswer)
        self.assertTrue(question.tags)
        self.assertEqual(len(question.regressionCases), 3)
        self.assertEqual(
            [case.label for case in question.regressionCases],
            ["文档高分基准答案", "程序化中档参考答案", "程序化低档参考答案"],
        )
        self.assertTrue(all(case.llmExpectedMin is not None for case in question.regressionCases))
        self.assertTrue(all(case.llmExpectedMax is not None for case in question.regressionCases))

    def test_imported_anhui_question_is_loadable(self):
        # 验证：新增的安徽自动题库也会被默认题库目录递归加载。
        """
        test_imported_anhui_question_is_loadable 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        question = self.bank.get_question("AHGWY-20201113PM-01")
        self.assertEqual(question.province, "安徽")
        self.assertEqual(question.sourceDocument, "2020-2025第二批次完全版.docx")
        self.assertTrue(question.tags)
        self.assertTrue(question.referenceAnswer)
        self.assertEqual(len(question.regressionCases), 3)

    def test_missing_question_raises(self):
        # 验证：不存在的题目应该抛出清晰异常，而不是返回 None 或直接崩溃。
        """
        test_missing_question_raises 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        with self.assertRaises(QuestionNotFoundError):
            self.bank.get_question("missing-id")

    def test_can_load_questions_from_directory(self):
        """
        test_can_load_questions_from_directory 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "q1.json").write_text(
                """
                {
                  "id": "Q1",
                  "type": "测试题",
                  "province": "河南",
                  "fullScore": 10,
                  "question": "问题1",
                  "dimensions": [{"name": "现象解读", "score": 10}]
                }
                """.strip(),
                encoding="utf-8",
            )
            nested_dir = temp_path / "nested"
            nested_dir.mkdir()
            (nested_dir / "q2.json").write_text(
                """
                {
                  "questions": [
                    {
                      "id": "Q2",
                      "type": "测试题",
                      "province": "河南",
                      "fullScore": 10,
                      "question": "问题2",
                      "dimensions": [{"name": "现象解读", "score": 10}]
                    }
                  ]
                }
                """.strip(),
                encoding="utf-8",
            )

            bank = QuestionBank(temp_path)
            self.assertEqual(bank.count, 2)
            self.assertEqual(bank.list_ids(), ["Q1", "Q2"])
            self.assertEqual(bank.get_question("Q2").question, "问题2")


if __name__ == "__main__":
    unittest.main()
