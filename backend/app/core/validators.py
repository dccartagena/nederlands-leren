from fastapi import HTTPException
from sqlalchemy.orm import Query as SAQuery

_VALID_LEVELS: frozenset[str] = frozenset({"a0", "a1", "a2", "b1", "b2", "c1"})


def validate_level(level: str) -> str:
    """Normalize and validate a CEFR level string. Raises 422 on unknown value."""
    normalized = level.lower()
    if normalized not in _VALID_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid level '{level}'. Valid: {sorted(_VALID_LEVELS)}",
        )
    return normalized


def apply_content_filters(q: SAQuery, model_class, level: str | None, theme: str | None = None) -> SAQuery:
    """Apply standard level + theme filters to any content list query."""
    if level:
        q = q.filter(model_class.level == level.lower())
    if theme:
        q = q.filter(model_class.theme == theme)
    return q
