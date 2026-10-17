"""Pull server-side aggregates of Revelio COSMOS job postings (WRDS), US vs China.

One date-indexed scan per month; GROUPING SETS give three aggregate tables in one pass:
  set 'occ2'   : month x country x seniority x 2-digit SOC major group (all occupations; denominators)
  set 'onet'   : month x country x seniority x 7-char O*NET code (e.g. 15-1252), computer occupations (15-12xx) only
  set 'parent' : month x country x seniority x ultimate parent company, computer occupations only
No posting-level rows are downloaded. Output: data/agg/YYYY-MM.parquet (resumable: existing months are skipped).

Seniority (Revelio 7-level ordinal, see docs/schema.md):
  1 Entry, 2 Junior, 3 Associate/Analyst, 4 Manager, 5 Director, 6 Executive, 7 Senior Executive

Usage: python3 01_swe_by_seniority.py 2018-01 2026-09    (or a single month: 2024-03 2024-03)
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
from db import connect

SENIORITY = {1: "Entry", 2: "Junior", 3: "Associate", 4: "Manager",
             5: "Director", 6: "Executive", 7: "Senior Executive"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "agg")
TABLE = "revelio.postings_cosmos"
MAX_BYTES = 5 * 1024**3   # hard stop: project data must stay well under the 10 GB budget

def data_bytes():
    root = os.path.dirname(OUT)
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)

SQL = f"""
with base as (
  select country, seniority,
         left(onet_code, 2)                                              as occ2,
         case when onet_code like '15-12%%' then left(onet_code, 7) end  as swe_onet,
         case when onet_code like '15-12%%' then coalesce(ultimate_parent_rcid, -1) end as swe_parent,  -- -1 = no parent id
         case when onet_code like '15-12%%' then ultimate_parent_company_name end as parent_name,
         expected_hires, salary, salary_predicted, remote_type
  from {TABLE}
  where post_date >= %(start)s and post_date < %(end)s
    and country in ('United States', 'China')
)
select case when grouping(occ2) = 0 then 'occ2'
            when grouping(swe_onet) = 0 then 'onet' else 'parent' end as gset,
       country, seniority, occ2, swe_onet, swe_parent,
       min(parent_name)                                   as parent_name,
       count(*)                                           as n_posts,
       sum(expected_hires)                                as exp_hires,
       avg(salary)                                        as avg_salary,
       avg(case when not salary_predicted then salary end) as avg_salary_observed,
       sum(case when not salary_predicted then 1 else 0 end) as n_salary_observed,
       sum(case when remote_type = 'Fully Remote' then 1 else 0 end) as n_remote
from base
group by grouping sets ((country, seniority, occ2),
                        (country, seniority, swe_onet),
                        (country, seniority, swe_parent))
"""

def months(a, b):
    return pd.period_range(a, b, freq="M")

def main(a, b):
    os.makedirs(OUT, exist_ok=True)
    db = connect()
    for m in months(a, b):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        if data_bytes() > MAX_BYTES:
            sys.exit(f"data/ exceeds {MAX_BYTES/1024**3:.0f} GB, stopping")
        t = time.time()
        start, end = m.start_time.date().isoformat(), (m + 1).start_time.date().isoformat()
        df = db.raw_sql(SQL, params={"start": start, "end": end})
        # drop the NULL buckets created by non-computer rows in the onet/parent sets
        df = df[~((df.gset == "onet") & df.swe_onet.isna()) & ~((df.gset == "parent") & df.swe_parent.isna())]
        df = df.copy()
        df.insert(0, "month", str(m))  # string YYYY-MM: pandas 2.2.3 datetime ops segfault on Python 3.14 here
        df["seniority_label"] = df.seniority.map(SENIORITY)
        df.to_parquet(f, index=False)
        print(f"{m}: {len(df):,} rows, {df.loc[df.gset=='onet','n_posts'].sum():,.0f} computer-occ postings, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2018-01", sys.argv[2] if len(sys.argv) > 2 else "2026-09")
