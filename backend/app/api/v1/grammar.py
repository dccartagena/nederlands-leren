
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import GrammarTopic
from app.db.session import get_db
from app.schemas import GrammarTopicOut

router = APIRouter()


@router.get("/", response_model=list[GrammarTopicOut])
def list_grammar(
    level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(GrammarTopic)
    if level:
        q = q.filter(GrammarTopic.level == level.lower())
    return q.all()


@router.get("/{slug}", response_model=GrammarTopicOut)
def get_grammar(slug: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    topic = db.query(GrammarTopic).filter_by(slug=slug).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Grammar topic not found")
    return topic
