import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import list_questions


class TestJiangsuQuestionFiltering(unittest.TestCase):
    def setUp(self):
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
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_jiangsu_position_filter_prefers_explicit_position_tags(self):
        a_result = list_questions(self.db, province="jiangsu", position="jiangsu_a", page_size=20)
        b_result = list_questions(self.db, province="jiangsu", position="jiangsu_b", page_size=20)
        d_result = list_questions(self.db, province="jiangsu", position="jiangsu_d", page_size=20)

        self.assertEqual([item["id"] for item in a_result["list"]], ["js_a_1"])
        self.assertEqual([item["id"] for item in b_result["list"]], ["js_b_1"])
        self.assertEqual(d_result["list"], [])


if __name__ == "__main__":
    unittest.main()
