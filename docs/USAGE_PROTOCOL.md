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

## Weekly

- Sunday: export your progress (`Ajustes → Exportar progreso`) as a backup,
  and glance at the strands meter and the activity heatmap.

## Monthly content refresh

```bash
cd backend
python scripts/etl/fetch_sources.py --refresh
python scripts/etl/build_lexicon.py
python scripts/etl/build_sentences.py
python scripts/populate_content.py            # LLM gap-fill only where coverage shows holes
python scripts/etl/validate.py --stamp
python scripts/seed_content.py                # also regenerates ATTRIBUTIONS.md
python scripts/etl/coverage_report.py
```

Regenerate stories against your updated known-word profile (keeps input at
i+1 as your vocabulary grows). Run the FSRS optimizer once ~1,000 review logs
exist (they're recorded automatically and included in every export); re-run
quarterly.

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
