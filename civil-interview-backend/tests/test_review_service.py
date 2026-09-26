"""Server-owned review state: identity, provenance, tombstones and migration."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.entities import User, Question, Exam, ExamAnswer, UserReviewState
from app.services.review_service import list_review_items, update_review_item, clear_review_items, import_review_items


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([User(id=1, username='alice', hashed_password='x'), User(id=2, username='bob', hashed_password='x')])
        session.add_all([Question(id='q1', stem='真实题干', dimension='analysis'), Question(id='q2', stem='第二题')])
        session.add_all([Exam(id='a1', user_id='alice', question_ids=['q1', 'q2']), Exam(id='b1', user_id='bob', question_ids=['q1'])])
        session.add_all([
            ExamAnswer(exam_id='a1', question_id='q1', transcript='先了解诉求，再协调落实。', score_result={'totalScore': 42, 'maxScore': 100}),
            ExamAnswer(exam_id='a1', question_id='q2', transcript='', score_result={'totalScore': 0, 'maxScore': 100}),
            ExamAnswer(exam_id='b1', question_id='q1', transcript='另一个用户的回答', score_result={'totalScore': 90, 'maxScore': 100}),
        ])
        session.commit()
        yield session


def test_server_derives_weak_items_and_never_includes_other_accounts_or_placeholders(db):
    rows = list_review_items(db, 'alice')['list']
    assert [(r['examId'], r['questionId']) for r in rows] == [('a1', 'q1')]
    assert rows[0]['isWeak'] and not rows[0]['isStarred']
    assert rows[0]['questionStem'] == '真实题干'
    assert list_review_items(db, 'bob')['list'] == []
    for score in ({}, {'totalScore': None}, {'totalScore': 1, 'maxScore': 0}, {'totalScore': float('nan'), 'maxScore': 100}):
        db.query(ExamAnswer).filter_by(exam_id='a1', question_id='q1').one().score_result = score
        db.commit()
        assert list_review_items(db, 'alice')['list'] == []


def test_weak_threshold_uses_effective_question_points_and_keeps_real_zero(db):
    answer = db.query(ExamAnswer).filter_by(exam_id='a1', question_id='q1').one()
    answer.score_result = {'totalScore': 80, 'maxScore': 100, 'questionScore': 18, 'questionMaxScore': 36}
    db.commit()
    item = list_review_items(db, 'alice')['list'][0]
    assert (item['score'], item['maxScore'], item['isWeak']) == (18, 36, True)
    answer.score_result = {'totalScore': 0, 'maxScore': 100}
    db.commit()
    assert list_review_items(db, 'alice')['list'][0]['score'] == 0


def test_starred_and_weak_flags_are_independent_and_deletions_survive_reload_and_import(db):
    update_review_item(db, 'alice', 'a1', 'q1', is_starred=True)
    update_review_item(db, 'alice', 'a1', 'q1', hide_weak=True)
    item = list_review_items(db, 'alice')['list'][0]
    assert item['isStarred'] and not item['isWeak']
    update_review_item(db, 'alice', 'a1', 'q1', is_starred=False)
    legacy = [{'examId': 'a1', 'questionId': 'q1', 'isStarred': True, 'score': 999, 'questionStem': '伪造题干'}]
    import_review_items(db, 'alice', legacy)
    assert list_review_items(db, 'alice')['list'] == []
    assert db.query(UserReviewState).count() == 1


def test_foreign_exam_wrong_question_and_missing_exam_are_indistinguishable(db):
    for exam, question in [('b1', 'q1'), ('missing', 'q1'), ('a1', 'missing'), ('a1', 'q2')]:
        with pytest.raises(HTTPException) as error:
            update_review_item(db, 'alice', exam, question, is_starred=True)
        assert error.value.status_code == 404
        assert error.value.detail == '记录不存在'


def test_import_revalidates_provenance_is_idempotent_and_does_not_trust_scores(db):
    legacy = [
        {'examId': 'a1', 'questionId': 'q1', 'type': 'starred', 'score': 999},
        {'examId': 'b1', 'questionId': 'q1', 'type': 'starred'},
        {'examId': 'a1', 'questionId': 'q2', 'type': 'starred'},
        {'examId': '', 'questionId': 'q1', 'type': 'starred'},
    ]
    first = import_review_items(db, 'alice', legacy)
    assert first['imported'] == 1 and first['rejected'] == 3
    assert import_review_items(db, 'alice', legacy)['imported'] == 0
    assert db.query(UserReviewState).count() == 1
    item = list_review_items(db, 'alice')['list'][0]
    assert item['score'] == 42 and item['isStarred']


def test_clear_keeps_other_users_and_future_attempts_and_rename_keeps_owner(db):
    update_review_item(db, 'alice', 'a1', 'q1', is_starred=True)
    update_review_item(db, 'bob', 'b1', 'q1', is_starred=True)
    clear_review_items(db, 'alice', 'all')
    assert not list_review_items(db, 'alice')['list']
    assert len(list_review_items(db, 'bob')['list']) == 1
    db.add(Exam(id='a2', user_id='alice', question_ids=['q1']))
    db.add(ExamAnswer(exam_id='a2', question_id='q1', transcript='新一次作答', score_result={'totalScore': 50, 'maxScore': 100}))
    db.commit()
    assert [r['examId'] for r in list_review_items(db, 'alice')['list']] == ['a2']
    db.get(User, 1).username = 'renamed'
    for exam in db.query(Exam).filter_by(user_id='alice'):
        exam.user_id = 'renamed'
    db.commit()
    assert [r['examId'] for r in list_review_items(db, 'renamed')['list']] == ['a2']
    assert db.query(UserReviewState).filter_by(user_id=1).count() == 1


def test_boundary_and_scope_clear(db):
    answer = db.query(ExamAnswer).filter_by(exam_id='a1', question_id='q1').one()
    answer.score_result = {'totalScore': 60, 'maxScore': 100}
    db.commit()
    assert list_review_items(db, 'alice')['list'] == []
    update_review_item(db, 'alice', 'a1', 'q1', is_starred=True)
    clear_review_items(db, 'alice', 'weak')
    assert list_review_items(db, 'alice')['list'][0]['isStarred']
