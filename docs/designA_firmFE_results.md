# Design A with firm fixed effects (P2 firm-level panel)

Code: `11_firm_list_pull.py`, `12_firm_panel_pull.py` (P2), `13_designA_firmFE.py`, `tools/honest_bounds.py`.
Full tables: `docs/designA_firmFE_tables.md` (generated). Figures: `figures/designA_firmFE_1_event_us.png`,
`_2_honest_sd.png`, `_2_honest_sd_fst.png`, `_3_honest_rm.png`, `_3_honest_rm_fst.png`, `_4_event_china.png`.

**Short version.** Adding firm fixed effects does not change the occupation-level conclusion: there is no identified AI effect on
early-career postings. Firm x quarter FE leave the estimates unchanged (mechanically, see below). Firm x seniority x quarter FE
move them a little. All event studies show a strong, exposure-graded decline of early-career postings during 2021-22, i.e.
before ChatGPT; the pre-trend test rejects at p < 0.001. After 2022Q3 the relative path is flat through 2024, then drifts
down by about 5-10 log points per SD of exposure by 2026Q2. The Rambachan-Roth bounds include zero for any non-trivial
departure from a linear trend. At exact linear continuation (M = 0), the sign depends on which pre-period slope is extrapolated.

## Data and sample
- **P2 pull.** Server-side counts of firm (`ultimate_parent_rcid`) x month x seniority group (early = 1-2, experienced = 3-4)
  x SOC 6-digit occupation x source group (li_only / cn_board / other), US and China, 2021-01..2026-09. 69 monthly files,
  420 MB. About 20-30 s per month.
- **Firm list.** Firms with >= 50 postings at seniority 1-4 in 2021-01..2022-10:
  - US: 205,387 of 1.60M firms, 94.2% of pre-period postings.
  - China: 61,344 of 199k firms, 92.5%.
- **Estimation cells.** Firm x occupation pairs with >= 10 pre-period (2021Q1-2022Q3) postings in *each* seniority group.
  The panel is balanced with zeros over 2021Q1-2026Q2; 2026Q3 is partial and dropped. The outcome is log(1+n).
  - US all sources: 54,699 firms, 733 occupations, 254,652 pairs, 11.2M cells, 321M postings.
  - US LinkedIn-only: 24,046 firms, 121,676 pairs, 5.35M cells.
  - China, CN boards: 5,141 firms, 16,293 pairs. Descriptive only.
  - The cut is 10 rather than 5 because 5 gives 20M cells, which is too much for 16 GB of RAM.
- **Exposure.** E = Eloundou GPT-4 beta, z-scored. Post = 2023Q1+, Post2 = 2025Q3+ (increment).
- **Standard errors.** Clustered by occupation.

## Pooled triple difference (Early x E x Post)
| Specification | Post (2023Q1+) | Post2 increment (2025Q3+) |
|---|---|---|
| Main: f^t + o^t + o^s + s^t | -0.070* (0.037) | -0.066*** (0.025) |
| f^t + o^s + s^t (as specified, E x Post controls) | -0.070* (0.037) | -0.066*** (0.025) |
| No firm FE, same sample | -0.070** (0.035) | -0.066*** (0.024) |
| + firm x occ x seniority FE | -0.070* (0.037) | -0.066*** (0.025) |
| **firm x seniority x quarter FE** | -0.046 (0.033) | -0.091*** (0.027) |
| Two-way cluster occupation + firm | -0.070** (0.035) | -0.066*** (0.024) |
| LinkedIn-only | -0.056** (0.023) | +0.082*** (0.018) |
| LinkedIn-only, f x s x t FE | -0.095*** (0.020) | +0.053*** (0.019) |
| Excluding staffing parents | -0.070* (0.037) | -0.065** (0.026) |
| Excluding staffing, f x s x t FE | -0.044 (0.033) | -0.091*** (0.028) |
| Felten LM-AIOE | -0.046 (0.034) | -0.076** (0.031) |
| Cells >= 20 per seniority group | -0.099** (0.043) | -0.089*** (0.034) |
| YoY log change | +0.111* (0.063) | -0.017 (0.024) |
| YoY, f x s x t FE | +0.082 (0.057) | -0.032 (0.021) |
| **Placebo: fake event 2022Q1, data to 2022Q3** | **-0.139*** (0.052)** | |
| China CN boards (to 2025Q2) | +0.040*** (0.012) | n/a |

How to read the table:
- **Why firm x quarter FE change nothing.** The panel is balanced and every firm x occupation x quarter contains both
  seniority cells, so firm x quarter FE are orthogonal to Early x E x Post. The same holds for the firm x occupation x seniority
  cell FE. The substantive within-firm control is **firm x seniority x quarter**. It absorbs any firm-wide change in the
  junior/senior mix, such as a junior hiring freeze or a new campus programme, and leaves only variation across a firm's own
  occupations of different exposure. It lowers Post to -0.046 (not significant) and raises Post2 to -0.091.
- **Post is not interpretable as an effect.** The placebo "event" in 2022Q1, before ChatGPT, is larger (-0.139) than the
  real one. The YoY version, which removes level differences and the seasonal pattern, is positive or zero.
- **The LinkedIn-only Post2 has the opposite sign** to all sources (+0.08 vs -0.07). The late-period result therefore depends
  on source composition: company-site and aggregator postings grew after 2025 (`docs/rebound_diagnosis.md`). It is not a
  robust finding.

## Event study (ref 2022Q3) and pre-trends
- **Pre-trend.** The leads (2021Q1..2022Q2) fall monotonically from +0.20 (0.07) to -0.01 (0.01): early-career postings in
  exposed occupations were already falling about 4-5 log points per SD per quarter in 2021, and the decline levelled off in
  2022. The joint Wald test on the 6 leads is chi2 = 151.5 (p < 1e-25). With firm x seniority x quarter FE it is 69.2;
  LinkedIn-only 80.6; ex-staffing 146.0; China 18.1 (p = 0.006).
- **Post path (all sources, firm FE).**
  - 2022Q4 +0.053 (0.033), 2023Q1 +0.037 (0.038).
  - 2023Q2-Q3 is noisy, with SE up to 0.15. This is the Jan-Feb 2023 seniority-3 spike documented in the rebound diagnosis.
  - 2024: about 0.
  - 2025Q2 -0.057 (0.060), 2025Q3 -0.060 (0.060), 2026Q2 -0.077 (0.049).
  - With f x s x t FE, 2026Q2 is -0.101 (0.042).
  - LinkedIn-only rises to +0.092 (0.039) by 2026Q2.
- **Firm FE vs no firm FE** coincide (see the figure). Composition across firms is not what drives the occupation-level pattern.

## Rambachan-Roth honest DiD
Method: Python port `honestdid` 0.1.1, run in the separate venv `~/.venvs/honestdid` (needs torch and cvxpy).
- **Local patches.**
  - `float()` on 1x1 numpy-2 arrays failed; it is replaced by a scalar-safe `_sc()`. The original file is kept as `core.py.orig`.
  - The default relative-magnitude grid (±20 SE around 0) truncated the sets, so the grid is passed explicitly.
- **Sanity check.** On synthetic data with an exactly linear pre-trend and zero effect, the M = 0 interval is centred on 0.
- **Restrictions.**
  - Delta^SD(M): smoothness. M = 0 means the pre-trend continues exactly linearly; M bounds the change in slope per quarter.
  - Delta^RM(Mbar): post-period violations at most Mbar times the largest pre-period violation.
- **Targets.** 2023Q1; the average over 2023Q1-2026Q2; the average over 2025Q3-2026Q2.
- **M grid.** {0, 0.25, 0.5, 1} x the largest observed second difference of the leads (0.078 for the main spec).
- **Own cross-check.** Closed-form identified sets plus or minus 1.96 SE, for last-slope and regression-slope extrapolation and
  for RM. These are in the generated tables.

95% sets, main spec (all sources, firm FE):
| Target | Original | SD, M = 0 | SD, M = 0.02 | RM, Mbar = 0.25 | RM, Mbar = 1 |
|---|---|---|---|---|---|
| 2023Q1 | [-0.039, 0.112] | [-0.006, 0.048] | [-0.109, 0.095] | [-0.065, 0.156] | [-0.150, 0.296] |
| avg 2023Q1-26Q2 | [-0.142, 0.125] | [-0.009, 0.154] | [-1.19, 0.98] | [-0.25, 0.34] | [-0.76, 0.95] |
| avg 2025Q3-26Q2 | [-0.159, 0.048] | [+0.031, 0.248] | [-2.30, 1.92] | [-0.35, 0.39] | [-1.34, 1.37] |

The same sets with firm x seniority x quarter FE:
| Target | Original | SD, M = 0 | SD, M = 0.023 | RM, Mbar = 0.25 |
|---|---|---|---|---|
| 2023Q1 | [-0.032, 0.106] | [-0.037, 0.001] | [-0.150, 0.077] | [-0.051, 0.153] |
| avg 2023Q1-26Q2 | [-0.124, 0.110] | [-0.260, -0.117] | [-1.45, 1.07] | see tables |
| avg 2025Q3-26Q2 | [-0.160, 0.015] | [-0.338, -0.145] | [-2.71, 2.22] | see tables |

LinkedIn-only (firm FE), SD with M = 0:
- 2023Q1 [-0.036, 0.012]
- avg 2023Q1-26Q2 [-0.005, 0.098]
- avg 2025Q3-26Q2 [+0.045, 0.205]

Reading the bounds:
1. **Only M = 0 excludes zero, and the sign depends on the slope used.** With exact linear continuation, the main
   spec gives a *positive* late effect (+0.03..+0.25): the junior decline slowed relative to trend. The f x s x t
   spec gives a *negative* one (-0.34..-0.15).
   - The FLCI weights the precise lead next to the reference quarter heavily.
   - Our extrapolations confirm the sensitivity. The last-slope version (2022Q2→Q3, slightly upward) gives -0.19 / -0.24.
     The regression slope through all six leads (the steep 2021 decline) gives +0.36 / +0.26.
   - The pre-trend is clearly non-linear: steep in 2021, flat in 2022, with a largest second difference of 0.08-0.09.
     M = 0 is therefore not credible.
2. **Everything else includes zero.** With M at a quarter of the observed curvature, or Mbar >= 0.25, every interval
   includes 0. The 14-15 post quarters make the smoothness sets explode, to ±1-2 log points for the averages.
   - Breakdown value: 0 for every target and spec except at exactly M = 0.

## Did conclusions change vs occupation-level Design A (`docs/designA_results.md`)?
No. The occupation-level US LinkedIn-only results were:
- main -0.070 (0.017) / -0.148 (0.021);
- pre-trend F = 132;
- placebo -0.087;
- linear-trend-adjusted +0.15 / +0.03.

The firm-level panel reproduces the same strong pre-ChatGPT exposure gradient in the junior decline within firm and
occupation. It gives a similar Post coefficient that is again matched or beaten by the placebo. The post-2025 term is not
robust: its sign depends on source group, and it is wiped out by honest bounds. Within-firm controls do not create an effect
and do not remove the pre-trend.

Two differences from the occupation level:
1. With firm x seniority x quarter FE, the late-period decline is somewhat larger: 2026Q2 is -0.10 (0.04).
2. LinkedIn-only firm-level postings move the *other* way after 2025.

Neither is identified given the pre-trends.

## Measurement caveats
- **Seniority** is Revelio's model-based title classification. There was a re-coding spike in Jan-Feb 2023, which is why the
  reference quarter is 2022Q3.
- **China.** The boards re-coded seniority in 2023 (Zhaopin 2023-10, 51job 2023-01, Liepin 2023Q4) and disappear after
  2025Q3, so China results are descriptive only.
- **Sample selection.** Restricting to firm x occupation pairs with junior and senior postings before 2022 selects stable,
  large employers. Entry and exit margins (new firms, firms that stop hiring juniors entirely) are outside this design.
- **The outcome is postings, not hires.** Ghost or reposted ads and changes in source coverage remain. That is why the
  LinkedIn-only robustness check matters.
