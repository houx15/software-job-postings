"""Experience-based junior hires and external vs internal moves (docs/explore_experience_junior.md).

Revelio individual_positions (LinkedIn-style profiles), users sampled by mod(user_id, MOD) = 0 (MOD = 5, a 20% random sample
of people: every position of a sampled user is kept, so career histories are complete). Server-side, per position:
  first_start = min(startdate) over the user's positions (window, ordered by position_number)
  prev_upr    = ultimate_parent_rcid of the previous position (position_number - 1, window lag)
  grad_end    = latest individual_user_education.enddate <= startdate + 6 months (last schooling finished before the job)
  updated_dt  = individual_user.updated_dt (last profile update; used for the profile-lag check)
Hires = positions with startdate in 2019-01..2026-06, country US, ultimate parent in the P2 US firm list, onet not null.
Aggregated to half x rcid x soc6 x sg x xf x xg x mv x upd -> n:
  sg  : Revelio seniority 1-2 'early' / 3-4 'exp' / 5-7 'sen'
  xf  : years from first_start to startdate: 'j' [0,3), 'm' [3,6), 's' >= 6
  xg  : years from grad_end to startdate: 'j' < 3 (incl. jobs started up to 6 months before the end date), 'm' [3,6), 's' >= 6,
        'na' (no dated education)
  mv  : 'first' (position_number 1), 'ext' (previous position at a different, known ultimate parent),
        'int' (previous position at the same ultimate parent = internal move), 'unk' (previous parent missing)
  upd : 'u26' if updated_dt >= 2026-01-01, 'u25' if in 2025, 'old' otherwise / missing
Output (git-ignored): data/hires_exp/hires_exp.parquet (MOD=5; other MOD -> hires_exp_m<MOD>.parquet).  Usage: nohup uv run python -u 24_hires_exp_pull.py > logs/24.log &
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "hires_exp")
MOD = int(os.environ.get("MOD", 5))
SQL = """
with f as (select unnest(%(us)s::bigint[]) rcid),
a as (
  select position_id, user_id, position_number pn, startdate, country, onet_code, seniority, ultimate_parent_rcid upr,
         min(startdate) over w first_start, lag(ultimate_parent_rcid) over w prev_upr
  from revelio.individual_positions
  where mod(user_id, %(mod)s) = 0
  window w as (partition by user_id order by position_number)
),
h as (
  select a.* from a join f on f.rcid = a.upr
  where a.startdate >= '2019-01-01' and a.startdate < '2026-07-01' and a.country = 'United States' and a.onet_code is not null
),
g as (
  select h.position_id, max(e.enddate) grad_end
  from h join revelio.individual_user_education e on e.user_id = h.user_id
  where mod(e.user_id, %(mod)s) = 0 and e.enddate is not null and e.enddate <= h.startdate + 182
  group by 1
),
u as (select user_id, updated_dt from revelio.individual_user where mod(user_id, %(mod)s) = 0)
select extract(year from h.startdate)::int || 'H' || (case when extract(month from h.startdate) <= 6 then 1 else 2 end) half,
  h.upr::bigint rcid, left(h.onet_code, 7) soc6,
  case when h.seniority <= 2 then 'early' when h.seniority <= 4 then 'exp' else 'sen' end sg,
  case when (h.startdate - h.first_start) < 1096 then 'j' when (h.startdate - h.first_start) < 2192 then 'm' else 's' end xf,
  case when g.grad_end is null then 'na' when (h.startdate - g.grad_end) < 1096 then 'j'
       when (h.startdate - g.grad_end) < 2192 then 'm' else 's' end xg,
  case when h.pn = 1 then 'first' when h.prev_upr is null then 'unk' when h.prev_upr = h.upr then 'int' else 'ext' end mv,
  case when u.updated_dt >= '2026-01-01' then 'u26' when u.updated_dt >= '2025-01-01' then 'u25' else 'old' end upd,
  count(*) n
from h left join g on g.position_id = h.position_id left join u on u.user_id = h.user_id
group by 1, 2, 3, 4, 5, 6, 7, 8
"""

def main():
    os.makedirs(OUT, exist_ok=True); f = os.path.join(OUT, "hires_exp.parquet" if MOD == 5 else f"hires_exp_m{MOD}.parquet")
    if os.path.exists(f): print("exists", f); return
    fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet"))
    us = [int(x) for x in fl[fl.country == "United States"].rcid]
    db = connect(); t = time.time()
    df = db.raw_sql(SQL, params={"us": us, "mod": MOD})
    print(f"fetched {len(df):,} rows, {time.time()-t:.0f}s", flush=True)
    df["n"] = df.n.astype("int32")
    for c in ["half", "soc6", "sg", "xf", "xg", "mv", "upd"]: df[c] = df[c].astype("category")
    df["mod"] = MOD
    df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
    print(f"{int(df.n.sum()):,} sampled hires, {len(df):,} rows, {os.path.getsize(f)/1e6:.1f} MB, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main()
