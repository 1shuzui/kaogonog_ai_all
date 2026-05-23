import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import _normalize_json_payload, list_questions


class TestAnhuiQuestionImport(unittest.TestCase):
    def setUp(self):
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
        self.db.close()
        self.engine.dispose()

    def test_anhui_assets_normalize_to_code(self):
        items = _normalize_json_payload([
            {"id": "raw_ah", "province": "安徽", "question": "安徽事业单位题目"},
            {"id": "raw_ah_fire", "province": "安徽消防", "question": "安徽消防救援题目"},
        ])

        self.assertEqual([item["province"] for item in items], ["anhui", "anhui"])

    def test_anhui_code_filter_returns_all_anhui_rows(self):
        result = list_questions(self.db, province="anhui", page_size=20)

        self.assertEqual({item["id"] for item in result["list"]}, {"ah_1", "ah_fire_1"})


if __name__ == "__main__":
    unittest.main()
