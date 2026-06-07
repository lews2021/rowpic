"""One-click classify API."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List

from app.models.schemas import ClassifyRequest, ClassifyResult, PhotoMeta
from app.services.classifier_service import classify_all

router = APIRouter(prefix="/api/classify", tags=["classify"])


class ClassifyRunBody(BaseModel):
    """Combined body for the classify endpoint."""
    rules: List[str] = Field(default_factory=lambda: ["blurry", "blurry_face", "exposure"])
    move: bool = False
    dest_template: str = "{category}/{name}"
    photos: List[PhotoMeta] = Field(default_factory=list)


@router.post("/run", response_model=ClassifyResult)
def run_classify(body: ClassifyRunBody):
    if not body.photos:
        return ClassifyResult(total=0, categories={}, moves=[], per_photo={})
    req = ClassifyRequest(
        rules=body.rules, move=body.move, dest_template=body.dest_template
    )
    return classify_all(body.photos, req)
