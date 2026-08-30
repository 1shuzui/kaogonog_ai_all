"""真实医疗卫生题库资产同步、定向筛选和正式套题接口回归。"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.entities import Question
from app.services import question_service
from app.services.question_service import (
    _choose_targeted_bank_questions,
    get_question,
    get_full_exam_suite_questions,
    list_full_exam_suites,
    sync_curated_question_assets,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDICAL_ASSET_ROOT = REPO_ROOT / "ai_gongwu_backend" / "assets" / "questions"


def _medical_asset_ids() -> set[str]:
    ids: set[str] = set()
    for profile in ("medical_general", "shandong_medical", "jiangsu_medical"):
        for path in sorted((MEDICAL_ASSET_ROOT / f"generated_{profile}").glob("*.json")):
            ids.add(str(json.loads(path.read_text(encoding="utf-8"))["id"]))
    return ids


class TestMedicalQuestionBankAsset:
    """使用真实生成 JSON 验证后端不会按同题干错误覆盖稳定源题 ID。"""

    @classmethod
    def setup_class(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        # 仅建立题目表；完整 MySQL 元数据包含 SQLite 不支持的 MySQL collation。
        Question.__table__.create(cls.engine)
        cls.session = sessionmaker(bind=cls.engine)()
        question_service._question_pick_cache.clear()
        question_service._full_exam_suite_cache.clear()
        cls.sync_result = sync_curated_question_assets(cls.session)

    @classmethod
    def teardown_class(cls):
        cls.session.close()
        cls.engine.dispose()

    def test_all_medical_source_ids_survive_curated_sync(self):
        expected_ids = _medical_asset_ids()
        actual_ids = {
            row.id
            for row in self.session.query(Question).all()
            if row.id in expected_ids
        }
        assert len(expected_ids) == 546
        assert actual_ids == expected_ids

        general = self.session.get(Question, "YL-综合-059")
        shandong = self.session.get(Question, "SD-MED-SET125-01")
        assert general is not None and shandong is not None
        assert general.province == "national"
        assert shandong.province == "shandong"
        general_payload = get_question(self.session, "YL-综合-059")
        assert general_payload["examCategory"] == "事业单位考试"
        assert general_payload["reviewReason"] == ""

    def test_medical_portal_and_position_filters_use_real_metadata(self):
        shandong = _choose_targeted_bank_questions(
            self.session,
            province="shandong",
            position="medical",
            count=5,
            target_filters={
                "portalTag": "医疗卫生面试",
                "positionType": "医师岗",
                "examCategory": "事业单位考试",
                "examSubcategory": "山东省",
            },
        )
        assert shandong
        assert all(item["id"].startswith("SD-MED-") for item in shandong)
        assert all(item["positionType"] == "医师岗" for item in shandong)

        general = _choose_targeted_bank_questions(
            self.session,
            province="national",
            position="medical",
            count=5,
            target_filters={
                "portalTag": "医疗卫生面试",
                "positionTags": ["medical"],
                "examCategory": "事业单位考试",
                "examSubcategory": "通用医疗卫生题库",
            },
        )
        assert general
        assert all(item["id"].startswith("YL-") for item in general)

    def test_general_batch_is_not_a_formal_suite_and_regional_suite_has_appearance_metadata(self):
        shandong = list_full_exam_suites(
            self.session,
            examCategory="事业单位考试",
            province="shandong",
            examSubcategory="山东省",
        )
        jiangsu = list_full_exam_suites(
            self.session,
            examCategory="事业单位考试",
            province="jiangsu",
            examSubcategory="江苏省",
        )
        general = list_full_exam_suites(
            self.session,
            examCategory="事业单位考试",
            province="national",
            examSubcategory="通用医疗卫生题库",
        )

        assert shandong["total"] > 0
        assert jiangsu["total"] > 0
        assert general["total"] == 0
        suite = shandong["list"][0]
        assert suite["questionCount"] >= 2
        assert suite["appearanceScore"] == 5.0
        assert suite["appearanceScoreScope"] == "suite"
        assert suite["hasAppearanceScore"] is True
        assert "冲突" not in suite["scoreCalculationNote"]

        detail = get_full_exam_suite_questions(self.session, suite["id"])
        assert len(detail["questions"]) == suite["questionCount"]
        assert [item["questionNo"] for item in detail["questions"]] == list(
            range(1, suite["questionCount"] + 1)
        )
