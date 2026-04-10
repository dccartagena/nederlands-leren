
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import Story
from app.db.session import get_db
from app.schemas import StoryOut

router = APIRouter()


@router.get("/", response_model=list[StoryOut])
def list_stories(
    level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Story)
    if level:
        q = q.filter(Story.level == level.lower())
    return q.all()


@router.get("/{slug}", response_model=StoryOut)
def get_story(slug: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    story = db.query(Story).filter_by(slug=slug).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story
