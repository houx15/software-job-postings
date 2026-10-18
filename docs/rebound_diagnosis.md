# Why does the early-career share dip and rebound? (2023 in particular)

Scripts: `06_source_pull.py` (source flags, full count, month x country x seniority), `07_title_kw_pull.py`
(title keywords, sampled 1/50 US and 1/20 CN), `08_rebound_diagnosis.py` (analysis).
Figures: `figures/rebound_1_decomposition.png`, `figures/rebound_2_seasonal.png`.
Sample: computer occupations (O*NET 15-12xx), early career = Revelio seniority 1-2, months 2021-01..2026-08. Descriptive only.

## Bottom line
- **US 2023 rebound** (37.0% in 2023Q1 → 47.5% in 2023Q4): this is a **denominator effect**, not more junior demand.
  Over those quarters early-career postings *fell* 17% (966k → 806k) while seniority-3 ("associate") postings fell 57% (916k → 396k)
  and 4+ fell 32%. The 2023Q1 trough is partly a Jan-Feb 2023 spike of seniority-3 postings on LinkedIn: the ratio of level-3 to
  levels 1-2 is 1.2-1.3 in those months versus 0.6-0.8 just before and after. That trough is further deepened by Q1 seasonality.
  - It is **not** source mix: shift-share across source buckets gives between = +0.7 pp, within = +9.9 pp of the +10.7 pp.
    LinkedIn-only (34.6 → 45.8%) and Indeed-without-LinkedIn (49.5 → 56.0%) both rise, so two largely independent sources agree.
  - It is **not** big posters: excluding the top-20 named parents gives 38.2 → 48.1%; excluding staffing/outsourcing parents gives 36.7 → 47.4%; excluding no-parent-id postings gives 37.0 → 46.2%.
  - It is **not** seasonal: the seasonally adjusted series still rises ~9 pp (Jan-23 38.4 → Oct-23 47.2). YoY changes are ≈0 in Sep-Dec 2023. In other words, 2023H2 merely got back to the 2022H2 level after an abnormal 2023H1, and the +6 to +11 pp YoY in early 2024 is a base effect.
  - Seniority model: the title-keyword shares hardly move (intern/junior titles 3-4% of postings; senior+ titles 39-41%), so there is no sign of the classifier re-labelling titles in 2023 US. However, the share of model-early postings that carry a *senior* title drifts down from 22% (2021) to 3% (2026), so the model and title conventions are not constant over time.
- **China 2023 rebound** (42.3% → 60.4%) is mostly **measurement artefacts**, not demand:
  1. **Seniority step changes by board.** The early share of Zhaopin postings jumps from 15.5% (Sep 2023) to 58% (Oct 2023) **in one month**, and stays ~60%. Liepin jumps 21% → 54% in 2023Q4, and 51job 36% → 68% at Dec-2022/Jan-2023. Level-3 counts on Zhaopin drop from 24k to 9k in a month while levels 1-2 triple. Real hiring does not move like that, so this is a re-coding/parsing change in Revelio for these boards.
  2. **Source entry and exit.** LinkedIn carries 80-86% of China computer postings in 2021Q3-2023Q1 and then collapses (LinkedIn shut down its China jobs app InCareer on 2023-08-09, [LinkedIn Help](https://www.linkedin.com/help/linkedin/answer/a534125)). CN boards rise to 40-65% of the mix by 2024-25, then **vanish from 2025Q4** (0%). Total volume jumps ×6 in 2025Q3. Shift-share says the 2023 move is "within" (+19.8 pp), but "within" is exactly where the board re-coding sits.
  3. LinkedIn-China itself: early share 77% (2021-22) → 43.7% (2023Q1) → ~61% (2023Q4-2024), with volume falling from 1.12M to 0.24M a quarter. The LinkedIn-China sample is shrinking and selected.
  - Top posters do not matter in China: the top-20 named parents are only 2-7% of postings, and the ex-top-20 and ex-outsourcing (法本, 中软国际, FESCO Adecco …) series sit on top of the total. 65-77% of China postings have no parent id.
- **Repeated dips and rebounds in general**: three things stack. (i) **Seasonality**: Q1 is the low quarter in both countries. (ii) **The level-3 denominator** is much more volatile than levels 1-2. (iii) In China, **source and pipeline breaks**. The persistent downward trend since 2024Q2 in the US (45 → 29%) survives all checks: it shows up in LinkedIn-only (43 → 28%), ex-top-20 and ex-staffing, and SA/YoY. It is partly reinforced by company-site postings (early share ~30-38%) rising to 50%+ of the US mix in 2026.

## Seasonality (month-of-year deviation from a 13-month centered MA, 2021-2026, pp)
| | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| US | -1.6 | -2.1 | -2.5 | 0.0 | +0.3 | +0.9 | +1.6 | -0.1 | +1.8 | +1.0 | +0.9 | +0.6 |
| China | -4.1 | -3.3 | +2.2 | +1.8 | +2.3 | +3.6 | +5.9 | +4.6 | +2.5 | +1.5 | -3.8 | -2.6 |

- US: Jan-Mar low (senior and req backfills at the start of the budget year), while summer and Sep are high (intern and new-grad cycle). The amplitude is ~4 pp.
- China: the trough is in Nov-Feb (after 秋招 and over Spring Festival). The peak is Jul-Aug (graduation, plus 秋招 launches for the next cohort), and 春招 (Mar-Apr) adds about +2 pp. The amplitude is ~10 pp. Caveat: China's month effects are estimated across source breaks, so treat them as indicative.
- So quarter-to-quarter comparisons involving Q1 overstate dips. Use YoY or the SA series (fig 2).

## Numbers (quarterly, thousands of postings; full tables in git-ignored `docs/rebound_*.csv`)
| | US 22Q2 | US 23Q1 | US 23Q4 | US 24Q4 | US 26Q2 | CN 22Q2 | CN 23Q1 | CN 23Q4 | CN 25Q3 | CN 26Q2 |
|---|---|---|---|---|---|---|---|---|---|---|
| all (denominator) | 4241 | 2611 | 1696 | 1312 | 3710 | 2076 | 1299 | 420 | 1324 | 835 |
| seniority 1-2 (numerator) | 1919 | 966 | 806 | 470 | 1086 | 1412 | 550 | 253 | 721 | 298 |
| seniority 3 | 1130 | 916 | 396 | 411 | 1413 | 486 | 592 | 104 | 235 | 377 |
| early share % | 45.2 | 37.0 | 47.5 | 35.8 | 29.3 | 68.0 | 42.3 | 60.4 | 54.4 | 35.7 |

## Implications
1. Never read a China series across 2023-01, 2023-10 or 2025-10 without a fixed-source panel. Analyse LinkedIn-China and CN boards separately and drop the switch months (or use board x period FE).
2. Use **counts by seniority**, not only the share: the share can rise while juniors fall.
3. Report YoY / SA series. Use 2021 onward only.
4. These checks are built into `docs/did_design.md` (source x seniority x month FE, staffing exclusion, title-keyword validation).
