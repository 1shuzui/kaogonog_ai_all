"""
这个测试文件守住 `test_evaluation_store` 对应的回归场景；它记录的是以前容易出错的业务边界，而不是普通示例代码。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
"""

import shutil
import unittest
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.entities import Base
from app.models.schemas import EvaluationResult
from app.services.evaluation_store import EvaluationStore


class EvaluationStoreTestCase(unittest.TestCase):
    """
    验证测评记录能够正常写入和读取。

    测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

    @param: 无；实例字段由 ORM、Pydantic 或测试夹具按声明式约定注入。
    @return: 返回可被调用方实例化或引用的公共类型。
    @raises: 类定义阶段不主动抛出业务异常；字段约束错误通常在实例化、校验或数据库提交时暴露。
    """

    def setUp(self):
        """
        setUp 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        self.temp_dir = Path.cwd() / "storage" / f"test_evaluation_store_{uuid.uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        database_path = self.temp_dir / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        self.session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        self.store = EvaluationStore(session_factory=self.session_factory)

    def tearDown(self):
        """
        tearDown 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_query_record(self):
        """
        test_save_and_query_record 保留为回归用例，是为了锁定曾经出现过的业务边界或集成风险。

        测试模块保留导入、评分和媒体链路的回归样例，注释说明为什么这些样例不能随意删减。

        @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
        @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
        @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
        """
        final_result = EvaluationResult(
            question_id="HN-LX-20200606-01",
            question_type="综合分析",
            transcript="考生作答内容",
            source="text",
            source_filename="26分.txt",
            duration_seconds=None,
            visual_observation=None,
            dimension_scores={"现象解读": 6.0},
            deduction_details=["未充分结合岗位"],
            bonus_details=["结构较完整"],
            evidence_quotes=["考生作答"],
            rationale="整体作答较完整。",
            total_score=20.0,
            matched_keywords={"strong": ["形式主义"]},
            speech_rate_chars_per_minute=None,
            speech_rate_level=None,
            speech_rate_advice="",
            answer_revision_suggestion="建议先压缩开头铺垫，再补一层岗位化落点。",
            validation_notes=["模型未提供足够证据。"],
        )

        enriched = self.store.save_evaluation(
            question_id="HN-LX-20200606-01",
            question_type="综合分析",
            source="text",
            source_filename="26分.txt",
            transcript="考生作答内容",
            duration_seconds=None,
            visual_observation=None,
            prompt_text="prompt",
            llm_provider="QWEN",
            llm_model_name="qwen3-coder-plus",
            raw_llm_content='{"total_score": 20}',
            raw_llm_payload={"total_score": 20},
            final_result=final_result,
        )

        self.assertIsNotNone(enriched.record_id)
        self.assertIsNotNone(enriched.evaluated_at)

        records = self.store.list_recent_records(limit=10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].question_id, "HN-LX-20200606-01")

        detail = self.store.get_record_detail(enriched.record_id)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail.final_result.record_id, enriched.record_id)
        self.assertEqual(detail.final_result.total_score, 20.0)
        self.assertEqual(detail.raw_llm_payload["total_score"], 20)
        self.assertEqual(detail.final_result.answer_revision_suggestion, "建议先压缩开头铺垫，再补一层岗位化落点。")


if __name__ == "__main__":
    unittest.main()
