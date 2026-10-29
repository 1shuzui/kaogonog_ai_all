"""Account-scoped threshold HTTP and historical-review regression coverage."""
from copy import deepcopy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.api.v1.routes.user_routes import router as user_router
from app.api.v1.routes.review_routes import router as review_router
from app.core.security import get_current_user
from app.db.session import Base, get_db
from app.models.entities import User, Question, Exam, ExamAnswer
from app.schemas.common import AuthUser


@pytest.fixture
def fixture():
    engine = create_engine('sqlite:///:memory:', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        metadata = {'wechatMiniProgram': {'openId': 'fixture-binding'}, 'billing': {'fixture': 'untouched'}, 'defaultPrepTime': 120}
        db.add_all([User(username='alice', hashed_password='x', preferences=metadata), User(username='bob', hashed_password='x')])
        scores = {'zero': (0, 100), 'below': (59, 100), 'boundary': (60, 100), 'between': (69, 100), 'new-boundary': (70, 100), 'scaled': (24, 40), 'content': (99, 100), 'pending': (None, 100), 'empty': (0, 100)}
        for qid in scores:
            db.add(Question(id=qid, stem='隔离测试题 ' + qid))
        db.add_all([Exam(id='alice-exam', user_id='alice', question_ids=list(scores)), Exam(id='bob-exam', user_id='bob', question_ids=['between'])])
        for qid, (score, maximum) in scores.items():
            result = {'totalScore': score, 'maxScore': maximum}
            if qid == 'content':
                result.update(questionScore=24, questionMaxScore=40)
            db.add(ExamAnswer(exam_id='alice-exam', question_id=qid, transcript='' if qid == 'empty' else '真实有效作答', score_result=result))
        db.add(ExamAnswer(exam_id='bob-exam', question_id='between', transcript='另一个账号的作答', score_result={'totalScore': 69, 'maxScore': 100}))
        db.commit()
        current = {'name': 'alice'}
        app = FastAPI()
        app.include_router(user_router)
        app.include_router(review_router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: AuthUser(username=current['name'])
        with TestClient(app) as client:
            yield db, client, current
    engine.dispose()


def prefs(client):
    response = client.get('/user/info')
    assert response.status_code == 200, response.text
    return response.json()['preferences']


def weak(client):
    response = client.get('/user/review-items?type=weak')
    assert response.status_code == 200, response.text
    return {row['questionId'] for row in response.json()['list']}


def test_threshold_refreshes_history_respects_boundaries_and_scoring_contract(fixture):
    db, client, _ = fixture
    before = [deepcopy(a.score_result) for a in db.query(ExamAnswer).order_by(ExamAnswer.id)]
    assert prefs(client)['reviewWeakThresholdPercent'] == 60
    assert weak(client) == {'zero', 'below'}
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': 70}).status_code == 200
    assert prefs(client)['reviewWeakThresholdPercent'] == 70
    assert weak(client) == {'zero', 'below', 'boundary', 'between', 'scaled', 'content'}
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': 60}).status_code == 200
    assert weak(client) == {'zero', 'below'}
    assert [a.score_result for a in db.query(ExamAnswer).order_by(ExamAnswer.id)] == before


def test_threshold_preserves_stars_removals_other_preferences_and_other_accounts(fixture):
    db, client, current = fixture
    original = deepcopy(db.query(User).filter_by(username='alice').one().preferences)
    item = {'examId': 'alice-exam', 'questionId': 'between'}
    assert client.put('/user/review-items', json={**item, 'isStarred': True}).status_code == 200
    assert client.put('/user/review-items', json={**item, 'hideWeak': True}).status_code == 200
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': 70, 'billing': {'admin': True}}).status_code == 200
    assert 'between' not in weak(client)
    stars = client.get('/user/review-items?type=starred').json()['list']
    assert len(stars) == 1 and stars[0]['questionId'] == 'between' and not stars[0]['isWeak']
    assert client.put('/user/preferences', json={'defaultAnswerTime': 240}).status_code == 200
    assert prefs(client)['reviewWeakThresholdPercent'] == 70
    saved = db.query(User).filter_by(username='alice').one().preferences
    assert all(saved[key] == value for key, value in original.items())
    current['name'] = 'bob'
    assert prefs(client)['reviewWeakThresholdPercent'] == 60
    assert weak(client) == set()
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': 80}).status_code == 200
    assert weak(client) == {'between'}
    current['name'] = 'alice'
    assert prefs(client)['reviewWeakThresholdPercent'] == 70
    assert 'between' not in weak(client)


@pytest.mark.parametrize('value', [0, 101, -1, 69.5, True, '70', '', [], {}])
def test_invalid_threshold_does_not_change_saved_preferences(fixture, value):
    _, client, _ = fixture
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': value}).status_code == 422
    assert prefs(client)['reviewWeakThresholdPercent'] == 60


@pytest.mark.parametrize('value', [1, 100])
def test_inclusive_setting_bounds(fixture, value):
    _, client, _ = fixture
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': value}).status_code == 200
    assert prefs(client)['reviewWeakThresholdPercent'] == value


@pytest.mark.parametrize('stored', [None, 0, 101, True, '70'])
def test_legacy_invalid_preference_uses_default(fixture, stored):
    db, client, _ = fixture
    db.query(User).filter_by(username='alice').one().preferences = {'reviewWeakThresholdPercent': stored}
    db.commit()
    assert prefs(client)['reviewWeakThresholdPercent'] == 60
    assert weak(client) == {'zero', 'below'}


def test_personal_low_line_does_not_change_direction_analysis_or_low_score_practice(fixture):
    from app.schemas.targeted_performance import PerformanceRequest, TargetedPracticeRequest
    from app.services.targeted_performance_service import performance
    from app.services.targeted_practice_service import select_practice

    db, client, _ = fixture
    question = db.get(Question, 'between')
    question.province = 'jiangsu'
    question.dimension = 'analysis'
    question.keywords = {'_meta': {'questionTypeCategory': '综合分析'}}
    db.commit()
    assert client.put('/user/preferences', json={'reviewWeakThresholdPercent': 70}).status_code == 200
    assert 'between' in weak(client)
    scope = {'province': 'jiangsu'}
    report = performance(db, 'alice', PerformanceRequest(target=scope, period='all'))
    assert report['rules']['lowThreshold'] == 60
    row = next(row for row in report['questionTypes'] if row['questionType'] == '综合分析')
    assert row['averagePercent'] == 69
    chosen = select_practice(db, 'alice', TargetedPracticeRequest(target=scope, period='all', questionType='综合分析', mode='low_score', count=3))
    assert chosen['questionIds'] == []
