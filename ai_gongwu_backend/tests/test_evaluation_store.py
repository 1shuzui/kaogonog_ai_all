"""测评落库测试。"""

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.entities import Base
from app.models.schemas import EvaluationResult
from app.services.evaluation_store import EvaluationStore


class EvaluationStoreTestCase(unittest.TestCase):
    """验证测评记录能够正常写入和读取。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
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
        self.temp_dir.cleanup()

    def test_save_and_query_record(self):
        final_result = EvaluationResult(
            question_id="HN-LX-20200606-01",
            question_type="综合分析",
            transcript="考生作答内容",
            source="text",
            source_filename="26分.txt",
            visual_observation=None,
            dimension_scores={"现象解读": 6.0},
            deduction_details=["未充分结合岗位"],
            bonus_details=["结构较完整"],
            evidence_quotes=["考生作答"],
            rationale="整体作答较完整。",
            total_score=20.0,
            matched_keywords={"strong": ["形式主义"]},
            validation_notes=["模型未提供足够证据。"],
        )

        enriched = self.store.save_evaluation(
            question_id="HN-LX-20200606-01",
            question_type="综合分析",
            source="text",
            source_filename="26分.txt",
            transcript="考生作答内容",
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


if __name__ == "__main__":
    unittest.main()
