"""Exercise actual HTTP routes against isolated acceptance data and real tokens."""
import io
import json

import openpyxl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.question_routes import router as question_router
from app.api.v1.routes.review_routes import router as review_router
from app.core.security import get_password_hash
from app.db.session import Base, get_db
from app.models.entities import User, Question, Exam, ExamAnswer
from app.services.auth_service import login_user
from app.services import question_service


@pytest.fixture
def fixture():
    engine = create_engine('sqlite:///:memory:', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        password_hash = get_password_hash('acceptance-password')
        db.add_all([User(username=name, hashed_password=password_hash) for name in ['alice', 'bob', 'admin']])
        db.add(Question(id='acceptance-q', stem='独立验收题目'))
        db.add(Exam(id='acceptance-exam', user_id='alice', question_ids=['acceptance-q']))
        db.add(ExamAnswer(exam_id='acceptance-exam', question_id='acceptance-q', transcript='有效作答', score_result={'totalScore': 40, 'maxScore': 100}))
        db.commit()
        app = FastAPI()
        app.include_router(review_router)
        app.include_router(question_router)
        app.dependency_overrides[get_db] = lambda: db
        headers = {(name, kind): {'Authorization': 'Bearer ' + login_user(db, name, 'acceptance-password', kind)['access_token']} for name, kind in [('alice', 'web'), ('alice', 'wechat'), ('bob', 'web'), ('admin', 'web')]}
        with TestClient(app) as client:
            yield db, client, headers
    engine.dispose()
    question_service._full_exam_suite_cache.clear()


def test_review_cross_client_sync_foreign_ids_and_clear_over_http(fixture):
    db, client, headers = fixture
    route = '/user/review-items'
    pc, mini, bob = headers['alice', 'web'], headers['alice', 'wechat'], headers['bob', 'web']
    body = {'examId': 'acceptance-exam', 'questionId': 'acceptance-q', 'isStarred': True}
    assert client.get(route).status_code == 401
    assert client.put(route, json=body, headers=pc).status_code == 200
    assert client.put(route, json=body, headers=pc).status_code == 200
    rows = client.get(route, headers=mini).json()
    assert rows['list'][0]['isStarred'] and rows['list'][0]['isWeak']
    assert rows['userId'] == str(db.query(User).filter_by(username='alice').one().id)
    assert client.get(route, headers=bob).json()['total'] == 0
    assert client.put(route, json=body, headers=bob).status_code == 404
    assert client.put(route, json={**body, 'userId': rows['userId']}, headers=bob).status_code == 422
    assert client.post(route + '/clear', json={'scope': 'bogus'}, headers=pc).status_code == 422
    assert client.put(route, json={**body, 'isStarred': False}, headers=mini).status_code == 200
    assert not client.get(route, headers=pc).json()['list'][0]['isStarred']
    assert client.post(route + '/clear', json={'scope': 'all'}, headers=pc).status_code == 200
    for _ in range(2):
        response = client.post(route + '/import', json={'items': [body]}, headers=mini)
        assert response.status_code == 200 and response.json()['imported'] == 0
    assert client.get(route, headers=mini).json()['total'] == 0


def test_admin_import_query_edit_and_invalid_files_use_independent_fixture(fixture):
    db, client, headers = fixture
    admin, bob = headers['admin', 'web'], headers['bob', 'web']
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['id', '题干', '省份', '考试大类', '年份'])
    sheet.append(['acceptance-import', '独立验收导入：如何沟通？', 'jiangsu', '事业单位考试', '2026'])
    content = io.BytesIO()
    workbook.save(content)
    files = {'file': ('acceptance.xlsx', content.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    assert client.post('/questions/import', files=files, headers=bob).status_code == 403
    imported = client.post('/questions/import', files=files, headers=admin)
    assert imported.status_code == 200 and imported.json()['imported'] == 1, imported.text
    query = client.get('/questions', params={'keyword': '独立验收导入', 'province': 'jiangsu', 'year': '2026'}, headers=admin)
    assert query.status_code == 200 and query.json()['total'] == 1, query.text
    question_id = query.json()['list'][0]['id']
    assert client.put('/questions/' + question_id, json={'stem': '独立验收编辑后的题干'}, headers=bob).status_code == 403
    edited = client.put('/questions/' + question_id, json={'stem': '独立验收编辑后的题干'}, headers=admin)
    assert edited.status_code == 200, edited.text
    assert client.get('/questions/' + question_id, headers=admin).json()['stem'] == '独立验收编辑后的题干'
    before = db.query(Question).count()
    for filename, content in [('broken.json', b'{'), ('empty.json', b'[]'), ('unsupported.txt', b'data'), ('broken.xlsx', b'not an xlsx')]:
        failed = client.post('/questions/import', files={'file': (filename, content)}, headers=admin)
        assert failed.status_code == 400, failed.text
        assert db.query(Question).count() == before
