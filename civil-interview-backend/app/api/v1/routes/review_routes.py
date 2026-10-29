"""Authenticated review operations. Ownership is never accepted from the request body."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services import review_service

router = APIRouter(prefix="/user/review-items", tags=["review"])


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    examId: str = Field(min_length=1, max_length=32)
    questionId: str = Field(min_length=1, max_length=128)
    isStarred: bool | None = None
    hideWeak: bool | None = None

    @model_validator(mode="after")
    def has_action(self):
        if self.isStarred is None and self.hideWeak is None:
            raise ValueError("请指定收藏或低分题操作")
        return self


class ReviewClear(BaseModel):
    scope: Literal["all", "starred", "weak"] = "all"


class LegacyReview(BaseModel):
    examId: str = Field(default="", max_length=32)
    questionId: str = Field(default="", max_length=128)
    isStarred: bool | None = None
    type: str = Field(default="", max_length=20)


class ReviewImport(BaseModel):
    items: list[LegacyReview] = Field(max_length=200)


@router.get("")
def list_items(current: int = Query(1, ge=1), pageSize: int = Query(100, ge=1, le=200),
               type: Literal["all", "weak", "starred"] = "all",
               user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.list_review_items(db, user.username, current, pageSize, type)


@router.put("")
def update_item(data: ReviewUpdate, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.update_review_item(db, user.username, data.examId, data.questionId, is_starred=data.isStarred, hide_weak=data.hideWeak)


@router.post("/clear")
def clear_items(data: ReviewClear, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.clear_review_items(db, user.username, data.scope)


@router.post("/import")
def import_items(data: ReviewImport, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.import_review_items(db, user.username, [item.model_dump(exclude_none=True) for item in data.items])
