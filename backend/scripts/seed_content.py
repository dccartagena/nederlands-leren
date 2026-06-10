#!/usr/bin/env python3
"""
Seed the database with vocabulary, grammar topics, and stories from JSON files.

This now happens automatically on backend startup (AUTO_SEED=true) and via the
background scheduler; this script remains as a manual fallback:
    python scripts/seed_content.py
"""
import sys
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import models
from app.db.session import SessionLocal, engine
from app.services.content_seeder import seed_all


def main():
    print("Creating tables…")
    models.Base.metadata.create_all(bind=engine)
    print("Seeding database…")
    db = SessionLocal()
    try:
        print(f"  {seed_all(db)}")
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
