from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.validators import apply_content_filters
from app.db.models import GrammarTopic
from app.db.session import get_db
from app.schemas import GrammarTopicOut

router = APIRouter()


@router.get("/", response_model=list[GrammarTopicOut])
def list_grammar(
    level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return apply_content_filters(db.query(GrammarTopic), GrammarTopic, level).all()


@router.get("/{slug}", response_model=GrammarTopicOut)
def get_grammar(slug: str, db: Session = Depends(get_db)):
    topic = db.query(GrammarTopic).filter_by(slug=slug).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Grammar topic not found")
    return topic
