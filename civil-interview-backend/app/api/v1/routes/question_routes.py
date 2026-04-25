from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.access import (
    ensure_admin_access,
    ensure_paid_access,
    ensure_question_read_access,
    ensure_random_question_access,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, QuestionCreate, QuestionUpdate
from app.services.question_service import (
    list_questions, get_random_questions, get_question,
    create_question, update_question, delete_question,
    import_questions, generate_questions_by_position, generate_training_questions,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("")
def list_qs(
    keyword: str = "", dimension: str = "", province: str = "",
    current: int = 1, pageSize: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    ensure_paid_access(current_user, detail="开通后可查看推荐题目与扩展题目")
    return list_questions(db, keyword=keyword, dimension=dimension, province=province, current=current, page_size=pageSize)


@router.get("/random")
def random_qs(
    province: str = "national", count: int = 5,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    ensure_random_question_access(current_user, count)
    return get_random_questions(db, province=province, count=count)


@router.get("/{question_id}")
def get_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_question_read_access(current_user, question_id)
    return get_question(db, question_id)


@router.post("")
def create_q(data: QuestionCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_admin_access(current_user)
    return create_question(db, data)


@router.put("/{question_id}")
def update_q(question_id: str, data: QuestionUpdate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_admin_access(current_user)
    return update_question(db, question_id, data)


@router.delete("/{question_id}")
def delete_q(question_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_admin_access(current_user)
    return delete_question(db, question_id)


@router.post("/import")
async def import_qs(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_admin_access(current_user)
    content = await file.read()
    return import_questions(db, content, file.filename or "")


@router.post("/generate")
async def generate_qs(data: dict, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ensure_admin_access(current_user)
    return await generate_questions_by_position(
        db,
        data.get("province", "national"),
        data.get("position", "general"),
        data.get("count", 5),
        data.get("sourceMode", "local"),
    )
