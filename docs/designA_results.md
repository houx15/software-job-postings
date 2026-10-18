# Design A results: early vs experienced x occupation AI exposure x post (US LinkedIn-only)

Code: `09_occ_panel_pull.py` (P1), `tools/build_exposure.py`, `10_designA.py`. Design: `docs/did_design.md`; measures: `docs/exposure.md`.
Figures: `figures/designA_1_event_us.png`, `designA_2_event_software_china.png`, `designA_3_raw_terciles.png`.

**Short version.** Postings for early-career workers fall relative to experienced workers more in AI-exposed occupations. The
estimate is about −7 log points per SD of exposure after ChatGPT, and a further −15 after 2025Q3. **But the divergence was
already under way in 2021-22.** The leads are large (joint pre-trend test p<0.001). A placebo "event" in 2022Q1 gives an
effect as large as the real one (−0.087). Allowing a differential linear trend flips the post-ChatGPT term to +0.15 and makes
the agentic term ≈0. The year-over-year specification is null. So with these data the design **does not identify an AI effect**.
What it shows is a steady, exposure-graded decline in early-career posting demand from 2021 to 2026, with no clear break at
ChatGPT. The 2025-26 decline is somewhat steeper than in 2023-24, but it is not distinguishable from trend.

## Data and specification
- P1: Revelio COSMOS `postings_cosmos`, all occupations, US + China, 2021-01..2026-09, month x country x O*NET code x seniority x source group (LinkedIn-only / LinkedIn+other / CN boards / other) x staffing flag. Full count, server-side; 1.10B postings, 6 MB parquet.
- Main sample: **US, LinkedIn-only postings** (28.7% of US postings; the most stable source over time, see `rebound_diagnosis.md`). 2021Q1-2026Q2 (22 quarters; 2026Q3 is partial).
- Cell: SOC-2018 6-digit occupation x {early = Revelio seniority 1-2, experienced = 3-4} x quarter. Occupations with ≥50 pre-period (2021Q1-2022Q3) postings in each group: **729 occupations, 32,076 cells, 222.6M postings**. Outcome log(n+1).
- `log y_ost = β1·Early_s·E_o·Post_t + β2·Early_s·E_o·Post2_t + FE(o×t) + FE(s×t) + FE(o×s)`. E = z-scored exposure. Post = 2023Q1+ (ChatGPT 2022-11-30). Post2 = 2025Q3+ (Claude Code GA 2025-05-22, "agentic coding"), additional to Post. SE clustered by occupation.
- β1 < 0 means: after ChatGPT, early-career postings fell relative to experienced postings by 100·β1 log points more per SD of exposure.

## Main table (coefficient, SE clustered by occupation; *** p<.01, ** p<.05, * p<.1)
| Specification | Early x E x Post-ChatGPT | Early x E x Post-agentic (extra) | occs | obs |
|---|---|---|---|---|
| **Main: Eloundou β (GPT-4), z** | **-0.070*** (0.017)** | **-0.148*** (0.021)** | 729 | 32,076 |
| Eloundou β (human raters) | -0.076*** (0.017) | -0.151*** (0.021) | 729 | 32,076 |
| Felten LM-AIOE | -0.093*** (0.018) | -0.188*** (0.022) | 733 | 32,252 |
| Felten AIOE (2021, pre-LLM) | -0.087*** (0.019) | -0.192*** (0.022) | 733 | 32,252 |
| Felten image-generation AIOE (contrast) | -0.063*** (0.019) | -0.175*** (0.020) | 733 | 32,252 |
| Excluding staffing/outsourcing parents | -0.069*** (0.018) | -0.156*** (0.021) | 724 | 31,856 |
| + occupation x seniority x quarter-of-year FE | -0.071*** (0.018) | -0.147*** (0.021) | 729 | 32,076 |
| Weighted by pre-period postings | -0.094*** (0.035) | -0.177*** (0.038) | 729 | 32,076 |
| Sample from 2022Q1 | -0.057*** (0.017) | -0.148*** (0.021) | 729 | 26,244 |
| Drop 2022Q4-2023Q1 (seniority-spike quarters) | -0.084*** (0.019) | -0.110*** (0.020) | 729 | 29,160 |
| Large occupations only (≥2,000 pre postings per group) | -0.056** (0.027) | -0.128*** (0.033) | 332 | 14,608 |
| Binary: top vs bottom exposure quartile | -0.186*** (0.049) | -0.340*** (0.057) | 376 | 16,544 |
| Treatment = software developers (15-1251..54) vs rest | -0.193 (0.135) | -0.189*** (0.050) | 729 | 32,076 |
| Outcome = early share (pp); E x Post, occ + quarter FE | -1.66*** (0.24) | -2.38*** (0.25) | 729 | 16,037 |
| **Checks that undermine a causal reading** | | | | |
| + differential linear trend (Early x E x t) | +0.152*** (0.024) | +0.025 (0.026) | 729 | 32,076 |
| Outcome = YoY log change (from 2022Q1) | -0.027 (0.021) | -0.017 (0.027) | 729 | 26,244 |
| Placebo in time: fake event 2022Q1, sample 2021Q1-2022Q3 | -0.087*** (0.018) | – | 729 | 10,206 |
| All US sources pooled (LinkedIn-only + LI+other + other) | +0.041*** (0.012) | -0.241*** (0.023) | 768 | 33,792 |
| China LinkedIn-only (descriptive) | -0.193*** (0.022) | -0.160*** (0.024) | 730 | 32,120 |
| China Zhaopin/51job/Liepin (descriptive, to 2025Q3) | -0.005 (0.018) | -0.082*** (0.029) | 705 | 26,790 |

## Event study (main; Early x E x quarter, ref 2022Q4; same FE)
Pre-trend joint Wald test on the 7 leads (2021Q1-2022Q3): **F = 132.5, p < 0.001**. Felten LM-AIOE: F = 207.4. Ex staffing: F = 129.7. Software dummy: F = 321.9. China LinkedIn: F = 62.1. China boards: F = 225.6 (all p < 0.001).

| 21Q1 | 21Q2 | 21Q3 | 21Q4 | 22Q1 | 22Q2 | 22Q3 | **22Q4** | 23Q1 | 23Q2 | 23Q3 | 23Q4 | 24Q2 | 24Q4 | 25Q2 | 25Q3 | 26Q1 | 26Q2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -0.061 | -0.123 | -0.177 | -0.249 | -0.250 | -0.310 | -0.158 | 0 | +0.103 | -0.113 | -0.157 | -0.302 | -0.337 | -0.310 | -0.345 | -0.372 | -0.367 | -0.434 |

(SEs 0.018-0.044; full series in git-ignored `docs/designA_event.csv`.)

Averages of event coefficients by window (log points per SD of exposure):
| Series | 2021 | 2022Q1-Q3 | 2023Q2-2024Q4 | 2025Q3-2026Q2 |
|---|---|---|---|---|
| US LinkedIn-only, Eloundou β | -0.152 | -0.239 | -0.263 | -0.384 |
| US LinkedIn-only, Felten LM-AIOE | -0.141 | -0.244 | -0.286 | -0.444 |
| US LinkedIn-only, ex staffing | -0.172 | -0.250 | -0.273 | -0.405 |
| US, software occs vs rest (dummy, not per SD) | -0.315 | -0.448 | -0.548 | -0.708 |
| China LinkedIn-only (descriptive) | -0.050 | -0.095 | -0.255 | -0.414 |
| China CN boards (descriptive; ends 2025Q3) | -0.115 | -0.017 | -0.041 | -0.150 (Q3 only) |

## Interpretation
1. **The reference quarter is abnormal.** 2022Q4-2023Q1 is a V-shaped spike in every exposure tercile (fig 3). This is the same Jan-Feb 2023 Revelio seniority-3 spike found in `rebound_diagnosis.md`. Low-exposure occupations swing the most. A pre/post DiD with 2022Q4 inside it is driven by this artefact. Dropping those two quarters changes little (-0.084 / -0.110), but the event study needs to be read against 2022Q1-Q3, not 2022Q4.
2. **Pre-trend.** Comparing 2022Q1-Q3 with 2023Q2-2024Q4, the exposure-graded gap widens by only ≈0.02-0.04 per SD. That is *smaller* than the 2021→2022 widening before ChatGPT (≈0.09). Between 2023-24 and 2025Q3-2026Q2 it widens by a further ≈0.12-0.16 per SD; this is the only visible acceleration. Even so, a linear trend fitted through the whole period absorbs it (agentic term +0.025, SE 0.026).
3. **The placebo fails** (fake 2022Q1 event = -0.087***), and Felten's pre-LLM AIOE and image-generation AIOE give the same answers as the LLM-specific measures. These measures all rank white-collar cognitive jobs high (correlations 0.72-0.88). They therefore pick up *any* white-collar-specific junior-hiring shock, such as the 2022-23 tech and professional-services bust, rate sensitivity or offshoring, not only LLMs. Webb's patent-based measure would be the natural "old AI" placebo, but it is not public.
4. **Source sensitivity.** Pooling all US sources flips the ChatGPT term to +0.041, because company-site and aggregator postings grow fast in 2024-26 and have a different seniority mix. This is why LinkedIn-only is the main sample, but it also shows the estimates are fragile.
5. **Software developers** (15-1251..54) vs all other occupations: about -0.10 to -0.25 relative to 2022 after ChatGPT (event study 2022Q1-Q3 avg -0.45 → 2023Q2-24Q4 avg -0.55 → 2025-26 -0.71). This direction matches Brynjolfsson-Chandar-Chen and Westby et al. The pooled post coefficient is imprecise, though (-0.193, SE 0.135), and it also has strong pre-trends.
6. **China** is descriptive only. LinkedIn-China shrinks and is selected after InCareer's exit (2023-08). The Zhaopin/Liepin/51job seniority labels re-code in 2023-01 and 2023-10 and the boards vanish in 2025-10. Both China series show exposure-graded early-career declines, but they cannot be interpreted causally.

## Caveats
- Outcome is postings, not hires. Seniority is Revelio's model, which has dated discontinuities.
- The pre-period is short (7 quarters) and sits in the 2021-22 hiring boom and LinkedIn coverage ramp-up. COSMOS before 2021 is unreliable, so 2019-20 cannot be used to stretch it.
- Inference: occupation clusters (729) are fine for the main spec, but the software-dummy spec effectively has 4 treated clusters, so its SE is unreliable (use wild bootstrap or randomization inference if pursued).
- Not done: HonestDiD (Rambachan-Roth) bounds; Callaway-Sant'Anna (the treatment is not staggered here); firm x month FE (needs P2).

## What would make this credible
1. **P2 (firm x month x seniority x occupation-group)**: firm x time FE absorbs the tech-bust and rate shocks hitting AI-exposed white-collar employers; this is the Canaries / Hosseini-Lichtinger approach.
2. A within-white-collar comparison: restrict to occupations with similar education and wage and compare high vs low LLM exposure *within* them. Or use the Anthropic Economic Index automation-vs-augmentation split as a sharper dose than generic exposure.
3. HonestDiD bounds allowing the 2021-22 slope to continue; report the breakdown value M̄.
4. A required-years-of-experience outcome (P4) to bypass Revelio's seniority model.
