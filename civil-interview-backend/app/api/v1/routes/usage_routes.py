from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser, UsageReportRequest
from app.services.usage_service import report_usage

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/report")
def usage_report(data: UsageReportRequest, current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_usage(db, current_user, data)
