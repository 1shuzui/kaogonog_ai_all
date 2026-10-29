from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.targeted_performance_rules import (
    classification, content_pair, dimension_rates, percent_text, question_type, window,
)


@pytest.mark.parametrize("score,expected", [
    ({"questionScore": 28.8, "questionMaxScore": 36}, (28.8, 36)),
    ({"totalScore": 0, "maxScore": 100}, (0, 100)),
    ({"contentScore": 76, "contentMaxScore": 95, "appearanceScore": 5, "maxScore": 100}, (76, 95)),
    ({"contentScore": 76, "appearanceScoreMax": 5, "maxScore": 100}, (76, 95)),
    ({"totalScore": 81, "appearanceScore": 5, "maxScore": 100}, None),
    ({"totalScore": 20}, None),
    ({"totalScore": True, "maxScore": 100}, None),
    ({"totalScore": float("nan"), "maxScore": 100}, None),
    ({"totalScore": -1, "maxScore": 100}, None),
    ({"totalScore": 101, "maxScore": 100}, None),
    ({"totalScore": 10, "maxScore": 0}, None),
])
def test_saved_content_denominator_is_required(score, expected):
    assert content_pair(score) == expected


def test_sample_threshold_and_boundaries():
    assert classification(None, 0)[0] == "unpracticed"
    assert classification(90, 4)[0] == "insufficient"
    assert classification(59.9999, 5)[0] == "weak"
    assert classification(60, 5)[0] == "developing"
    assert classification(80, 5)[0] == "strong"
    assert percent_text(59.9999) == "<60%"
    assert percent_text(79.9999) == "<80%"


def test_beijing_calendar_window_is_not_rolling_720_hours():
    now = datetime(2026, 10, 15, 17, 12, tzinfo=timezone.utc)
    start, end = window("recent30", now)
    assert start == datetime(2026, 9, 16, 16, tzinfo=timezone.utc)
    assert end == now
    assert window("all", now) == (None, now)


def test_unknown_type_and_missing_ability_are_not_invented():
    assert question_type(SimpleNamespace(keywords={}, dimension="practical")) is None
    assert question_type(SimpleNamespace(keywords={"_meta": {"questionTypeCategory": "组织管理"}}, dimension="practical")) == "组织管理"
    assert dimension_rates({"dimensions": [{"name": "逻辑结构", "score": 2}]}) == {}
    assert dimension_rates({"dimensions": [{"name": "逻辑结构", "score": 0, "maxScore": 15}]}) == {"逻辑结构": 0}
