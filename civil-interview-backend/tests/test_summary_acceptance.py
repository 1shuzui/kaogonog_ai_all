from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.session import Base
from app.models.entities import Exam, ExamAnswer, Question
from app.services.exam_service import complete_exam
from app.services.history_service import get_history_stats


def test_completed_attempts_pending_scores_and_real_zero_have_distinct_statistics():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert get_history_stats(db, 'alice')['scoredExams'] == 0
        db.add(Question(id='q1', stem='验收题'))
        for exam_id in ['pending', 'zero', 'eighty']:
            db.add(Exam(id=exam_id, user_id='alice', question_ids=['q1']))
        db.add(ExamAnswer(exam_id='pending', question_id='q1', transcript='已转写，待点评', score_result={}))
        db.add(ExamAnswer(exam_id='zero', question_id='q1', transcript='真实零分作答', score_result={'totalScore':0,'maxScore':100}))
        db.add(ExamAnswer(exam_id='eighty', question_id='q1', transcript='已点评作答', score_result={'totalScore':28.8,'maxScore':36}))
        db.commit()
        complete_exam(db, 'pending')
        assert get_history_stats(db, 'alice')['totalExams'] == 1
        assert get_history_stats(db, 'alice')['scoredExams'] == 0
        complete_exam(db, 'zero')
        assert get_history_stats(db, 'alice')['scoredExams'] == 1
        assert get_history_stats(db, 'alice')['avgScore'] == 0
        complete_exam(db, 'eighty')
        stats = get_history_stats(db, 'alice')
        assert stats['totalExams'] == 3 and stats['scoredExams'] == 2 and stats['avgScore'] == 40
        assert get_history_stats(db, 'bob')['totalExams'] == 0


def test_five_question_attempt_keeps_order_and_three_answers_after_early_exit():
    from app.services.exam_service import start_exam
    from app.services.history_service import get_history_detail
    from app.schemas.common import ExamStartRequest
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    order = ['q3', 'q1', 'q5', 'q2', 'q4']
    with Session(engine) as db:
        db.add_all([Question(id=q, stem='验收题目 ' + q) for q in order])
        db.commit()
        exam_id = start_exam(db, ExamStartRequest(questionIds=order, practiceMode='training'), 'alice')['examId']
        for q in order[:3]:
            db.add(ExamAnswer(exam_id=exam_id, question_id=q, transcript='真实已答内容', score_result={'totalScore':70,'maxScore':100}))
        db.commit()
        complete_exam(db, exam_id)
        db.expunge_all()
        detail = get_history_detail(db, exam_id, 'alice')
        assert detail['questionIds'] == order and detail['totalQuestions'] == 5
        assert [answer['questionId'] for answer in detail['answers']] == order[:3]
        assert detail['questionCount'] == 3 and detail['practiceMode'] == 'training'
    engine.dispose()
