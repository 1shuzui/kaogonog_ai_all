from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.access import ensure_exam_start_access
from app.core.rate_limit import check_rate_limit
from app.core.security import get_current_user, get_current_user_from_request
from app.db.session import get_db
from app.schemas.common import AuthUser, ExamStartRequest
from app.services.exam_service import (
    complete_exam_for_user,
    get_exam_media_record,
    start_exam,
    upload_recording,
)
from app.services.media_storage import media_response

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start")
def exam_start(data: ExamStartRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_exam_start_access(current_user, data.questionIds)
    return start_exam(db, data, current_user.username)


@router.post("/{exam_id}/upload")
async def exam_upload(
    request: Request,
    exam_id: str,
    questionId: str = Form(...),
    mediaType: str = Form(""),
    source: str = Form("live_recording"),
    recording: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_rate_limit(request, "exam:upload", limit=20, window_seconds=600, identity=current_user.username)
    content = await recording.read()
    return upload_recording(
        db,
        exam_id,
        questionId,
        recording.filename or "",
        content,
        current_user.username,
        is_admin=current_user.isAdmin,
        media_type=mediaType or recording.content_type or "",
        source=source,
    )


@router.post("/{exam_id}/complete")
def exam_complete(exam_id: str, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return complete_exam_for_user(db, exam_id, current_user.username, is_admin=current_user.isAdmin)


@router.get("/{exam_id}/media/{question_id}/play")
def exam_media_play(
    exam_id: str,
    question_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user_from_request),
    db: Session = Depends(get_db),
):
    media_record = get_exam_media_record(db, exam_id, question_id, current_user.username, is_admin=current_user.isAdmin)
    return media_response(request, media_record, download=False)


@router.get("/{exam_id}/media/{question_id}/download")
def exam_media_download(
    exam_id: str,
    question_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media_record = get_exam_media_record(db, exam_id, question_id, current_user.username, is_admin=current_user.isAdmin)
    return media_response(request, media_record, download=True)
