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
Chunking: the MOD sample is pulled as buckets mod(user_id, BASE) = r for r in {0, MOD, 2*MOD, ...} < BASE (BASE = 20 by default), so
users never straddle chunks and windows stay complete. Each bucket goes to data/hires_exp/m<MOD>_parts/r<r>.parquet; finished buckets are
skipped on rerun; connection errors trigger reconnect and retry (TCP keepalives on). Bucket r=0 with BASE=20 is the 1/20 sample itself,
so an existing hires_exp_m20.parquet is reused for it.
"""
import os, sys, time, shutil
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
  where mod(user_id, %(base)s) = %(r)s
  window w as (partition by user_id order by position_number)
),
h as (
  select a.* from a join f on f.rcid = a.upr
  where a.startdate >= '2019-01-01' and a.startdate < '2026-07-01' and a.country = 'United States' and a.onet_code is not null
),
g as (
  select h.position_id, max(e.enddate) grad_end
  from h join revelio.individual_user_education e on e.user_id = h.user_id
  where mod(e.user_id, %(base)s) = %(r)s and e.enddate is not null and e.enddate <= h.startdate + 182
  group by 1
),
u as (select user_id, updated_dt from revelio.individual_user where mod(user_id, %(base)s) = %(r)s)
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

BASE = int(os.environ.get("BASE", 20)); RETRIES = int(os.environ.get("RETRIES", 6))
CAT = ["half", "soc6", "sg", "xf", "xg", "mv", "upd"]

def pull_bucket(us, r, path):
    for k in range(RETRIES):
        db = None
        try:
            db = connect(keepalive=True); t = time.time()
            df = db.raw_sql(SQL, params={"us": us, "base": BASE, "r": r})
            df["n"] = df.n.astype("int32")
            for c in CAT: df[c] = df[c].astype("category")
            df.to_parquet(path + ".tmp", index=False); os.replace(path + ".tmp", path)
            print(f"bucket r={r}: {len(df):,} rows, {int(df.n.sum()):,} hires, {time.time()-t:.0f}s", flush=True); return
        except Exception as e:  # OperationalError (SSL timeout, dropped connection) etc.: reconnect and retry
            print(f"bucket r={r} attempt {k+1} failed: {type(e).__name__}: {str(e)[:200]}", flush=True)
            time.sleep(min(60 * 2 ** k, 900))
        finally:
            try: db and db.close()
            except Exception: pass
    raise RuntimeError(f"bucket r={r} failed after {RETRIES} attempts")

def main():
    assert BASE % MOD == 0, "BASE must be a multiple of MOD"
    os.makedirs(OUT, exist_ok=True); f = os.path.join(OUT, "hires_exp.parquet" if MOD == 5 else f"hires_exp_m{MOD}.parquet")
    if os.path.exists(f): print("exists", f); return
    parts = os.path.join(OUT, f"m{MOD}_parts"); os.makedirs(parts, exist_ok=True)
    fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet"))
    us = [int(x) for x in fl[fl.country == "United States"].rcid]
    rs = list(range(0, BASE, MOD)); t = time.time()
    m20 = os.path.join(OUT, "hires_exp_m20.parquet")
    for r in rs:
        p = os.path.join(parts, f"r{r}.parquet")
        if os.path.exists(p): print(f"bucket r={r}: done, skip", flush=True); continue
        if r == 0 and BASE == 20 and MOD != 20 and os.path.exists(m20):
            shutil.copy(m20, p); print(f"bucket r=0: reused {m20}", flush=True); continue
        pull_bucket(us, r, p)
    df = pd.concat([pd.read_parquet(os.path.join(parts, f"r{r}.parquet")).drop(columns="mod", errors="ignore") for r in rs], ignore_index=True)
    for c in CAT: df[c] = df[c].astype(str)
    df = df.groupby(["half", "rcid"] + CAT[1:], observed=True, as_index=False).n.sum()
    df["n"] = df.n.astype("int32")
    for c in CAT: df[c] = df[c].astype("category")
    df["mod"] = MOD
    df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
    print(f"{int(df.n.sum()):,} sampled hires, {len(df):,} rows, {os.path.getsize(f)/1e6:.1f} MB, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main()
