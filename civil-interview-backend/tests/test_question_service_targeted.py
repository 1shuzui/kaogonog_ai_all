import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.schemas.common import QuestionUpdate
from app.services.question_service import _choose_targeted_bank_questions, _normalize_province, delete_question, update_question
from app.services.user_service import get_provinces
from app.core.ai import _to_simplified_chinese


def build_keywords(source="local_asset", position_tags=None):
    return {
        "scoring": [],
        "deducting": [],
        "bonus": [],
        "_meta": {
            "source": source,
            "sourceLabel": "本地真题" if source == "local_asset" else "手动题目",
            "positionTags": position_tags or [],
        },
    }


class TargetedQuestionServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all([
            Question(
                id="q_anhui_tax",
                stem="安徽税务系统题",
                dimension="analysis",
                province="anhui",
                keywords=build_keywords(position_tags=["tax"]),
            ),
            Question(
                id="q_anhui_general",
                stem="安徽通用题",
                dimension="practical",
                province="anhui",
                keywords=build_keywords(position_tags=[]),
            ),
            Question(
                id="q_national_tax",
                stem="国考税务系统题",
                dimension="analysis",
                province="national",
                keywords=build_keywords(position_tags=["tax"]),
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_targeted_questions_prioritize_selected_province_before_national_fallback(self):
        with patch("app.services.question_service.random.shuffle", lambda items: None):
            result = _choose_targeted_bank_questions(self.db, "anhui", "tax", 3)

        self.assertEqual([item["id"] for item in result], ["q_anhui_tax", "q_anhui_general", "q_national_tax"])
        self.assertFalse(result[0]["isProvinceFallback"])
        self.assertFalse(result[1]["isProvinceFallback"])
        self.assertTrue(result[2]["isProvinceFallback"])
        self.assertEqual(result[2]["requestedProvince"], "anhui")

    def test_province_alias_normalization_accepts_legacy_shaanxi_code(self):
        self.assertEqual(_normalize_province("shaanxi"), "shanxi")
        self.assertEqual(_normalize_province("陕西"), "shanxi")

    def test_province_api_contains_extended_supported_provinces(self):
        provinces = get_provinces()
        province_map = {item["code"]: item["name"] for item in provinces}

        self.assertEqual(province_map.get("national"), "国考")
        self.assertEqual(province_map.get("anhui"), "安徽")
        self.assertEqual(province_map.get("shanghai"), "上海")
        self.assertEqual(province_map.get("hebei"), "河北")
        self.assertEqual(province_map.get("fujian"), "福建")
        self.assertEqual(province_map.get("shanxi"), "陕西")

    def test_admin_service_can_update_and_delete_standard_bank_questions(self):
        data = QuestionUpdate(
            stem="更新后的标准题库题干",
            dimension="practical",
            province="jiangsu",
            prepTime=300,
            answerTime=900,
            scoringPoints=[{"content": "有明确执行步骤", "score": 10}],
            keywords={"scoring": ["执行"], "deducting": [], "bonus": []},
        )

        updated = update_question(self.db, "q_anhui_tax", data)
        self.assertEqual(updated["stem"], "更新后的标准题库题干")
        self.assertEqual(updated["questionSource"], "local_asset")

        result = delete_question(self.db, "q_anhui_tax")
        self.assertTrue(result["success"])
        self.assertIsNone(self.db.query(Question).filter(Question.id == "q_anhui_tax").first())

    def test_transcription_normalization_converts_common_traditional_text(self):
        text = _to_simplified_chinese("這個問題應該由相關部門協調處理，讓群眾滿意。")
        self.assertEqual(text, "这个问题应该由相关部门协调处理，让群众满意。")


if __name__ == "__main__":
    unittest.main()
