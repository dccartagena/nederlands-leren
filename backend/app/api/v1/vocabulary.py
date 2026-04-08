from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.db.models import VocabularyItem
from app.schemas import VocabularyItemOut

router = APIRouter()


@router.get("/", response_model=List[VocabularyItemOut])
def list_vocabulary(
    level: Optional[str] = Query(None, description="Filter by level: a0, a1"),
    theme: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
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
