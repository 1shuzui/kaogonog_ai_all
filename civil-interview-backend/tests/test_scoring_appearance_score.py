"""默认仪态分与实际仪态分替换逻辑的回归测试。"""

from app.models.entities import Question
from app.services.scoring_service import _decorate_result


def test_default_appearance_is_not_double_counted_and_actual_replaces_it():
    question = Question(
        stem="医疗岗位题干",
        scoring_points=[{"name": "内容", "score": 95}],
        keywords={
            "scoring": [],
            "deducting": [],
            "bonus": [],
            "_meta": {
                "hasAppearanceScore": True,
                "questionScore": 95,
                "appearanceScore": 5,
                "appearanceScoreMax": 5,
                "appearanceScoreSource": "profile_default",
                "appearanceScoreScope": "question",
                "effectiveFullScore": 100,
                "scoreCalculationNote": "仪态分已按默认值计入。",
            },
        },
    )
    initial = _decorate_result(
        question,
        "我会结合岗位实际说明处置方案。",
        {"totalScore": 80, "maxScore": 100, "dimensions": [{"name": "内容", "score": 80}]},
    )
    repeated = _decorate_result(question, "", initial)
    actual = _decorate_result(
        question,
        "",
        {**repeated, "appearanceScore": 3, "appearanceScoreSource": "actual"},
    )

    assert initial["contentScore"] == 76.0
    assert initial["appearanceScore"] == 5.0
    assert initial["totalScore"] == 81.0
    assert repeated["totalScore"] == 81.0
    assert repeated["appearanceScore"] == 5.0
    assert actual["contentScore"] == 76.0
    assert actual["appearanceScore"] == 3.0
    assert actual["appearanceScoreSource"] == "actual"
    assert actual["totalScore"] == 79.0
