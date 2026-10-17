# Tech-stack / language tags (03_stack_language_tags.py, 04_stack_figures.py)

**Universe.** Revelio COSMOS postings, O*NET 15-12xx (computer occupations), US + China, 2021-01..2026-09
(figures stop at 2026-08; 2026-09 is partial). Joined to `postings_cosmos_raw` on job_id; all regex runs on WRDS;
only month x country x seniority-group counts are downloaded (`data/tags/`, ~1 MB total).

**Sampling.** Deterministic: `job_id % 50 = 0` (US, ~2%), `job_id % 20 = 0` (China, ~5%). 2.21 M sampled postings
(US 1.17 M, China 1.05 M). Shares need no weights; counts x MOD estimate totals. ~1 min per month on WRDS.

**Tags.** Stack tags come from the title (`title_raw` + `jobtitle_translated`, English + Chinese keywords). Language,
framework and AI tags come from the description (share of postings with a description longer than 150 chars).
Seniority groups: early = Revelio 1-2, mid = 3, senior = 4 (senior individual contributor), lead = 5-7.

## Precision checks (hand-read 6-12 hits per tag; snippets kept in data/validation/, never committed)
| issue | fix |
|---|---|
| `go` matched "go to office", "Go to Profile" (~10/12 false) | golang / "go lang" or case-sensitive `Go` inside a language list (`, Go,` `/Go` `(Go)`). After the fix 10/10 correct |
| `c` matched "(c) consistent with", "Rev C" | case-sensitive `C` in a list, `C programming/language`, `C语言`; not after "Objective-". About 9/10 correct; "C/C++" counts as both C and C++ |
| `swift` matched "swift resolution" and SWIFT bank messages | case-sensitive `Swift`, excluding message/payment/code |
| backend: 数字后端 (chip physical design) | excluded `(?<!数字)后端`, `(?<!digital )backend` |
| ML/AI title: "AI-LiNK 品牌先锋" (A.O. Smith marketing job coded 15-12) | `\mai\M(?!-link)` |
| desktop: "Desktop Engineer" = IT desktop support | dropped "desktop engineer" |
| web: "Web Designer", "WEB Crew Advisor" | require web developer/engineer/programmer/application/development... |
| **China full-page scrapes**: ~60% of China descriptions (51job, Liepin) are whole web pages: city navigation, link farms ("深圳多模态大模型算法招聘 Golang招聘 ..."), and company registration text | keep text from 职位信息 to the first footer / link-farm / company-info / anti-fraud marker. Test day: link-farm runs 423/700 -> 0, mean length 5,390 -> 613 chars; Java hits 61 -> 60, LLM 41 -> 34 |

Clean: Python, Java, JS/TS, Scala, React, C#, PHP, Ruby, Rust, Kotlin, SQL; Chinese frontend/fullstack/mobile/cloud titles.

**Remaining caveats**
- Description tags count *mentions*, and long skill lists add several languages at once. They measure what postings ask for, not the tools actually used.
- Liepin pages often contain only the company intro, not the duties, so China description tags are diluted. China postings with a description: 2024 only 54% (32.7k of 60.7k), other years 70-99%.
- 运维 (ops) includes IT operations as well as DevOps.
- Stack-in-title shares are small in the US (most titles are a generic "Software Engineer"). They are better read as relative trends.
- US 2023Q4-2024Q2 shows a spike (senior full-stack/backend titles, Python/Go/Scala). It is probably one large poster or a source batch; check with the parent-company split before interpreting it.
- Seniority is predicted by Revelio's model, mostly from titles (see schema.md).
