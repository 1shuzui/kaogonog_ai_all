import io
import json
import unittest

import openpyxl
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import Question
from app.services.question_service import import_questions


class QuestionImportTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_import_questions_accepts_json_payload(self):
        payload = [
            {
                "id": "JS-IMPORT-JSON-01",
                "stem": "请谈谈如何做好基层治理中的群众沟通。",
                "province": "江苏",
                "dimension": "practical",
                "scoringPoints": [{"content": "群众立场清晰", "score": 8}],
                "keywords": {"scoring": ["群众沟通"], "deducting": [], "bonus": ["闭环办理"]},
                "tags": ["江苏事业单位"],
            }
        ]

        result = import_questions(self.db, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "questions.json")
        question = self.db.query(Question).filter(Question.id == "JS-IMPORT-JSON-01").first()

        self.assertEqual(result, {"imported": 1, "failed": 0, "filename": "questions.json"})
        self.assertIsNotNone(question)
        self.assertEqual(question.province, "jiangsu")
        self.assertEqual(question.scoring_points[0]["content"], "群众立场清晰")
        self.assertIn("群众沟通", question.keywords["scoring"])
        self.assertEqual(question.keywords["_meta"]["source"], "imported_file")
        self.assertEqual(question.keywords["_meta"]["categoryReviewStatus"], "needs_review")
        self.assertGreaterEqual(question.keywords["_meta"]["categoryConfidence"], 0)

    def test_import_questions_accepts_xlsx_payload(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["题干", "所属维度", "省份", "准备时间", "作答时间", "采分点", "得分关键词", "扣分关键词", "加分关键词"])
        sheet.append([
            "领导安排你负责一次安全生产专项整治，你怎么开展？",
            "practical",
            "江苏",
            120,
            240,
            json.dumps([{"content": "排查闭环", "score": 10}], ensure_ascii=False),
            json.dumps(["安全生产", "闭环整改"], ensure_ascii=False),
            "空泛,推诿",
            "分类整治",
        ])
        buffer = io.BytesIO()
        workbook.save(buffer)

        result = import_questions(self.db, buffer.getvalue(), "questions.xlsx")
        question = self.db.query(Question).filter(Question.stem.like("%安全生产专项整治%")).first()

        self.assertEqual(result, {"imported": 1, "failed": 0, "filename": "questions.xlsx"})
        self.assertIsNotNone(question)
        self.assertEqual(question.province, "jiangsu")
        self.assertEqual(question.prep_time, 120)
        self.assertEqual(question.answer_time, 240)
        self.assertEqual(question.scoring_points[0]["content"], "排查闭环")
        self.assertIn("安全生产", question.keywords["scoring"])
        self.assertIn("空泛", question.keywords["deducting"])
        self.assertIn("分类整治", question.keywords["bonus"])
        self.assertEqual(question.keywords["_meta"]["categoryReviewStatus"], "needs_review")

    def test_import_questions_rejects_xls_payload(self):
        with self.assertRaises(HTTPException) as context:
            import_questions(self.db, b"not-an-xlsx", "questions.xls")

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn(".json 或 .xlsx", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
