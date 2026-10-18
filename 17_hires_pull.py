"""P5: hires (new positions) from Revelio individual_positions (LinkedIn-profile based), US, as an alternative outcome.
startdate is not indexed, so each query is one full scan (~1.8B rows); run in the background.
  occ : month(startdate) x SOC6 x seniority (1..7) x first_job (position_number = 1) -> count, sum(weight)
  firm: quarter x ultimate_parent_rcid (P2 US firm list) x seniority group (early 1-2 / exp 3-4) x software (SOC 15-12) -> count, sum(weight)
weight = Revelio's sampling weight (corrects LinkedIn coverage by occupation/location). Profiles are updated with a lag,
so the most recent quarters are under-counted (documented in docs/data_vs_result_diagnosis.md).
Output (git-ignored): data/hires/occ.parquet, data/hires/firm.parquet.  Usage: uv run python 17_hires_pull.py occ|firm
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "hires")
SQL_OCC = """
select to_char(startdate, 'YYYY-MM') as month, left(onet_code, 7) soc6, seniority, (position_number = 1) first_job,
       count(*) n, sum(weight) w
from revelio.individual_positions
where startdate >= '2019-01-01' and startdate < '2026-10-01' and country = 'United States' and onet_code is not null
group by 1, 2, 3, 4
"""
SQL_FIRM = """
with f as (select unnest(%(us)s::bigint[]) rcid)
select to_char(date_trunc('quarter', p.startdate), 'YYYY-MM') qstart, p.ultimate_parent_rcid::bigint rcid,
       case when p.seniority <= 2 then 'early' else 'exp' end sg, (p.onet_code like '15-12%%') software,
       count(*) n, sum(p.weight) w
from revelio.individual_positions p join f on f.rcid = p.ultimate_parent_rcid
where p.startdate >= '2019-01-01' and p.startdate < '2026-10-01' and p.country = 'United States' and p.seniority between 1 and 4
group by 1, 2, 3, 4
"""

def main(which):
    os.makedirs(OUT, exist_ok=True); f = os.path.join(OUT, f"{which}.parquet")
    if os.path.exists(f): print("exists", f); return
    db = connect(); t = time.time()
    if which == "occ":
        df = db.raw_sql(SQL_OCC)
    else:
        fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet"))
        df = db.raw_sql(SQL_FIRM, params={"us": [int(x) for x in fl[fl.country == "United States"].rcid]})
    df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
    print(f"{which}: {len(df):,} rows, {int(df.n.sum()):,} positions, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
