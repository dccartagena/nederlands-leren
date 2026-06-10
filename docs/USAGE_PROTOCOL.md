# Usage Protocol (Wave 6)

How to actually use the app so the pedagogy works. Based on Nation's four
strands and the spaced-repetition literature — see the masterplan handoff.

## Daily (~25 min, four strands)

1. **Clear the FSRS queue** (≤10 min, hard floor — this is non-negotiable).
   `Práctica → Tarjetas`. New cards are capped at 15/day so reviews never snowball.
2. **One input activity**: a story (`Modo Historia`) or a listening round
   (`Escuchar`, `Dictado`).
3. **One output activity**: `Escribir`, `Hablar`, or 5 chat turns on the
   current theme.
4. **Fridays**: swap (3) for a fluency drill — a speed round of cards you
   already know well, or re-reading an already-completed story.

The **strands meter** on the Progress page shows this week's balance; aim for
roughly equal activity across the four strands.

## Operations: automated

The backend runs an in-process scheduler — there is no routine maintenance to
remember. Status and manual triggers live in **Ajustes → Mantenimiento
automático**.

| Job | Cadence | What it does | Flag (`.env`) |
|---|---|---|---|
| Seed content | startup + daily | loads `data/` JSON into the DB, regenerates `ATTRIBUTIONS.md` | `AUTO_SEED` |
| Backup | daily | progress export → `data/backups/` (keeps `BACKUP_RETENTION`, default 14) | `AUTO_BACKUP` |
| Audio gap-fill | daily | synthesizes audio for vocabulary that has none (batch-capped) | `AUTO_AUDIO_GAPFILL` |
| FSRS optimizer | weekly | recomputes scheduler parameters once ≥1,000 review logs exist (needs `pip install "fsrs[optimizer]"`) | `AUTO_FSRS_OPTIMIZE` |
| Content refresh | weekly | full ETL (fetch → lexicon → sentences → validate → reseed → coverage) | `AUTO_CONTENT_REFRESH` (off by default: large downloads) |

Vocabulary audio is also resolved/synthesized **on demand** by
`GET /api/v1/vocabulary/{id}/audio`, so a missing file never blocks a game.

Weekly habit that remains yours: glance at the strands meter and heatmap on
the Progress page.

### Manual fallback

Every job can be run by hand (`Ajustes → Mantenimiento` or
`POST /api/v1/admin/jobs/{name}/run`), and the underlying scripts still work
from `backend/`:

```bash
python scripts/etl/fetch_sources.py --refresh
python scripts/etl/build_lexicon.py && python scripts/etl/build_sentences.py
python scripts/etl/validate.py --stamp
python scripts/seed_content.py
python scripts/etl/coverage_report.py
```

## Milestones

| Transition | Bar |
|---|---|
| A0 → A1 | 300 mastered words (stability > 21 days) |
| A1 → A2 | 800 mastered words + one A1 story completed without the translation |
| A2 exit | ≈ the Open KNM list mastered (the real-world inburgering A2 bar) |

## Gamification knobs

- **Modo sereno** (Ajustes): hides XP and combos when you'd rather study
  without scores.
- **Streak freeze**: earned automatically every 7-day streak (max 1 banked);
  it silently bridges a single missed day.
- **Daily quests** are optional — skip them freely, there is no penalty.
