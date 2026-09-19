import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, Question
from app.schemas.common import ExamStartRequest
from app.services.exam_service import start_exam
from app.services.history_service import get_history_list, get_history_detail
from app.services.question_service import get_random_questions, list_questions


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for id, province, year in [('a', 'jiangsu', '2024'), ('b', 'jiangsu', '2025'), ('c', 'anhui', '2024')]:
            session.add(Question(id=id, stem='基层群众沟通', province=province, dimension='analysis', keywords={
                '_meta': {'examDate': f'{year}-01-01', 'year': ['2020'], 'examCategory': '省级公务员考试'}
            }))
        session.commit()
        yield session


def test_random_inherits_exact_bank_filters_without_empty_result_fallback(db):
    filters = dict(province='jiangsu', year='2024', dimension='analysis', examCategory='省级公务员考试', keyword='群众')
    listed = list_questions(db, **filters)['list']
    sampled = get_random_questions(db, count=5, **filters)
    assert [row['id'] for row in sampled] == [row['id'] for row in listed] == ['a']
    assert get_random_questions(db, year='1999', province='jiangsu') == []
    assert {row['id'] for row in get_random_questions(db, province='all', year='2024，2025')} == {'a', 'b', 'c'}


def test_training_mode_survives_partial_submission_and_remains_private(db):
    created = start_exam(db, ExamStartRequest(questionIds=['a', 'b'], practiceMode='training'), 'alice')
    db.add(ExamAnswer(exam_id=created['examId'], question_id='a', transcript='首先了解群众需求'))
    db.commit()
    result = get_history_detail(db, created['examId'], 'alice')
    assert result['practiceMode'] == 'training'
    assert '专项训练' in result['questionSummary']
    assert result['totalQuestions'] == 2 and result['questionCount'] == 1
    assert get_history_list(db, 'bob')['list'] == []
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        get_history_detail(db, created['examId'], 'bob')
    assert error.value.status_code == 404


def test_legacy_clients_do_not_invent_a_practice_mode(db):
    result = start_exam(db, ExamStartRequest(questionIds=['a']), 'alice')
    assert db.get(Exam, result['examId']).practice_mode == 'legacy'


def test_old_exam_schema_is_upgraded_once_without_rewriting_records(monkeypatch):
    import main
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE exams (id VARCHAR(32) PRIMARY KEY)'))
        conn.execute(text("INSERT INTO exams (id) VALUES ('existing')"))
    monkeypatch.setattr(main, 'engine', engine)
    main.ensure_exam_practice_mode_schema()
    main.ensure_exam_practice_mode_schema()
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id, practice_mode FROM exams')).all() == [('existing', 'legacy')]
