"""医疗卫生三批题库的批次级验收与默认仪态分回归测试。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "ai_gongwu_backend" / "assets" / "questions"
MEDICAL_BATCHES = {
    "medical_general": (100, "全国", "通用医疗卫生题库", False),
    "shandong_medical": (259, "山东", "山东省", True),
    "jiangsu_medical": (187, "江苏", "江苏省", True),
}
REQUIRED_FIELDS = {
    "id",
    "type",
    "province",
    "fullScore",
    "question",
    "scoringPoints",
    "referenceAnswer",
    "examCategory",
    "examSubcategory",
    "portalTags",
    "displayPortals",
    "positionTags",
    "positionType",
    "interviewFormat",
    "questionTypeCategory",
    "suiteId",
    "suiteKey",
    "suiteName",
    "sourceDocument",
    "originFile",
    "sourceQuestionId",
    "questionNo",
    "questionScore",
    "appearanceScore",
    "appearanceScoreMax",
    "appearanceScoreSource",
    "appearanceScoreScope",
    "effectiveFullScore",
    "hasAppearanceScore",
    "hasCompleteSuiteLevel",
    "scoreCalculationNote",
    "reviewStatus",
    "reviewReason",
}


def load_batch(profile: str) -> list[dict]:
    directory = ASSET_ROOT / f"generated_{profile}"
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"), key=lambda path: path.name)
    ]


def test_medical_batches_have_expected_counts_and_contract():
    all_questions: list[dict] = []
    for profile, (expected_count, province, subcategory, complete) in MEDICAL_BATCHES.items():
        questions = load_batch(profile)
        assert len(questions) == expected_count
        all_questions.extend(questions)
        for question in questions:
            assert REQUIRED_FIELDS <= question.keys(), question["id"]
            assert question["province"] == province
            assert question["examCategory"] == "事业单位考试"
            assert question["examSubcategory"] == subcategory
            assert "医疗卫生面试" in question["portalTags"]
            assert "医疗卫生面试" in question["displayPortals"]
            assert "medical" in question["positionTags"]
            assert question["interviewFormat"] == "医疗卫生结构化面试"
            assert question["hasCompleteSuiteLevel"] is complete
            assert question["hasAppearanceScore"] is True
            assert question["appearanceScoreSource"] in {"source_explicit", "profile_default"}
            if question["appearanceScoreSource"] == "profile_default":
                assert question["appearanceScore"] == 5.0
                assert question["appearanceScoreMax"] == 5.0
            else:
                assert 0.0 < question["appearanceScore"] <= question["appearanceScoreMax"]
            assert question["effectiveFullScore"] == question["questionScore"] + question["appearanceScoreMax"]
            assert question["fullScore"] == question["effectiveFullScore"]
            assert question["reviewStatus"] != "待确认"
            assert "仪态" not in question["reviewReason"]
            assert not question["question"].startswith(("第一题：", "第1题："))

    assert len({question["id"] for question in all_questions}) == len(all_questions)
    assert any(question["questionScore"] == 95.0 for question in all_questions)


def test_medical_source_files_form_stable_suites_and_continuous_question_numbers():
    for profile in ("shandong_medical", "jiangsu_medical"):
        suites: dict[str, list[dict]] = defaultdict(list)
        for question in load_batch(profile):
            suites[question["suiteKey"]].append(question)

        for suite_key, questions in suites.items():
            assert len({question["originFile"] for question in questions}) == 1
            assert len({question["suiteId"] for question in questions}) == 1
            assert [
                question["questionNo"]
                for question in sorted(questions, key=lambda item: item["questionNo"])
            ] == list(range(1, len(questions) + 1)), suite_key
            if profile == "shandong_medical":
                assert suite_key.startswith("SD-MED-SET")
                assert all(question["id"].startswith(f"{suite_key}-") for question in questions)
            else:
                assert suite_key.startswith("JS-MED-SET")
                assert all(question["id"].startswith(f"{suite_key}-") for question in questions)

    jiangsu = load_batch("jiangsu_medical")
    assert len([question for question in jiangsu if question["suiteKey"] == "JS-MED-SET039"]) == 3
    assert len([question for question in jiangsu if question["suiteKey"] == "JS-MED-SET045"]) == 2
    assert all(question["suiteKey"] != "JS-MED-SET003" for question in jiangsu)


def test_suite_scoped_appearance_score_is_added_once():
    questions = load_batch("jiangsu_medical")
    suite_questions = [question for question in questions if question["suiteKey"] == "JS-MED-SET039"]
    assert suite_questions
    assert {question["appearanceScoreScope"] for question in suite_questions} == {"suite"}
    assert len({question["suiteTotalScore"] for question in suite_questions}) == 1
    assert suite_questions[0]["suiteTotalScore"] == sum(
        question["questionScore"] for question in suite_questions
    ) + 5.0
