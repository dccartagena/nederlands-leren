"""Curate-first content pipeline (handoff Part C).

Ingests open-licensed Dutch resources and builds the canonical files the
seed script consumes. The LLM is used only for enrichment and gap-filling —
never for facts (CEFR level, de/het article, plural, frequency, examples)
that authoritative data already provides.

Order of operations (monthly refresh, handoff Wave 6):
    python scripts/etl/fetch_sources.py --refresh
    python scripts/etl/build_lexicon.py
    python scripts/etl/build_sentences.py
    python scripts/etl/validate.py
    python scripts/seed_content.py
    python scripts/etl/coverage_report.py
"""
