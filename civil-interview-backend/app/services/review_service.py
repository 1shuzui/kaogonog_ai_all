"""Reviews are projections of owned saved answers plus durable user choices.

Scores, stems and weak flags never come from client caches. Writes lock the immutable
user row to serialize imports, removals and concurrent devices without losing tombstones.
"""
import math
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import User, Exam, ExamAnswer, Question, UserReviewState
from app.services.scoring_service import _is_placeholder_transcript


def _user(db, username, *, lock=False):
    query = db.query(User).filter(User.username == username)
    user = (query.with_for_update() if lock else query).first()
    if not user:
        raise HTTPException(status_code=404, detail="记录不存在")
    return user


def _score(answer):
    result = answer.score_result if isinstance(answer.score_result, dict) else {}
    if _is_placeholder_transcript(str(answer.transcript or "")) or result.get("skipReason"):
        return None
    try:
        points, maximum = float(result["totalScore"]), float(result.get("maxScore", 100))
        if result.get("appearanceScore") is None and result.get("questionScore") is not None and result.get("questionMaxScore") is not None:
            points, maximum = float(result["questionScore"]), float(result["questionMaxScore"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(points) or not math.isfinite(maximum) or maximum <= 0 or points < 0:
        return None
    return min(points, maximum), maximum


def _owned_answer(db, user, exam_id, question_id):
    row = db.query(ExamAnswer, Exam).join(Exam, Exam.id == ExamAnswer.exam_id).filter(
        Exam.user_id == user.username, Exam.id == exam_id, ExamAnswer.question_id == question_id,
    ).first()
    if not row or question_id not in (row[1].question_ids or []) or _score(row[0]) is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return row[0]


def _rows(db, user):
    answers = db.query(ExamAnswer, Exam).join(
        Exam, Exam.id == ExamAnswer.exam_id,
    ).filter(Exam.user_id == user.username).order_by(ExamAnswer.answered_at.desc(), ExamAnswer.id.desc()).all()
    # Existing deployments have different collations on question/answer/review IDs.
    # Bind IDs as query values, then associate exact IDs in memory instead of joining
    # incompatible legacy text columns or changing the whole production schema.
    question_ids = {answer.question_id for answer, _exam in answers}
    questions = {q.id: q for q in db.query(Question).filter(Question.id.in_(question_ids)).all()} if question_ids else {}
    states = {(state.exam_id, state.question_id): state for state in db.query(UserReviewState).filter_by(user_id=user.id).all()}
    return [(answer, exam, questions.get(answer.question_id), states.get((exam.id, answer.question_id))) for answer, exam in answers]


def list_review_items(db: Session, username: str, current=1, page_size=100, kind="all") -> dict:
    user = _user(db, username)
    items, seen = [], set()
    for answer, exam, question, state in _rows(db, user):
        key = (exam.id, answer.question_id)
        if key in seen or answer.question_id not in (exam.question_ids or []):
            continue
        seen.add(key)
        score = _score(answer)
        if score is None:
            continue
        points, maximum = score
        weak = points / maximum < 0.6 and not (state and state.hide_weak)
        starred = bool(state and state.is_starred)
        if not (weak or starred) or (kind == "weak" and not weak) or (kind == "starred" and not starred):
            continue
        date = answer.answered_at.isoformat() if answer.answered_at else ""
        items.append({
            "id": f"{exam.id}:{answer.question_id}", "examId": exam.id, "questionId": answer.question_id,
            "questionStem": question.stem if question else "题目已移除，可从历史记录查看作答",
            "dimension": question.dimension if question else "", "score": points, "maxScore": maximum,
            "grade": (answer.score_result or {}).get("grade", ""), "date": date,
            "addedAt": state.created_at.isoformat() if state and state.created_at else date,
            "isWeak": weak, "isStarred": starred, "type": "starred" if starred else "weak",
            "canPractice": question is not None,
        })
    current, page_size = max(1, int(current)), max(1, min(200, int(page_size)))
    offset = (current - 1) * page_size
    return {"list": items[offset:offset + page_size], "total": len(items), "current": current, "pageSize": page_size, "userId": str(user.id)}


def _state(db, user, exam_id, question_id):
    row = db.get(UserReviewState, (user.id, exam_id, question_id))
    if row is None:
        row = UserReviewState(user_id=user.id, exam_id=exam_id, question_id=question_id, is_starred=False, hide_weak=False)
        db.add(row)
    return row


def update_review_item(db: Session, username: str, exam_id: str, question_id: str, *, is_starred=None, hide_weak=None) -> dict:
    user = _user(db, username, lock=True)
    _owned_answer(db, user, exam_id, question_id)
    state = _state(db, user, exam_id, question_id)
    if is_starred is not None:
        state.is_starred = bool(is_starred)
    if hide_weak is not None:
        state.hide_weak = bool(hide_weak)
    state.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "userId": str(user.id)}


def clear_review_items(db: Session, username: str, scope="all") -> dict:
    user = _user(db, username, lock=True)
    for answer, exam, _question, _existing in _rows(db, user):
        if answer.question_id not in (exam.question_ids or []) or _score(answer) is None:
            continue
        state = _state(db, user, exam.id, answer.question_id)
        if scope in {"all", "starred"}:
            state.is_starred = False
        if scope in {"all", "weak"}:
            state.hide_weak = True
        state.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "userId": str(user.id)}


def import_review_items(db: Session, username: str, items: list[dict]) -> dict:
    user = _user(db, username, lock=True)
    imported = rejected = 0
    for item in items:
        exam_id, question_id = str(item.get("examId") or ""), str(item.get("questionId") or "")
        try:
            _owned_answer(db, user, exam_id, question_id)
        except HTTPException:
            rejected += 1
            continue
        # Existing rows include explicit cancellation/clear tombstones. Never overwrite them.
        if db.get(UserReviewState, (user.id, exam_id, question_id)) is not None:
            continue
        starred = item.get("isStarred") is True or ("isStarred" not in item and item.get("type") in {"starred", "favorite"})
        if starred:
            _state(db, user, exam_id, question_id).is_starred = True
            db.flush()
            imported += 1
    db.commit()
    return {"success": True, "userId": str(user.id), "imported": imported, "rejected": rejected}
