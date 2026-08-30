"""考试、答案和评分结果的统一所有权边界。"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamAnswer


def get_owned_exam_or_404(
    db: Session,
    exam_id: str,
    username: str,
    question_id: str | None = None,
) -> Exam:
    """
    返回当前用户自己的考试；越权、不存在和题目不属于考试均返回相同 404。

    对合法用户没有额外交互步骤。对外统一 404 可以避免通过考试 ID 或题目 ID 枚举他人作答数据。
    旧考试若 question_ids 不完整，但已经有该题答案，仍视为考试内题目，保证历史用户可正常复盘。
    """
    normalized_exam_id = str(exam_id or "").strip()
    normalized_username = str(username or "").strip()
    exam = (
        db.query(Exam)
        .filter(
            Exam.id == normalized_exam_id,
            Exam.user_id == normalized_username,
        )
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="记录不存在")

    normalized_question_id = str(question_id or "").strip()
    if normalized_question_id:
        question_ids = exam.question_ids if isinstance(exam.question_ids, list) else []
        belongs_to_exam = normalized_question_id in {str(item) for item in question_ids}
        if not belongs_to_exam:
            belongs_to_exam = db.query(ExamAnswer.id).filter(
                ExamAnswer.exam_id == exam.id,
                ExamAnswer.question_id == normalized_question_id,
            ).first() is not None
        if not belongs_to_exam:
            raise HTTPException(status_code=404, detail="记录不存在")
    return exam
