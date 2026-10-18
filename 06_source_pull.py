"""Source composition of computer-occupation postings (O*NET 15-12xx), US + China, month x country x seniority.

Server-side aggregates only (one date-indexed scan per month). For each Revelio source flag, the number of postings
carrying it (flags overlap: a deduplicated posting can be seen on several boards), plus mutually exclusive
'primary source' buckets used for composition decompositions:
  linkedin_only, cn_board_only (zhaopin/51job/liepin, no LinkedIn), linkedin_and_cn_board, company_site_only,
  indeed_any (no LinkedIn, no CN board), staffing_any (rest with staffing flag), other.
Output: data/sources/YYYY-MM.parquet (resumable).  Usage: uv run python 06_source_pull.py 2020-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "sources")
FLAGS = ["source_company_sites", "source_linkedin", "source_indeed", "source_zhaopin", "source_51job", "source_liepin",
         "source_other_aggregators", "source_staffingfirms", "source_regional_aggregators"]
SQL = """
with b as (
  select country, seniority, """ + ", ".join(f"coalesce({f}, false) as {f}" for f in FLAGS) + """
  from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s
    and country in ('United States', 'China') and onet_code like '15-12%%'
), c as (
  select *, (source_zhaopin or source_51job or source_liepin) as cn_board from b
)
select country, seniority, count(*) as n,
  """ + ",\n  ".join(f"sum({f}::int) as {f.replace('source_', 'n_')}" for f in FLAGS) + """,
  sum((source_linkedin and not cn_board and not source_company_sites and not source_indeed and not source_staffingfirms
       and not source_other_aggregators and not source_regional_aggregators)::int) as p_linkedin_only,
  sum((cn_board and not source_linkedin)::int) as p_cn_board_only,
  sum((cn_board and source_linkedin)::int) as p_linkedin_and_cn_board,
  sum((source_company_sites and not source_linkedin and not cn_board and not source_indeed and not source_staffingfirms
       and not source_other_aggregators and not source_regional_aggregators)::int) as p_company_site_only,
  sum((source_indeed and not source_linkedin and not cn_board)::int) as p_indeed_no_li,
  sum((source_staffingfirms and not source_linkedin and not cn_board and not source_indeed)::int) as p_staffing_no_li
from c group by 1, 2
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True)
    db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat()}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f, index=False)
        print(f"{m}: {int(df.n.sum()):,} postings, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
