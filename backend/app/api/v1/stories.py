from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.validators import apply_content_filters
from app.db.models import Story
from app.db.session import get_db
from app.schemas import StoryOut

router = APIRouter()


@router.get("/", response_model=list[StoryOut])
def list_stories(
    level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return apply_content_filters(db.query(Story), Story, level).all()


@router.get("/{slug}", response_model=StoryOut)
def get_story(slug: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter_by(slug=slug).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story
