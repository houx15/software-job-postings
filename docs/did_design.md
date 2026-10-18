# DiD / event-study design: AI and early-career software hiring (Revelio COSMOS postings)

Status: design memo, nothing here is estimated yet. Read it with `docs/rebound_diagnosis.md`: that memo shows the raw
early-career share is driven by source mix, big posters and seasonality, so every design below must neutralise those.

## 1. Question and estimand

Did generative-AI / AI-coding tools reduce firms' demand for early-career (Revelio seniority 1-2) software workers
relative to (a) experienced workers in the same jobs and (b) early-career workers in less-exposed jobs?
The outcome is **posted demand** (postings), not hires or employment.

Main outcome: `log(postings + 1)` in a cell, or the cell's early-career share. Cells:
country x occupation (O*NET 6/8-digit) x seniority group x month, and firm x seniority group x month.
Use PPML (`fepois`) for counts with many zeros (firm cells).

## 2. Related designs (all real, links checked 2026-10-18)

| Paper | Data | Treatment / comparison | Result | Status |
|---|---|---|---|---|
| Brynjolfsson, Chandar & Chen, "Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of AI" ([SIEPR WP, Aug 2025](https://siepr.stanford.edu/publications/working-paper/canaries-coal-mine-six-facts-about-recent-employment-effects-artificial); [Aug 2026 update](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf)) | ADP payroll (admin data, millions of US workers) | age group x occupation exposure quintile (Eloundou et al. GPT-4 β; Anthropic Economic Index automation vs augmentation); **firm x time FE** | Workers aged 22-25 in the most-exposed quintile: -13% relative employment (2025); 2026 update: 19% below counterfactual, mostly through lower hiring. Some pre-trends and attenuation once education is controlled | working paper |
| Hosseini Maasoum & Lichtinger, "Generative AI as Seniority-Biased Technological Change" ([SSRN 5425555](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5425555)) | **Revelio** résumés (62M workers, 285k firms) + postings | firm adopters = firms that post "GenAI integrator" roles (keywords + LLM classifier); DiD, triple-diff junior x adopter x post, staggered DiD | Junior employment in adopters falls from 2023Q1 relative to non-adopters; senior employment flat; driven by slower hiring | working paper (rev. Jun 2026) |
| Westby, Modestino & Cheng, "Generative AI and the Redefinition of Entry-Level Software Work" ([IZA DP 18723, Jun 2026](https://docs.iza.org/dp18723.pdf)) | Lightcast postings, SOC 15-1252 | junior (≤3 yrs required experience) vs senior, post Nov-2022; triple-diff vs other SOC-15; mechanical engineers as placebo | Junior software vacancies -14-15% relative to senior; experience requirements rise *within* titles | discussion paper |
| Humlum & Vestergaard, "Large Language Models, Small Labor Market Effects", now "Still Waters, Rapid Currents" ([NBER w33777](https://www.nber.org/papers/w33777)) | Danish adoption surveys linked to admin registers | worker/firm chatbot adoption (DiD) | Effects on earnings and hours are ≈0; effects >2% ruled out two years after ChatGPT; tasks and occupations reorganised | NBER WP |
| Hampole, Papanikolaou, Schmidt & Seegmiller, "Artificial Intelligence and the Labor Market" ([NBER w33509](https://www.nber.org/papers/w33509)) | Revelio-type résumés + postings, 2010-2023 | firm/task-level AI exposure built from postings text | Exposed tasks shrink; net employment effects small because of reallocation and productivity | NBER WP |
| Liu, Wang & Yu, "Labor Demand in the Age of Generative AI" ([World Bank PRWP 11263](https://doi.org/10.1596/1813-9450-11263)) | US postings | occupation exposure x post | early evidence of lower demand in exposed occupations | WB WP |

Exposure measures:
- Eloundou, Manning, Mishkin & Rock, "GPTs are GPTs", *Science* 384 (2024) ([doi](https://doi.org/10.1126/science.adj0998)); O*NET-SOC-level data in [openai/GPTs-are-GPTs `data/occ_level.csv`](https://github.com/openai/GPTs-are-GPTs) (α, β, ζ; human and GPT-4 ratings). Use β.
- Felten, Raj & Seamans, AIOE (*SMJ* 2021) plus the language-modeling AIOE ([arXiv 2303.01157](https://arxiv.org/abs/2303.01157)); data at [AIOE-Data/AIOE](https://github.com/AIOE-Data/AIOE).
- Webb, "The Impact of Artificial Intelligence on the Labor Market" ([SSRN 3482150](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3482150)). This is pre-LLM patent overlap, so use it as a placebo-type contrast: "old AI" exposure should *not* predict a post-2022 break.

Econometrics: Callaway & Sant'Anna (2021, *J. Econometrics*) and Sun & Abraham (2021) for staggered adoption; Borusyak, Jaravel & Spiess (2024, *REStud*) imputation; Roth (2022, *AER: Insights*) on pre-test power; Rambachan & Roth (2023, *REStud*) HonestDiD sensitivity bounds.

## 3. Designs

### Design A: occupation exposure x seniority x post (triple difference; the "Canaries" logic on postings)
```
log Y_{o,s,c,t} = Σ_k β_k · 1[t = k] · Exposure_o · Early_s
                + α_{o,s,c} + δ_{o,c,t} + γ_{s,c,t} + ε
```
- o = O*NET occupation (6-digit SOC; Revelio `onet_code`), s ∈ {early (1-2), experienced (3-4)}. Drop 5-7 or keep as a third group. c = country; t = month.
- **Treatment intensity**: Eloundou β (continuous, or top quintile vs bottom). Robustness: Felten LM-AIOE. Placebo: Webb pre-LLM AI exposure.
- **FE**: occupation x country x seniority (levels); **occupation x country x month** absorbs occupation-specific demand shocks such as the tech bust and rate sensitivity; seniority x country x month absorbs economy-wide junior/senior cycles, including campus-recruiting seasonality. β_k is then identified only from *differential early-vs-experienced changes in exposed vs unexposed occupations*.
- **Comparison groups**: (i) experienced workers in the same occupation; (ii) early-career workers in low-exposure occupations with similar pay and education: civil/mechanical/electrical engineers (17-2xxx), technicians, nurses (Westby et al. use mechanical engineers as a placebo); (iii) within computer occupations, lower-exposure codes (network/systems admin 15-1244, computer support 15-1232) versus software developers (15-1252), programmers (15-1251), web developers (15-1254). Variation in exposure inside 15-12xx is narrow, so (iii) is a weak design on its own.
- Weight cells by pre-period (2021-2022) postings; cluster SEs by occupation (≈700 clusters for all occupations, too few for 15-12xx only, so use wild-cluster bootstrap there).

### Design B: firm-level AI adoption (Hosseini & Lichtinger logic, using our text tags)
```
Y_{f,s,t} (PPML) = Σ_k β_k · 1[t - A_f = k] · Early_s + α_{f,s} + δ_{f,t} + γ_{s,t} (+ industry x s x t) + ε
```
- **Adoption proxy, two versions**:
  1. *Pre-period intensity* (continuous, fixed): share of a firm's 2021-06..2022-10 computer postings that mention Copilot / AI pair-programming / ML tooling (our `03` tags are already defined). Then estimate continuous-treatment DiD with one event at ChatGPT (2022-11-30). Weakness: almost no firm mentions LLM tools before late 2022 (our LLM tag is ~0 pre-2023), so this mostly picks up "AI-forward" firms (ML-heavy firms).
  2. *Staggered adoption date* A_f: first month in which the firm posts ≥2 postings that mention LLM/GenAI tools (Copilot, Cursor, Claude Code, ChatGPT, LLM, 大模型, AIGC...) **in non-AI-engineer roles**, which is a proxy for "the firm uses AI tools" and not "the firm builds AI". Better: replicate the "GenAI integrator" classifier (keyword + LLM verify). Estimate with Callaway-Sant'Anna or Sun-Abraham, not-yet-treated firms as controls.
- **FE**: firm x month absorbs firm-wide hiring shocks (rate hikes, layoffs, a firm's business cycle). This is the key advantage over aggregates, and it mirrors the Canaries firm-time FE. Firm x seniority absorbs each firm's standing junior intensity.
- Reverse-causality risk: firms that cut juniors may *then* advertise AI tools. Use the pre-period intensity version and leads (k<0) as a check.

### Design C: event study around discrete tool shocks (aggregate, descriptive)
Copilot GA (2022-06-21), ChatGPT (2022-11-30), GPT-4 (2023-03-14), Claude Code GA / agentic coding (2025-05-22), OpenClaw mania (2026-01-30); China: DeepSeek-R1 (2025-01-20), Trae, 通义灵码 (see `docs/ai_events.csv`). Use as k=0 in A/B (ChatGPT as the main date, agentic-coding 2025-05 as a second "dose"). On its own, a single national time series cannot separate AI from macro shocks, so Design C is **only** an input to A/B.

## 4. Seasonality
- Campus cycles are large: China 秋招 (Aug-Nov), 春招 (Feb-Apr); US new-grad and intern postings in Aug-Oct. See `rebound_diagnosis.md`.
- In A/B, seniority x country x **calendar month** (absorbed by γ_{s,c,t}) handles it as long as seasonality is common across occupations and firms. Add *occupation x seniority x month-of-year* FE to allow occupation-specific campus cycles (software is more campus-heavy than nursing).
- For descriptive series, use YoY differences or the month-of-year-adjusted series from `08_rebound_diagnosis.py`, never raw quarter-to-quarter changes.

## 5. Source-composition controls (essential in Revelio COSMOS)
- The share of the panel coming from each source moves a lot. In China in particular, Zhaopin, 51job and Liepin enter and exit, and they have very different seniority mixes from LinkedIn (see the diagnosis).
- Options, best first:
  1. **Fixed-source panel**: define the outcome on postings carrying `source_linkedin` only (both countries) as the main sample; CN boards as a separate China sample; never pool across a source break.
  2. Cell x source-bucket outcomes with **source x seniority x month FE**.
  3. Reweight to fixed 2021-2022 source shares (shift-share reweighting).
- Drop or separately flag staffing/outsourcing parents (Diverse Lynx, Allegis, Insight Global, 法本, 中软国际, FESCO Adecco …): in 2023Q1 they are large and senior-heavy (see diagnosis). Run the analysis with and without them.
- Pre-2021 COSMOS coverage is thin (China especially), so start the panel in **2021-01**. That gives a pre-period of 22 months before ChatGPT. It is short, and it overlaps the 2021-22 hiring boom.

## 6. Pre-trend tests and inference
- Plot β_k for k ∈ [-18, +36] months (or quarters). Joint F-test on leads. Report Roth (2022) power for the pre-test, and HonestDiD (Rambachan-Roth) bounds that allow linear pre-trends to continue.
- Placebo dates (e.g. fake treatment at 2021-11 or 2022-05); placebo exposure (Webb pre-LLM AI exposure); placebo occupations (mechanical/civil engineers).
- Cluster by occupation (A) or firm (B); for few-cluster cuts use wild bootstrap.

## 7. Threats to validity
1. **Coincident macro shock**: the 2022-23 rate hikes and tech layoffs hit exactly at ChatGPT. Firm x month and occupation x month FE help only if the shock is not itself junior-biased *within* firm/occupation. Recessions are known to raise posted requirements ("upskilling": Modestino, Shoag & Ballance 2020, *REStat*). Control: interact Early_s x a pre-period rate-sensitivity or tech-bust proxy (e.g. 2022H2 posting drop of the firm).
2. **Post-COVID normalisation**: the 2021-22 junior hiring boom was unusual; a reversion looks like a negative effect. Test the pre-trend from the 2019 baseline where coverage allows (US only).
3. **China-specific shocks**: platform regulation (2021-22), 2022 lockdowns, youth unemployment, the 2023 statistics change, the 35-year-old ceiling, 2025 hiring subsidies. China results need their own design (CN boards vs LinkedIn-China separately).
4. **Seniority measurement**: Revelio's seniority is model-predicted from title/description. If firms re-title roles (e.g. drop "junior" to signal AI-era expectations), measured seniority moves without real demand change. Validate with title keywords (`07_title_kw_pull.py`) and, for the US, required-years-of-experience extracted from descriptions (new pull).
5. **Postings ≠ hires**: ghost and evergreen postings, reposting. Use `remove_date - post_date` duration, and dedup by `job_id`; compare to Revelio workforce hires if licensed (not in our WRDS subscription).
6. **Offshoring and outsourcing**: junior work moving to India or contractors would look like an AI effect. Partly visible through staffing parents and countries outside our pull.
7. **Treatment measurement**: exposure measures rate *tasks*, not adoption; a firm's AI-tool mentions measure *advertised* adoption.

## 8. Feasibility with current aggregates vs. new pulls

| Piece | Have now? | Notes |
|---|---|---|
| Aggregate early share, seasonality, source mix | yes: `data/agg`, `data/sources` (06), `data/titlekw` (07) | descriptive only |
| Design A within 15-12xx (≈10 codes) | partly: `data/agg` has onet x seniority x month for 15-12xx | too little exposure variation and too few clusters |
| Design A across all occupations | **new pull P1** | month x country x O*NET (6-digit) x seniority x source bucket (LinkedIn-only / CN board / other), 2019-01..2026-09. About 800 occ x 7 x 2 x 4 x 93 months, which is small (<200 MB). Then merge Eloundou β, Felten LM-AIOE, Webb via O*NET-SOC (crosswalk 2010→2019 SOC if needed) |
| Design B firm panel | **new pull P2** | month x ultimate_parent_rcid x seniority group x occ group (computer / exposed non-computer / low-exposure) x source bucket; keep firms with ≥50 pre-period postings. One scan per month, as in 01 |
| Firm adoption proxy | **new pull P3** | per firm x month: count of postings mentioning AI tools in non-AI roles (sampled description regex like 03, or full scan over a smaller firm set), plus "integrator" roles; 2021-01..2026-09 |
| Experience requirements (US) | new pull P4 (optional) | regex "(\d+)\+? years" in descriptions, by seniority/occ/month, to validate the seniority model |

Disk: P1+P2 at parquet ≈ 1-2 GB in total; that is inside the 10 GB cap (data now ≈0.4 GB).

Recommended order: P1 (cheap, enables Design A for both countries) → P2 (firm x month FE) → P3 (treatment timing).
