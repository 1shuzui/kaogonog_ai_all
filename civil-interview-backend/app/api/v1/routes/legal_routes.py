from fastapi import APIRouter

from app.services.legal_service import get_legal_documents

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents")
def legal_documents():
    return get_legal_documents()
