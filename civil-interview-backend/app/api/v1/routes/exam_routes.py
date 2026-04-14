from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, ExamStartRequest
from app.services.exam_service import start_exam, upload_recording, complete_exam

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start")
def exam_start(data: ExamStartRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return complete_exam(db, exam_id)
