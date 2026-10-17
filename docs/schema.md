# WRDS Revelio: schema notes (checked 2026-10-16)

All `revelio.*` objects are **views** over WRDS schemas (`revelio_job_postings`, `revelio_layoffs`, ...).
Probes: `tools/inspect_schema.py`, `tools/probe*.py`, `tools/validate_seniority.py`.

## Access (Princeton account)
| table | access |
|---|---|
| postings_cosmos, postings_cosmos_raw (+ _p0.._p9), postings_role_lookup_v2/v3 | OK |
| individual_positions, individual_user, individual_user_skills, company_mapping | OK |
| **layoffs** | **DENIED** (`permission denied for schema revelio_layoffs`) |
| **workforce_dynamics_geo** | **DENIED** (schema `revelio_workforce_dynamics`) |
| sentiment_scores | DENIED |

## postings_cosmos (deduplicated postings; ~2.92 bn rows, 858 GB)
Columns: job_id, rcid, company, role_k1500_v2, role_k17000_v3, onet_code (e.g. `15-1252.00`), country, state,
metro_area, seniority (smallint), salary, salary_min, salary_max, salary_predicted (bool), post_date, remove_date,
ultimate_parent_rcid, ultimate_parent_company_name, remote_type, expected_hires, source_company_sites,
source_linkedin, source_indeed, source_zhaopin, source_51job, source_liepin, source_other_aggregators,
source_staffingfirms, source_regional_aggregators.

- **No description text in this table.** Indexes: post_date, job_id, rcid, (rcid, post_date), ultimate_parent_rcid,
  role_k1500_v2, role_k17000_v3. **No index on onet_code or country** -> always restrict by post_date (one month
  of US+China scans in ~15-30 s; all countries ~70 s cold).
- post_date range: 2008-01-01 .. 2026-09-06. Revelio's docs say COSMOS history "begins in 2021" (earlier years
  are back-filled from fewer sources) -> treat pre-2021 levels with caution; compare shares, not counts.
- country: full English names ('United States', 'China'; Hong Kong and Taiwan separate). ~2.6 M postings/month
  have country = 'empty'.
- remote_type values: Fully In Office, Fully Remote, Partially In Office, Remote In Territory, Temporarily Remote.
- salary_predicted: ~85-90% of US computer-occupation salaries and ~55% of China's are *model-predicted*, not posted.
- Source mix (computer occupations, Mar 2024): US = LinkedIn 74%, company sites 16%, Indeed 16%, staffing 8%;
  China = LinkedIn 50%, Zhaopin 22%, Liepin 14%, 51job 10% (flags overlap). China coverage of domestic boards is
  partial (no Boss Zhipin, Lagou).
- Big staffing/aggregator posters dominate some months (e.g. Diverse Lynx 69.5k US computer postings in Mar 2024,
  "America's Navy" 30k) -> exclude staffing firms / check robustness to top posters.

## Seniority coding
Values observed: 1-7 only, no NULLs. Revelio data dictionary (methodology + FAQ pages,
https://www.data-dictionary.reveliolabs.com/methodology.html): ensemble model on title, company, industry
(postings: title-based), mapped to 7 ordinal bins:

| code | label | dictionary examples |
|---|---|---|
| 1 | Entry level / Intern | Accounting Intern, Software Engineer Trainee, Paralegal |
| 2 | Junior | AR Bookkeeper, Junior Software QA Engineer |
| 3 | Associate / Analyst | Senior Tax Accountant, Lead Electrical Engineer |
| 4 | Manager | Account Manager, Superintendent Engineer |
| 5 | Director | VP Network Engineering, Head of Legal |
| 6 | Executive | Managing Director, Director of Engineering |
| 7 | Senior Executive | CFO, COO, CEO |

All-country distribution, Mar 2024 (postings): 1: 12.5 M, 2: 9.7 M, 3: 5.6 M, 4: 2.9 M, 5: 1.1 M, 6: 91 k, 7: 36 k.
Computer occupations (15-12xx), Mar 2024: US 1: 128k, 2: 216k, 3: 169k, 4: 237k, 5: 73k, 6: 4k, 7: 0.9k;
China 1: 22k, 2: 56k, 3: 28k, 4: 17k, 5: 4k.

**Face validity** (`docs/seniority_validation_2024-03-05.csv`, title keywords x code, one day): monotone but noisy.
US titles with "senior" sit mostly at 4 (2,408) and 3 (1,380); "intern/grad" mostly at 1; "staff/principal"
at 4-5; "director/VP" at 5-6. => **Code 4 is "senior individual contributor", not people manager**, in tech.
Most level-1/2 postings have no seniority keyword at all. Recommendation: use **1+2 = early-career** as the
main entry-level measure, report 1 alone as a robustness check.

## postings_cosmos_raw (hash-partitioned by job_id into 10 parts, ~634 GB each)
Columns: job_id (numeric), title_raw, jobtitle_translated, location_raw, **description (full posting text)**.
Join to postings_cosmos on job_id (indexed). Descriptions are ~4-9k characters. Never pull at scale: sample by
job_id or compute keyword flags server-side (e.g. `description ~* 'large language|LLM|copilot'`) and aggregate.

## postings_role_lookup_v2 / v3
v2: role_k1500_v2 -> role_k150_v2, role_k50_v2, job_category_v2.
v3: role_k10_v3 ... role_k17000_v3 hierarchy + onet_code, onet_title.

## individual_positions (LinkedIn-style profiles, accessible)
user_id, position_id, region, country, state, metro_area, msa, city, startdate, enddate, role_k1500_v2,
role_k17000_v3, remote_suitability, weight (sampling weight), start_salary, end_salary, seniority, salary,
position_number, rcid, ultimate_parent_rcid, onet_code, total_compensation, additional_compensation.

## individual_user_skills
user_id, skill_raw, skill_translated, first_reported (date), skill_source, skill_k35000.
## individual_user
user_id, fullname, f_prob/m_prob, race probabilities, prestige, highest_degree, sex_predicted,
ethnicity_predicted, profile_linkedin_url, user_location, user_country, updated_dt, numconnections.
(Contains names/URLs: personal data, never export.)

## layoffs (schema only; access denied)
company_raw, rcid, company, state/city/msa/county raw + cleaned, metro_area, notice_date, layoff_date,
layoff_start_date, layoff_end_date, layoff_type, num_employees, num_employees_temporary, num_employees_furlough,
ultimate_parent_rcid, ultimate_parent_company_name. Fields mirror US **WARN Act** notices (state-level, US only).

## workforce_dynamics_geo (schema only; access denied)
rcid, country, state, metro_area, seniority, role_k10, count/inflow/outflow/external_* (scaled_ and raw_
versions), salary, duration, remote_suitability, datemonth.
