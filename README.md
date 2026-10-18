# job-postings

US vs China computer/software job postings by seniority, from WRDS Revelio COSMOS (Princeton license).
WRDS data stay on this machine: `data/` and `*.parquet` are git-ignored. Only code, docs and figures are committed.

| file | what |
|---|---|
| `01_swe_by_seniority.py` | server-side GROUPING SETS pull, one month per query -> `data/agg/YYYY-MM.parquet` (resumable, 5 GB guard) |
| `02_descriptive.py` | figures -> `figures/`, yearly summary -> `data/summary/` |
| `03_stack_language_tags.py` / `04_stack_figures.py` | stack & language regex tags (sampled, server-side) and figures; see `docs/stack_tags.md` |
| `05_event_overlay.py` | AI-coding/LLM milestones (`docs/ai_events.csv`, sourced) overlaid on quarterly series + before/after table (descriptive) |
| `06_source_pull.py` | source-flag composition (LinkedIn / Zhaopin / 51job / Liepin / Indeed / company sites …), month x country x seniority, full count → `data/sources/` |
| `07_title_kw_pull.py` | title keywords (intern/junior/senior+) x Revelio seniority, sampled → `data/titlekw/` (seniority-model check) |
| `08_rebound_diagnosis.py` | early-career share dip/rebound decomposition (numerator/denominator, source shift-share, big posters, seasonality) → `figures/rebound_*.png`, `docs/rebound_diagnosis.md` |
| `docs/did_design.md` | DiD / event-study design memo for AI and early-career software hiring |
| `docs/schema.md` | table schemas, access, seniority coding and validation, caveats |
| `tools/` | `db.py` (connection via ~/.pgpass), schema/seniority probes |

Status (2026-10-17): 105 months pulled (2018-01..2026-09; 2026-09 partial), 410 MB on disk.

Main caveats: COSMOS coverage expands sharply in 2021 (counts x4-8), so pre-2021 levels are not comparable;
China covers LinkedIn/Zhaopin/Liepin/51job only; seniority is model-predicted from titles; most salaries are predicted.
