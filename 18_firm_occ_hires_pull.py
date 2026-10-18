"""Exploration A (docs/explore_gap_uscn.md): hires at firm x SOC6 occupation x half-year, US, for the P2 firm list
(data/firms/firm_list.parquet, firms with >= 50 pre-period postings), to match the posting panel of 12.
One full-scan query over 2019-01..2026-06 grouped by half-year (a per-half-year query with the startdate index took
> 15 min for the first half alone; a single scan like 17 is far cheaper).
  sg  : Revelio seniority group, early = 1-2, exp = 3-4 (5-7 dropped, as in 12)
  pn  : experience proxy that does not use the seniority model: 'first' = position_number 1 (first recorded
        position on the profile, i.e. a labour-market entrant), 'second' = 2, 'later' = 3+
  n, w: count and sum of Revelio sampling weights
Output (git-ignored): data/hires_fo/hires_fo.parquet.  Usage: uv run python 18_firm_occ_hires_pull.py
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "hires_fo")
MAX_BYTES = 6 * 1024**3
SQL = """
with f as (select unnest(%(us)s::bigint[]) rcid)
select extract(year from p.startdate)::int || 'H' || (case when extract(month from p.startdate) <= 6 then 1 else 2 end) half,
       p.ultimate_parent_rcid::bigint rcid, left(p.onet_code, 7) soc6,
       case when p.seniority <= 2 then 'early' else 'exp' end sg,
       case when p.position_number = 1 then 'first' when p.position_number = 2 then 'second' else 'later' end pn,
       count(*) n, sum(p.weight) w
from revelio.individual_positions p join f on f.rcid = p.ultimate_parent_rcid
where p.startdate >= '2019-01-01' and p.startdate < '2026-07-01' and p.country = 'United States'
  and p.seniority between 1 and 4 and p.onet_code is not null
group by 1, 2, 3, 4, 5
"""

def data_bytes():
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(HERE, "data")) for f in fs)

def main():
    os.makedirs(OUT, exist_ok=True); f = os.path.join(OUT, "hires_fo.parquet")
    if os.path.exists(f): print("exists", f); return
    if data_bytes() > MAX_BYTES: sys.exit("data/ over 6 GB guard, stopping")
    fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet"))
    us = [int(x) for x in fl[fl.country == "United States"].rcid]
    db = connect(); t = time.time()
    df = db.raw_sql(SQL, params={"us": us})   # wrds' raw_sql returns one DataFrame (its chunksize does not stream)
    print(f"fetched {len(df):,} rows, {time.time()-t:.0f}s", flush=True)
    df["n"] = df.n.astype("int32"); df["w"] = df.w.astype("float32")
    for c in ["half", "soc6", "sg", "pn"]: df[c] = df[c].astype("category")
    df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
    print(f"{int(df.n.sum()):,} hires, {len(df):,} rows, {os.path.getsize(f)/1e6:.1f} MB, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main()
