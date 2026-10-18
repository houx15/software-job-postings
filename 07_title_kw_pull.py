"""Seniority-model check: title keywords x Revelio seniority, computer occupations, US + China, sampled like 03
(job_id % 50 US, % 20 China). Month x country x seniority x keyword class counts. Output: data/titlekw/YYYY-MM.parquet.
Keyword classes (title_raw + jobtitle_translated), first match wins in this order:
  intern_grad : intern, trainee, graduate, new grad, campus, 实习, 校招, 校园, 应届, 管培
  junior      : junior, jr, entry, associate engineer, level I/1, 初级, 助理
  senior_plus : senior, sr, staff, principal, lead, manager, director, architect, 高级, 资深, 专家, 主管, 经理, 总监, 架构
  none        : no keyword
Usage: uv run python 07_title_kw_pull.py 2021-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "titlekw")
P = {"kw_intern": r"intern|trainee|graduate|new grad|campus|实习|校招|校园|应届|管培",
     "kw_junior": r"junior|\mjr\M|entry|associate engineer|\m(i|1)\M\s*$|初级|助理",
     "kw_senior": r"senior|\msr\M|staff|principal|\mlead|manager|director|architect|head of|\mvp\M|高级|资深|专家|主管|经理|总监|架构"}
SQL = """
with p as (
  select job_id, country, seniority from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s and country in ('United States', 'China') and onet_code like '15-12%%'
    and job_id %% (case when country = 'China' then 20 else 50 end) = 0
), t as (
  select p.country, p.seniority, lower(coalesce(r.title_raw, '') || ' | ' || coalesce(r.jobtitle_translated, '')) tt
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
)
select country, seniority,
  case when tt ~* %(kw_intern)s then 'intern_grad' when tt ~* %(kw_junior)s then 'junior'
       when tt ~* %(kw_senior)s then 'senior_plus' else 'none' end as kw, count(*) n
from t group by 1, 2, 3
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True)
    db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat(), **P}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f, index=False)
        print(f"{m}: {int(df.n.sum()):,} sampled, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
