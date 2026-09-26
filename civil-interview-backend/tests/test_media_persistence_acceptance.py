from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from app.db.session import Base
from app.db.schema_upgrades import ensure_answer_media_schema
from app.models.entities import Exam, ExamAnswer, Question
from app.services.exam_service import upload_recording, complete_exam
from app.services.history_service import get_history_detail
from app.services.scoring_service import _persist_result, get_scoring_result, attach_asr_meta_to_media_record
from app.services.answer_media import answer_media_record


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr('app.services.exam_service.UPLOAD_DIR', tmp_path)
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([Question(id='q1', stem='测试题'), Exam(id='exam-a', user_id='alice', question_ids=['q1'], practice_mode='targeted')])
        session.commit()
        yield session
    engine.dispose()


def test_upload_survives_scoring_retry_and_fresh_history_session(db):
    uploaded = upload_recording(db, 'exam-a', 'q1', 'recording.mp4', b'video-fixture', 'video')
    assert uploaded['mediaType'] == 'video/mp4'
    saved = _persist_result(db, 'exam-a', 'q1', '有效作答', {'totalScore': 70, 'maxScore': 100})
    assert saved['mediaRecord']['fileUrl'] == uploaded['fileUrl']
    complete_exam(db, 'exam-a')
    replacement = upload_recording(db, 'exam-a', 'q1', 'retry.mp4', b'new-video-fixture', 'video')
    assert replacement['fileUrl'] != uploaded['fileUrl']
    # An old scoring task or cache must not restore the previous upload's URL.
    _persist_result(db, 'exam-a', 'q1', '有效作答重试', {'totalScore': 75, 'maxScore': 100, 'mediaRecord': uploaded})
    with Session(db.bind) as fresh:
        detail = get_history_detail(fresh, 'exam-a', 'alice')
        assert detail['answers'][0]['mediaUrl'] == replacement['fileUrl']
        assert detail['answers'][0]['mediaType'] == 'video/mp4'
        assert get_scoring_result(fresh, 'exam-a', 'q1')['mediaRecord']['fileUrl'] == replacement['fileUrl']
        with pytest.raises(Exception) as error:
            get_history_detail(fresh, 'exam-a', 'bob')
        assert error.value.status_code == 404


def test_transcription_metadata_is_bound_to_exam_even_when_audio_track_hash_differs(db):
    upload_recording(db, 'exam-a', 'q1', 'answer.mp4', b'video', 'video')
    assert attach_asr_meta_to_media_record(db, 'separate-audio-hash', {'status':'success'}, exam_id='exam-a', question_id='q1')
    assert db.query(ExamAnswer).one().media_record['asrMeta']['status'] == 'success'
    assert not attach_asr_meta_to_media_record(db, 'separate-audio-hash', {'status':'wrong-user'})
    assert not attach_asr_meta_to_media_record(db, 'separate-audio-hash', {}, exam_id='foreign', question_id='q1')


def test_legacy_media_read_and_repeated_additive_upgrade_preserve_existing_data():
    legacy = SimpleNamespace(media_record=None, score_result={'mediaRecord': {'fileUrl':'/uploads/old.mp4','mediaType':'video'}})
    assert answer_media_record(legacy)['mediaType'] == 'video/mp4'
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE exam_answers (id INTEGER PRIMARY KEY, transcript TEXT)'))
        connection.execute(text("INSERT INTO exam_answers VALUES (1, 'preserved')"))
    ensure_answer_media_schema(engine)
    ensure_answer_media_schema(engine)
    assert 'media_record' in {column['name'] for column in inspect(engine).get_columns('exam_answers')}
    with engine.connect() as connection:
        assert connection.execute(text('SELECT transcript FROM exam_answers')).scalar() == 'preserved'
