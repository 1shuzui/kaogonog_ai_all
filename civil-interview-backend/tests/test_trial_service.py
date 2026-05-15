import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.access import TRIAL_QUESTION_ID
from app.db.session import Base
from app.models.entities import Question
from app.services.trial_service import _pick_trial_question


class TestTrialService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_question(self, question_id, province="national", tags=None, source=""):
        keywords = {"scoring": [], "deducting": [], "bonus": []}
        meta = {}
        if tags is not None:
            meta["tags"] = tags
        if source:
            meta["source"] = source
        if meta:
            keywords["_meta"] = meta
        self.db.add(
            Question(
                id=question_id,
                stem=f"{question_id} stem",
                dimension="analysis",
                province=province,
                keywords=keywords,
                created_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

    def test_prefers_fixed_national_trial_question(self):
        self.add_question("js_trial", province="jiangsu", tags=["trial"])
        self.add_question(TRIAL_QUESTION_ID, province="national")

        self.assertEqual(_pick_trial_question(self.db).id, TRIAL_QUESTION_ID)

    def test_falls_back_only_within_national_pool(self):
        self.add_question("js_trial", province="jiangsu", tags=["trial"])
        self.add_question("q900", province="national", tags=["trial"])

        self.assertEqual(_pick_trial_question(self.db).id, "q900")


if __name__ == "__main__":
    unittest.main()
