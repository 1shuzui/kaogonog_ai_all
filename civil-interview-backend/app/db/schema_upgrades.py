"""Additive, repeatable schema upgrades for existing installations."""
from sqlalchemy import inspect, text


def ensure_answer_media_schema(bind):
    inspector = inspect(bind)
    if not inspector.has_table('exam_answers'):
        return
    if 'media_record' not in {column['name'] for column in inspector.get_columns('exam_answers')}:
        with bind.begin() as connection:
            connection.execute(text('ALTER TABLE exam_answers ADD COLUMN media_record JSON NULL'))
