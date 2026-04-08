#!/usr/bin/env python3
"""
Seed the database with vocabulary, grammar topics, and stories from JSON files.
Run from the backend/ directory with the venv activated:
    .venv/bin/python scripts/seed_content.py
"""
import sys
import json
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.db import models

DATA_DIR = settings.DATA_DIR


def seed_vocabulary(db):
    count = 0
    for json_file in (DATA_DIR / "vocabulary").glob("*.json"):
        with open(json_file) as f:
            words = json.load(f)
        for w in words:
            existing = db.query(models.VocabularyItem).filter_by(
                dutch_word=w["dutch_word"], level=w["level"]
            ).first()
            if not existing:
                item = models.VocabularyItem(**{
                    k: v for k, v in w.items()
                    if hasattr(models.VocabularyItem, k)
                })
                db.add(item)
                count += 1
    db.commit()
    print(f"  Vocabulary: {count} new items seeded")


def seed_grammar(db):
    count = 0
    for json_file in (DATA_DIR / "grammar").glob("*.json"):
        with open(json_file) as f:
            topics = json.load(f)
        for t in topics:
            existing = db.query(models.GrammarTopic).filter_by(slug=t["slug"]).first()
            if not existing:
                topic = models.GrammarTopic(**{
                    k: v for k, v in t.items()
                    if hasattr(models.GrammarTopic, k)
                })
                db.add(topic)
                count += 1
    db.commit()
    print(f"  Grammar: {count} new topics seeded")


def seed_stories(db):
    count = 0
    for json_file in (DATA_DIR / "stories").glob("*.json"):
        with open(json_file) as f:
            stories = json.load(f)
        for s in stories:
            existing = db.query(models.Story).filter_by(slug=s["slug"]).first()
            if not existing:
                story = models.Story(**{
                    k: v for k, v in s.items()
                    if hasattr(models.Story, k)
                })
                db.add(story)
                count += 1
    db.commit()
    print(f"  Stories: {count} new stories seeded")


def main():
    print("Creating tables…")
    models.Base.metadata.create_all(bind=engine)
    print("Seeding database…")
    db = SessionLocal()
    try:
        seed_vocabulary(db)
        seed_grammar(db)
        seed_stories(db)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
