"""
考试路由，承接创建考场、上传每题答案媒体和完成整场考试三个用户关键动作。

这里必须先做登录与权益校验，再把题目选择、媒体保存和结果写库交给 `exam_service.py`。
作答接口只接收音频/视频和文字稿，不返回评分后的分数；分数展示由评分和结果页完成，避免练习或考试时提前暴露题目分值。

@param: FastAPI 注入考试创建请求、上传文件、表单字段、当前用户和数据库 Session。
@return: 返回新考试信息、单题上传结果或整场完成结果。
@raises HTTPException: 未登录、权益不足、考试不存在、题目不存在或媒体上传失败时返回 HTTP 错误。
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.access import ensure_exam_start_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, ExamStartRequest
from app.services.exam_service import start_exam, upload_recording, complete_exam

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start")
def exam_start(data: ExamStartRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    创建一次练习或考试会话的路由。

    抽题、模式校验和考试记录创建都在 exam_service，路由层只把端侧准备页的选择转成服务层请求。

    @param data: 考试开始请求，包含模式、题目数量和筛选条件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 新考试会话、题目列表和模式信息。
    @raises HTTPException: 未登录、无可用题目或权限不足时抛出。
    """
    ensure_exam_start_access(current_user, data.questionIds)
    return start_exam(db, data, current_user.username)


@router.post("/{exam_id}/upload")
async def exam_upload(
    exam_id: str,
    questionId: str = Form(...),
    mediaType: str = Form(""),
    source: str = Form("live_recording"),
    recording: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传答题音频或视频的路由。

    媒体文件只先保存并关联考试答案，转写和评分由后续评分链路处理，避免上传接口承担长耗时模型调用。

    @param exam_id: 考试会话 ID。
    @param answer_id: 答案 ID。
    @param mediaType: audio 或 video。
    @param source: 上传来源。
    @param recording: 上传文件。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 媒体保存结果和可用于评分的引用信息。
    @raises HTTPException: 文件缺失、考试无权访问或保存失败时抛出。
    """
    content = await recording.read()
    return upload_recording(
        db,
        exam_id,
        questionId,
        recording.filename or "",
        content,
        media_type=mediaType or recording.content_type or "",
        source=source,
    )


@router.post("/{exam_id}/complete")
def exam_complete(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    完成考试会话的路由。

    提交完成只标记考试流程状态，不直接代表评分完成；结果页仍需要按评分接口返回的数据展示。

    @param exam_id: 考试会话 ID。
    @param data: 完成请求，包含答案摘要等信息。
    @param current_user: Bearer token 解析出的当前用户。
    @param db: 请求级数据库会话。
    @return: 完成后的考试状态。
    @raises HTTPException: 考试不存在或无权访问时抛出。
    """
    return complete_exam(db, exam_id)
