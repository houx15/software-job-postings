"""P4: measurement validation of Revelio seniority with required years of experience parsed from posting descriptions.
US computer occupations (SOC 15-12xx), 1/200 sample (job_id %% 200 = 0), 2021-01..2026-09.
Server-side: first "N(+)( - M) years ... experience" match in the description (min years N; NULL if none), plus the
title-keyword class of 07. Only aggregated counts leave WRDS: month x seniority x soc6 x yoe x kw.
Output (git-ignored): data/yoe/YYYY-MM.parquet.  Usage: uv run python 15_yoe_pull.py 2021-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "yoe")
P = {"yoe_re": r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)[^.;\n]{0,40}experience",
     "kw_intern": r"intern|trainee|graduate|new grad|campus",
     "kw_junior": r"junior|\mjr\M|entry|associate engineer|\m(i|1)\M\s*$",
     "kw_senior": r"senior|\msr\M|staff|principal|\mlead|manager|director|architect|head of|\mvp\M"}
SQL = """
with p as (
  select job_id, seniority, left(onet_code, 7) soc6 from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s and country = 'United States' and onet_code like '15-12%%'
    and job_id %% 200 = 0
), t as (
  select p.seniority, p.soc6, lower(coalesce(r.title_raw, '')) tt,
         substring(lower(coalesce(r.description, '')) from %(yoe_re)s)::int yoe
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
)
select seniority, soc6, case when yoe > 30 then null else yoe end yoe,
  case when tt ~* %(kw_intern)s then 'intern_grad' when tt ~* %(kw_junior)s then 'junior'
       when tt ~* %(kw_senior)s then 'senior_plus' else 'none' end kw, count(*) n
from t group by 1, 2, 3, 4
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True); db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f): continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat(), **P}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: {int(df.n.sum()):,} sampled, {100*df[df.yoe.notna()].n.sum()/df.n.sum():.0f}% with years, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
