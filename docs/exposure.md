# Occupation AI-exposure measures and crosswalk to Revelio O*NET codes

Built by `tools/build_exposure.py` (downloads into git-ignored `data/exposure/raw`, writes `data/exposure/exposure_soc6.csv`).

| Measure | Source (public) | Native codes | What it measures |
|---|---|---|---|
| Eloundou β (GPT-4 rater; also human rater, α, γ) | Eloundou, Manning, Mishkin & Rock, *Science* 384 (2024), [doi](https://doi.org/10.1126/science.adj0998); data [`openai/GPTs-are-GPTs/data/occ_level.csv`](https://github.com/openai/GPTs-are-GPTs) | O*NET-SOC 2019, 8-digit (923 codes; O*NET 27.2 tasks) | share of tasks where an LLM (β = E1 + 0.5·E2, i.e. LLM alone or with complementary software) cuts time by ≥50% |
| Felten LM-AIOE | Felten, Raj & Seamans (2023), [arXiv 2303.01157](https://arxiv.org/abs/2303.01157); data [`AIOE-Data/AIOE`](https://github.com/AIOE-Data/AIOE) "Language Modeling AIOE and AIIE.xlsx" | SOC 2010, 6-digit (774) | O*NET abilities weighted by relevance to the language-modelling AI application |
| Felten AIOE | Felten, Raj & Seamans, *SMJ* 42(12) 2021, [doi](https://doi.org/10.1002/smj.3286); `AIOE_DataAppendix.xlsx`, Appendix A | SOC 2010, 6-digit | the same ability approach over 10 AI applications (EFF progress metrics, pre-LLM) |
| Felten image-generation AIOE | same repo, "Image Generation AIOE and AIIE.xlsx" | SOC 2010, 6-digit | contrast measure (a less coding-relevant technology) |
| **Webb pct_ai** | Webb (2020), [SSRN 3482150](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3482150) | occ1990dd | **Not used: no public download.** The author's data page only hosts patent-replication files; others (e.g. EIG's [AI-unemployment](https://github.com/EIG-Research/AI-unemployment)) list `exposure_by_occ1990dd_lswt2010.csv` as obtained privately. Mapping occ1990dd→SOC 2018 would also need a CPS-weighted crosswalk. The Webb placebo is therefore replaced by a placebo-in-time test (fake event 2022Q1). |

## Crosswalk
- Revelio `onet_code` is O*NET-SOC 2019 8-digit (e.g. `15-1252.00`; 1,010 codes in P1). The regression unit is the **SOC-2018 6-digit** code (`onet_code[:7]`), because Felten is 6-digit and many 8-digit O*NET codes are small.
- Eloundou: averaged (unweighted) across the 8-digit codes within each 6-digit code; 923 → 798 codes.
- Felten: SOC-2010 6-digit → O*NET-SOC 2010 → O*NET-SOC 2019 using the official [O*NET 2010→2019 crosswalk](https://www.onetcenter.org/taxonomy/2019/walk.html) → 6-digit; many-to-many cells are averaged; 774 → 802 codes.
- Each measure is z-scored across scored occupations (unweighted) before entering regressions.
- Coverage of postings in P1 (2021-01..2026-09): US 850.6M postings, 94.6% in occupations with an Eloundou score (94.8% Felten); China 247.2M, 92.4%. Unmatched postings are mostly "All other" residual codes (35-2019, 39-9099, 43-9199, …) and `unknown`.
- Correlations across 6-digit occupations: Eloundou β (GPT-4) vs human β 0.88; vs Felten AIOE 0.83; vs Felten LM-AIOE 0.81; vs image-generation AIOE 0.72. All measures largely rank "white-collar cognitive" vs "manual" jobs, so they **cannot separate LLM exposure from general white-collar exposure** (this matters for the placebo; see designA_results.md).
