# job-postings

US vs China computer/software job postings by seniority, from WRDS Revelio COSMOS (Princeton license).
WRDS data stay on this machine: `data/` and `*.parquet` are git-ignored. Only code, docs and figures are committed.

| file | what |
|---|---|
| `01_swe_by_seniority.py` | server-side GROUPING SETS pull, one month per query -> `data/agg/YYYY-MM.parquet` (resumable, 5 GB guard) |
| `02_descriptive.py` | figures -> `figures/`, yearly summary -> `data/summary/` |
| `docs/schema.md` | table schemas, access, seniority coding and validation, caveats |
| `tools/` | `db.py` (connection via ~/.pgpass), schema/seniority probes |

Status (2026-10-17): 105 months pulled (2018-01..2026-09; 2026-09 partial), 410 MB on disk.

Main caveats: COSMOS coverage expands sharply in 2021 (counts x4-8), so pre-2021 levels are not comparable;
China covers LinkedIn/Zhaopin/Liepin/51job only; seniority is model-predicted from titles; most salaries are predicted.
