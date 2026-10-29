"""Real queries and HTTP contracts against an isolated bank; never calls a model."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.targeted_performance_routes import router
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.entities import Exam, ExamAnswer, Question
from app.schemas.common import AuthUser, ExamStartRequest
from app.services.exam_service import start_exam

TARGET = {"province": "jiangsu", "examCategory": "事业单位考试", "examTrack": "medical",
          "examSubcategory": "江苏省", "positionType": "护理岗", "year": ["2025", "2026"]}


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    for table in (Question.__table__, Exam.__table__, ExamAnswer.__table__):
        table.create(engine)
    with Session(engine) as db:
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: AuthUser(username="alice", permissions={"canAccessPremiumModules": True})
        with TestClient(app) as client:
            yield db, app, client
    engine.dispose()


def question(db, key, *, kind="综合分析", province="jiangsu", **meta):
    q = Question(id=key, stem="验收题", province=province, dimension="analysis", keywords={"_meta": {
        "examCategory": "事业单位考试", "examSubcategory": "江苏省", "positionType": "护理岗",
        "portalTags": ["医疗卫生面试"], "year": "2026", "questionTypeCategory": kind, **meta}})
    db.add(q)
    db.flush()
    return q


def answer(db, key, score=80, *, username="alice", days=0, result=None, text="这是我的真实作答", media=None):
    exam = Exam(id=f"e{db.query(Exam).count()}", user_id=username, question_ids=[key], status="in_progress")
    db.add(exam)
    db.flush()
    row = ExamAnswer(exam_id=exam.id, question_id=key, transcript=text,
                     score_result=result if result is not None else {"totalScore": score, "maxScore": 100, "scoringMode": "llm"},
                     media_record=media or {}, answered_at=datetime.now(timezone.utc) - timedelta(days=days))
    db.add(row)
    db.commit()
    return row


def post(client, path="performance", **payload):
    response = client.post('/targeted/' + path, json={"target": TARGET, **payload})
    assert response.status_code == 200, response.text
    return response.json()


def type_row(report, kind="综合分析"):
    return next(row for row in report["questionTypes"] if row["questionType"] == kind)


def test_owned_scope_full_history_latest_valid_and_threshold_independence(env):
    db, _, client = env
    for i in range(5):
        question(db, str(i), year="2025" if i % 2 else "2026")
        answer(db, str(i), 70)
        answer(db, str(i), 100, username="bob")
    answer(db, "0", 20)  # latest valid, not highest
    answer(db, "0", result={"scoringMode": "conservative", "totalScore": 0, "maxScore": 100})
    question(db, "doctor", positionType="医师岗")
    answer(db, "doctor", 100)
    question(db, "other-province", province="anhui")
    answer(db, "other-province", 100)
    report = post(client)
    row = type_row(report)
    assert (row["sampleCount"], row["averagePercent"], row["label"]) == (5, 60, "需巩固")
    assert report["summary"]["excluded"]["technical_failure"] == 1
    details = post(client, "performance/answers", questionType="综合分析", recordFilter="low_score")
    assert [r["questionId"] for r in details["list"]] == ["0"]
    assert details["report"]["analysisRevision"] == report["analysisRevision"]
    # No review/preferences table even exists: personal thresholds and tombstones
    # cannot be read accidentally by this projection.


def test_newness_uses_all_history_and_actual_submission(env):
    db, _, client = env
    for key in ("old", "pending", "failed", "viewed", "skipped", "other-account"):
        question(db, key)
    answer(db, "old", days=45)
    answer(db, "pending", result={}, text="", media={"fileUrl": "/private/audio"})
    answer(db, "failed", result={"error": "technical"})
    answer(db, "skipped", result={"skipReason": "user_confirmed_skip"}, text="")
    answer(db, "other-account", username="bob")
    db.add(Exam(id="view", user_id="alice", question_ids=["viewed"]))
    db.commit()
    selected = post(client, "practice-selections", questionType="综合分析", count=5)
    assert set(selected["questionIds"]) == {"viewed", "skipped", "other-account"}
    assert (selected["actualCount"], selected["reason"]) == (3, "insufficient")
    assert type_row(post(client))["sampleCount"] == 0
    assert type_row(post(client, period="all"))["sampleCount"] == 1


def test_preselection_revalidated_before_start_and_legacy_start_preserved(env):
    db, _, client = env
    question(db, "new")
    selected = post(client, "practice-selections", questionType="综合分析")
    answer(db, "new")
    request = ExamStartRequest(questionIds=selected["questionIds"], practiceMode="targeted", targetedContext=selected["targetedContext"])
    before = db.query(Exam).count()
    with pytest.raises(HTTPException) as error:
        start_exam(db, request, "alice")
    assert error.value.status_code == 409
    assert db.query(Exam).count() == before
    assert start_exam(db, ExamStartRequest(questionIds=["new"]), "alice")["questionIds"] == ["new"]


def test_repractice_replaces_sample_and_low_independent_of_type_label(env):
    db, _, client = env
    for i, score in enumerate([10, 100, 100, 100, 100]):
        question(db, str(i))
        answer(db, str(i), score)
    assert type_row(post(client))["status"] == "strong"
    selection = post(client, "practice-selections", questionType="综合分析", mode="low_score")
    assert selection["questionIds"] == ["0"]
    exam = start_exam(db, ExamStartRequest(questionIds=["0"], practiceMode="targeted", targetedContext=selection["targetedContext"]), "alice")
    assert exam["questionIds"] == ["0"]
    old = post(client)
    answer(db, "0", 90)
    latest = post(client, "performance/answers", questionType="综合分析", analysisRevision=old["analysisRevision"])
    assert latest["dataChanged"] is True
    assert type_row(latest["report"])["sampleCount"] == 5
    assert post(client, "practice-selections", questionType="综合分析", mode="low_score")["actualCount"] == 0


def test_no_1500_cutoff_no_cross_track_padding_and_no_negative_role(env):
    db, _, client = env
    for i in range(1501):
        question(db, f"a{i:04}", positionType="医师岗")
    question(db, "z-match")
    question(db, "z-negative", sourceTitleRaw="江苏事业单位面试题（非护理岗）")
    question(db, "z-institution", portalTags=[], positionType="综合岗")
    db.commit()
    selected = post(client, "practice-selections", questionType="综合分析", count=5)
    assert selected["questionIds"] == ["z-match"]
    assert selected["actualCount"] == 1


def test_content_scores_pending_zero_unknown_and_reference_coaching(env):
    db, _, client = env
    question(db, "zero")
    answer(db, "zero", 0)
    question(db, "content")
    answer(db, "content", result={"contentScore": 76, "contentMaxScore": 95, "appearanceScore": 5,
                                    "totalScore": 81, "maxScore": 100,
                                    "answerImprovementSuggestion": {"source": "reference"}})
    question(db, "unknown", kind="尚未确认题型")
    answer(db, "unknown", 100)
    details = post(client, "performance/answers", questionType="综合分析", pageSize=1)
    assert details["total"] == 2
    assert type_row(details["report"])["averagePercent"] == 40
    assert details["report"]["summary"]["excluded"]["unclassified"] == 1
    assert details["list"][0]["score"] == 81


def test_api_access_and_invalid_parameters(env):
    _, app, client = env
    for payload in ({"period": "yesterday"}, {"questionType": "wrong"}, {"count": 10}):
        response = client.post('/targeted/practice-selections', json={"target": TARGET, "questionType": "综合分析", **payload})
        assert response.status_code == 422
    app.dependency_overrides[get_current_user] = lambda: AuthUser(username="unpaid")
    for path in ("performance", "performance/answers", "practice-selections"):
        response = client.post('/targeted/' + path, json={"target": TARGET, "questionType": "综合分析"})
        assert response.status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.post('/targeted/performance', json={"target": TARGET}).status_code == 401


def test_broad_tags_do_not_override_narrow_role_and_missing_questions_are_explicit(env):
    db, _, client = env
    question(db, "doctor", positionType="医师岗", positionTags=["medical"])
    question(db, "nurse", positionTags=["medical"])
    answer(db, "removed")
    selected = post(client, "practice-selections", target={**TARGET, "positionTags": ["medical"]}, questionType="综合分析")
    assert selected["questionIds"] == ["nurse"]
    report = post(client)
    assert report["summary"]["sampleCount"] == 0
    assert report["summary"]["unattributedCount"] == 1
