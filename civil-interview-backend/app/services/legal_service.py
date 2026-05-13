"""Legal document service."""

from app.data.legal_documents import LEGAL_DOCUMENTS


def get_legal_documents() -> dict:
    return LEGAL_DOCUMENTS
