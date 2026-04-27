from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.validators import apply_content_filters, validate_level
from app.db.models import VocabularyItem
from app.db.session import get_db
from app.schemas import VocabularyItemOut

router = APIRouter()


@router.get("/", response_model=list[VocabularyItemOut])
def list_vocabulary(
    level: str | None = Query(None, description="Filter by level: a0, a1, a2, b1, b2, c1"),
    theme: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if level is not None:
        validate_level(level)
    q = apply_content_filters(db.query(VocabularyItem), VocabularyItem, level, theme)
    return q.offset(offset).limit(limit).all()


@router.get("/{item_id}", response_model=VocabularyItemOut)
def get_vocabulary_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(VocabularyItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
