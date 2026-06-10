"""
考试服务层，负责创建练习/全真模拟、保存每题音视频答案、完成整场考试并写入历史成绩。

专项练习、定向备面和全真模拟最终都落到同一套考试表，是为了保证题目顺序、答题媒体、评分结果和历史记录能互相追溯。
作答阶段不能提前暴露分数；题目分值、扣分点和维度反馈只能在评分后进入结果。上传目录在这里集中创建，
避免路由层直接处理本地路径导致部署路径和容器路径不一致。

@param: 服务函数接收数据库 Session、当前用户、考试创建请求、上传文件和提交内容。
@return: 返回考试对象、答题保存结果、完成后的历史记录或结果摘要。
@raises HTTPException: 题目不存在、考试不存在、重复提交冲突、文件保存失败或用户无权访问时抛出 HTTP 错误。
"""
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamAnswer, HistoryRecord, Question
from app.schemas.common import ExamStartRequest

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_upload_name(raw_name: str) -> str:
    safe_name = "".join(ch for ch in str(raw_name or "") if ch.isalnum() or ch in {"-", "_", "."})
    return safe_name or "recording.webm"


def start_exam(db: Session, data: ExamStartRequest, username: str) -> dict:
    """
    创建考试记录前先确认题目存在，避免坏题号进入后续上传、评分和历史链路。

    专项练习和全真模拟都走这里，所以题目去重和顺序保留必须在服务端统一处理。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param data: 路由层校验后的业务请求体；保留模型字段可以减少端侧版本差异造成的分支。
    @param username: 账号唯一标识；历史记录、权益和订单仍以用户名串联，需保持向后兼容。
    @return: 新建考试 ID、确认后的题目顺序和开始时间。
    @raises HTTPException: 题目不存在时抛出 404，避免创建无法评分的考试。
    """
    question_ids = list(dict.fromkeys(data.questionIds))
    existing_ids = {
        row[0]
        for row in db.query(Question.id).filter(Question.id.in_(question_ids)).all()
    }
    missing_ids = [question_id for question_id in question_ids if question_id not in existing_ids]
    if missing_ids:
        preview = "、".join(missing_ids[:3])
        raise HTTPException(status_code=404, detail=f"题目不存在，无法开始考试: {preview}")

    exam_id = f"exam_{uuid.uuid4().hex[:8]}"
    exam = Exam(
        id=exam_id,
        user_id=username,
        question_ids=question_ids,
        status="in_progress",
        start_time=datetime.now(timezone.utc),
    )
    db.add(exam)
    db.commit()
    return {
        "examId": exam_id,
        "questionIds": question_ids,
        "startTime": exam.start_time.isoformat(),
    }


def upload_recording(
    db: Session,
    exam_id: str,
    question_id: str,
    filename: str,
    content: bytes,
    media_type: str = "",
    source: str = "live_recording",
) -> dict:
    """
    保存答题媒体并挂到对应考试题目上，方便后续 ASR、评分结果和人工排查互相追溯。

    文件名会被重新生成，是为了防止用户上传的原文件名覆盖本地文件或泄露奇怪路径。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @param question_id: 题目唯一标识；评分、收藏和错题复盘需要用它追溯同一道真实题源。
    @param filename: 文件对象或路径；脚本和上传流程依赖它保留来源可追溯性。
    @param content: 上传文件的字节内容；用于落盘和生成内容哈希。
    @param media_type: 端侧上报的 MIME 类型；为空时按二进制文件兜底。
    @param source: 媒体来源标记；用于区分现场录制、补传或测试素材。
    @return: 上传成功标记、访问路径、文件名、媒体类型和哈希信息。
    @raises HTTPException: 考试不存在时抛出 404。
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")

    answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.question_id == question_id,
    ).first()
    if not answer:
        answer = ExamAnswer(exam_id=exam_id, question_id=question_id)
        db.add(answer)

    original_name = _sanitize_upload_name(filename)
    extension = Path(original_name).suffix or ".webm"
    stored_name = f"{exam_id}_{question_id}_{uuid.uuid4().hex[:8]}{extension}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(content)

    media_record = {
        "fileUrl": f"/uploads/{stored_name}",
        "storedFilename": stored_name,
        "originalFilename": original_name,
        "mediaType": media_type or "application/octet-stream",
        "source": source or "live_recording",
        "contentSha256": hashlib.sha256(content).hexdigest(),
        "contentBytes": len(content),
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }
    existing_result = answer.score_result if isinstance(answer.score_result, dict) else {}
    if "totalScore" not in existing_result:
        answer.score_result = {**existing_result, "mediaRecord": media_record}
    answer.answered_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, **media_record}


def complete_exam(db: Session, exam_id: str) -> dict:
    """
    结束考试时汇总已评分答案并写入历史记录，让结果页和历史页看到同一份成绩。

    这里按已完成评分的题目计算平均分；未评分答案不会被硬算成低分。

    @param db: 调用方传入的数据库会话；复用外层事务边界，避免服务层隐式创建连接导致状态不一致。
    @param exam_id: 考试记录标识；用于把多题作答、扣权益和历史结果绑定到同一次练习。
    @return: 完成后的考试状态、平均分、等级和历史记录摘要。
    @raises HTTPException, IntegrityError: 考试不存在或历史记录写入冲突时抛出。
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试未找到")
    exam.status = "completed"
    exam.end_time = datetime.now(timezone.utc)

    answers = db.query(ExamAnswer).filter(ExamAnswer.exam_id == exam_id).all()
    total_score, question_count, dimensions = 0.0, 0, []
    for ans in answers:
        sr = ans.score_result or {}
        if "totalScore" not in sr:
            continue
        total_score += sr.get("totalScore", 0)
        question_count += 1
        if sr.get("dimensions"):
            dimensions = sr["dimensions"]

    avg = round(total_score / question_count, 2) if question_count else 0
    max_score = 100
    grade = "A" if avg / max_score > 0.85 else "B" if avg / max_score >= 0.75 else "C" if avg / max_score >= 0.60 else "D"

    # Upsert history record
    record = db.query(HistoryRecord).filter(HistoryRecord.exam_id == exam_id).first()
    if not record:
        record = HistoryRecord(exam_id=exam_id, username=exam.user_id)
        db.add(record)
    province = "national"
    if isinstance(exam.question_ids, list) and exam.question_ids:
        first_question = db.query(Question).filter(Question.id == exam.question_ids[0]).first()
        if first_question and first_question.province:
            province = first_question.province
    record.question_count = question_count
    record.total_score = avg
    record.max_score = max_score
    record.grade = grade
    record.province = province
    record.dimensions = dimensions
    record.completed_at = exam.end_time
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "history_records.exam_id" not in str(exc) and "Duplicate entry" not in str(exc):
            raise
        record = db.query(HistoryRecord).filter(HistoryRecord.exam_id == exam_id).first()
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not record or not exam:
            raise
        question_count = int(record.question_count or 0)
        avg = float(record.total_score or 0)

    return {
        "success": True,
        "status": exam.status,
        "questionCount": question_count,
        "finalScore": avg,
        "completedAt": exam.end_time.isoformat() if exam.end_time else "",
    }
