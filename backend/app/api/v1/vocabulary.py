
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import VocabularyItem
from app.db.session import get_db
from app.schemas import VocabularyItemOut

router = APIRouter()

_VALID_LEVELS = {"a0", "a1", "a2", "b1", "b2", "c1"}


@router.get("/", response_model=list[VocabularyItemOut])
def list_vocabulary(
    level: str | None = Query(None, description="Filter by level: a0, a1, a2, b1, b2, c1"),
    theme: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if level is not None and level.lower() not in _VALID_LEVELS:
        raise HTTPException(status_code=422, detail=f"Invalid level '{level}'. Must be one of: {sorted(_VALID_LEVELS)}")
    q = db.query(VocabularyItem)
    if level:
        q = q.filter(VocabularyItem.level == level.lower())
    if theme:
        q = q.filter(VocabularyItem.theme == theme)
    return q.offset(offset).limit(limit).all()


@router.get("/{item_id}", response_model=VocabularyItemOut)
def get_vocabulary_item(item_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    item = db.query(VocabularyItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
