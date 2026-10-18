# Is the Design A null a data limitation or the true result?

**Verdict: mainly a data limitation of job postings, the outcome variable, not evidence of a true null.** The same Revelio
data, measured as *hires* from profiles (`individual_positions`), give flat pre-trends from 2019 to 2023Q2 and a clear,
exposure-graded junior decline from 2023Q3. Hires also reproduce the published adopter-firm result (Hosseini Maasoum &
Lichtinger). Postings fail on three independent counts:
1. **Power.** The MDE is at or above the effect sizes in the literature, and far above it once the pre-trend is allowed for.
2. **Measurement.** Posting seniority is weakly related to stated experience requirements and drifts over time.
3. **Coverage.** The source mix swings between 7% and 45% LinkedIn-only, which is what flips the post-2025 sign.

Code: `14_diagnostics.py` (sections power / panel / measure / benchmark / hires), with new pulls:
- `15_yoe_pull.py` (P4): years of experience from descriptions;
- `16_genai_adopters_pull.py`: GenAI-role postings;
- `17_hires_pull.py` (P5): hires from profiles.

Generated tables are in `docs/diag_{power,panel,measure,benchmark,hires}.md`; figures are `figures/diag_*.png`.

## Literature benchmarks (verified)
- **Brynjolfsson, Chandar & Chen, "Canaries in the Coal Mine?"** (Stanford Digital Economy Lab / SIEPR working paper,
  Aug 2025; updated Aug 2026). ADP payroll data: workers aged 22-25 in the most AI-exposed occupations saw a **13% relative
  employment decline**, net of firm shocks.
  <https://siepr.stanford.edu/publications/working-paper/canaries-coal-mine-six-facts-about-recent-employment-effects-artificial>
  Not peer-reviewed.
- **Hosseini Maasoum & Lichtinger, "Generative AI as Seniority-Biased Technological Change"** (SSRN 5425555, 2025). Revelio
  résumés and postings; adopters are firms posting GenAI-integrator roles (10,599 of about 285k firms). Junior employment in
  adopters falls **7.7% after six quarters** (DiD) and **about 10%** in a triple difference with firm x time FE, with flat
  pre-trends for 2015-2022. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5425555> Working paper, not peer-reviewed.

## 1. Power / MDE: data limitation
- **Literature effects in our units.** The exposure gap between the top and bottom quintile of occupations is 2.76 SD of E.
  BCC's 13% becomes about **-0.05 log points per SD**; HL's 8-10% becomes about -0.03 to -0.04.
- **MDE (80% power, 5% two-sided) for Early x E x Post:**

  | Design | MDE (log points per SD) |
  |---|---|
  | Occupation-level LinkedIn-only | 0.048 |
  | Firm FE | 0.104 |
  | Firm x seniority x quarter FE | 0.092 |
  | Firm-level LinkedIn-only | 0.064 |

  That is 1-3 times the plausible effect, before any allowance for pre-trends.
- **Pre-trend allowance.**
  - The posting pre-trend slope is **-0.037 per SD per quarter**, about 7 times the BCC-implied effect slope (-0.005).
  - The half-width of the Rambachan-Roth robust interval (main firm spec, average 2023Q1-2026Q2) is 0.08 at M = 0 and
    1.09 at M = 0.25 x the observed curvature. It is 0.30 for the relative-magnitudes bound at Mbar = 0.25.
  - So the smallest effect we could declare nonzero is 2 to 20 times larger than any published estimate.
- **Verdict.** Postings cannot detect effects of the size reported in the literature. A null from them is uninformative.

## 2. Measurement validity of posting seniority: data limitation
- **Years of experience (P4).** US software postings, 1/200 sample, 292k postings, 2021-01..2026-09; 51% state a number.
  - Revelio seniority 2, half of our "early" group, has a median requirement of **4 years**: only 23% ask for ≤ 2 years and
    49% ask for ≥ 5.
  - Seniority 1: median 2 years, but 24% ask for ≥ 5.
  - Agreement: P(early | requires ≤ 2 yrs) = 0.61, P(experienced | requires ≥ 3) = 0.66.
  - The misclassification factor (sensitivity + specificity - 1) is **0.26**. With non-differential error, a true effect on
    junior roles shrinks to about a quarter in the label-based contrast.
- **Drift in levels.**
  - The Revelio early share of these postings fell from 0.53 (2021Q1) to 0.26 (2026Q3). The share requiring ≤ 2 years fell
    only from 0.20 to 0.16.
  - The 2021-22 fall in Revelio-early (0.53 → 0.42) has **no counterpart** in requirements (0.20 → 0.19).
  - Quarter-on-quarter changes in the two series are uncorrelated (r = 0.04).
- **Title keywords (07).** The share of *senior-titled* postings labelled early drops from 0.28 (2021Q1) to 0.15 (2022) to
  0.02 (2026Q2). Untagged titles go from 0.78 to 0.52. Holding the title class fixed, the label's meaning changes over time,
  which is the signature of model or source drift.
- **Break dates.** Robust-z jumps in the monthly early share:
  - other sources: 2025-11 (-0.12, z = -8), 2023-02/03 (z = -4 / +5, the known Jan-Feb 2023 spike), 2022-12;
  - LinkedIn-only: 2024-08, 2025-03, 2025-07, 2025-08 (|z| 3-4).
- **Verdict.** Posting seniority is a noisy and non-stationary proxy for junior roles. That explains both the attenuation and
  part of the 2021-22 "pre-trend".

## 3. Composition / coverage: data limitation for the sign flips, not for the pre-trend
- **Source mix.** The LinkedIn-only share of US P2 postings goes 0.13 (2021Q1) → 0.45 (2022Q1) → 0.22 (2025Q1) → **0.07**
  (2025Q3 onward). The early share differs by source (LinkedIn-only 0.55-0.77 vs other 0.72-0.86) and moves differently
  within each source.
- **Fixed panel.** 17,307 firms post on LinkedIn-only in all 22 quarters; the estimation panel has 11,029 firms and 89,926
  firm-occupation pairs.

  | Fixed-firm sample | Post | Post2 | Pre-trend test |
  |---|---|---|---|
  | LinkedIn-only postings | -0.085 (0.023) | **+0.070** (0.018) | chi2(6) = 99.7 |
  | Same firms, all sources | -0.090 (0.037) | **-0.113** (0.029) | chi2(6) = 153 |

  Same firms, opposite Post2 sign: the source channel alone flips it.
- **Verdict.**
  - The Post2 instability is a coverage artefact.
  - The pre-trend survives fixing firms and sources, so it is not firm entry or exit.
  - Together with section 2, the pre-trend is best read as posting-label drift plus the 2021-22 tech posting boom and bust.

## 4. Benchmark replication: the data can reproduce HL, but only with hires
- **Adopters.** Revelio role taxonomy (`role_k17000_v3` = Generative AI Engineer / Conversational AI Engineer), first posting
  in 2023Q1-2025Q1. This gives 1,066 adopters in the P2 firm list; the 495 firms with such postings before 2023 are dropped.
  The definition is far narrower than HL's LLM-screened keyword approach.
- **Design.** Firm x seniority x quarter cells. SE clustered by firm.

  | Outcome | Junior DiD | Senior DiD | Triple diff (firm x quarter FE) |
  |---|---|---|---|
  | Hires (profiles, weighted) | -0.104 (0.016) | +0.016 (0.015) | **-0.120 (0.011)** |
  | Hires, HL window to 2024Q2 | | | -0.113 (0.011) |
  | Software hires | | | -0.150 (0.011) |
  | Postings | | | -0.070 (0.016) |
  | Postings, HL window to 2024Q2 | | | +0.030 (0.015) |

- **Event studies.**
  - Hires: leads within ±0.06 over 2019-2022 (chi2(7) = 19 on the 2021+ leads), then a drop to -0.10..-0.18 from 2023Q3.
    This is HL's magnitude and timing.
  - Postings: leads from +0.40 to -0.22 (chi2(7) = 773) and a wild post path.
  - Figure: `diag_benchmark_1_adopters.png`.
- **Verdict.** The underlying data *can* reproduce a known published pattern; the posting outcome cannot. So the failure is in
  the postings measure, not the data source or the code.

## 5. Hires instead of postings, occupation level (Design A on hires)
- **Data.** `individual_positions` holds 163M US position starts, 2019-2026, weighted. Profile lag: recent quarters are
  under-counted (2025Q4 about half of 2025Q3), so the sample ends at 2025Q4.
- **Design.** Same triple difference as Design A, soc6 x seniority group x quarter, 660 occupations:
  - Post = **-0.073 (0.009)**, Post2 = -0.057 (0.011), YoY = -0.051 (0.007).
  - Event leads 2019Q1-2022Q2 lie within ±0.035 with no trend. The test rejects (chi2 = 35.9, p = 0.001) because the SEs
    are small, not because of drift.
  - Post coefficients: 0 through 2023Q2, then -0.05 (2024Q1), -0.10 (2025Q1), -0.14 (2025Q3).
- **Honest DiD.**
  - At M = 0 the 95% sets are 2024Q1 [-0.076, -0.034] and average 2023Q1-2025Q4 [-0.103, -0.065], so zero is excluded.
  - Relative magnitudes: the breakdown Mbar is about **0.2-0.3**. The effect survives if post-period deviations stay below
    about a quarter of the largest quarter-to-quarter wobble in the leads, which includes the COVID quarters.
  - Smoothness sets blow up for any M > 0 over 12 post quarters.
  - Robust to trend continuation, then; moderately robust to non-linear violations.
- **Canaries proxy.** First-job hires vs other hires gives Post = -0.009 (0.006). It is weak, with a slight negative drift
  in the leads; `position_number = 1` mixes internships and is a poor stand-in for age 22-25.
- **Descriptive, software developers (15-1252).** First-job hires fall to about 30-50 (2022Q3 = 100) by 2025; other hires
  fall to about 80.
- **Remaining threats.**
  - Profile-based hires lag and can be selectively updated; juniors may add jobs later. The break starts in 2023Q3, well
    before the lag window, so lag alone does not explain it.
  - Position seniority is also model-based. It is more stable than posting seniority because it uses career history.
- **Verdict.** Hires tell a clean story, consistent with BCC and HL.

## Overall
| Diagnostic | Verdict |
|---|---|
| 1. Power / MDE | Data limit: MDE ≥ literature effects; honest MDE 2-20 times larger |
| 2. Seniority measurement | Data limit: attenuation about 0.26; label drift explains part of the pre-trend |
| 3. Composition / coverage | Data limit for the sign flips (source mix); pre-trend not from firm turnover |
| 4. Benchmark replication | Hires reproduce HL (-0.12); postings do not, so the postings measure is the problem |
| 5. Alternative outcome | Hires: flat pre-trends, junior decline of about -0.07 per SD after 2023Q3, robust to linear trends |

**What we can say.**
1. The posting-based null is not informative about AI.
2. Profile-based hires show an exposure-graded junior decline beginning in 2023H2, of the size reported by BCC and HL.
3. That evidence is still correlational. It relies on Revelio's profile seniority and on the absence of other
   exposure-graded junior shocks in 2023, such as interest rates and the Section 174 R&D amortisation in tech; the latter
   has not been checked here.

**Recommendation.** Make hires (`individual_positions`) the main outcome and keep postings as secondary, with a fixed-source
panel and a years-of-experience definition of junior.
