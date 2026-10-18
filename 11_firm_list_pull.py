"""P2 step 1: pre-period firm sizes (ultimate_parent_rcid x country), 2021-01..2022-10 (pre-ChatGPT), all occupations,
seniority 1-4 only. Server-side counts per month, summed locally. Output (git-ignored, company IDs stay in data/):
  data/firms/pre_counts/YYYY-MM.parquet, data/firms/firm_list.parquet (firms with >= MIN_PRE pre-period postings).
Usage: uv run python 11_firm_list_pull.py
"""
import glob, os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "firms")
MIN_PRE = 50
SQL = """
select country, ultimate_parent_rcid rcid, count(*) n, sum((seniority <= 2)::int) n_early
from revelio.postings_cosmos
where post_date >= %(start)s and post_date < %(end)s and country in ('United States', 'China')
  and seniority between 1 and 4 and ultimate_parent_rcid is not null
group by 1, 2
"""

def main():
    os.makedirs(os.path.join(OUT, "pre_counts"), exist_ok=True)
    db = connect()
    for m in pd.period_range("2021-01", "2022-10", freq="M"):
        f = os.path.join(OUT, "pre_counts", f"{m}.parquet")
        if os.path.exists(f):
            continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat()}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: {len(df):,} firms, {time.time()-t:.0f}s", flush=True)
    d = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(OUT, "pre_counts", "*.parquet"))))
    g = d.groupby(["country", "rcid"])[["n", "n_early"]].sum().reset_index()
    keep = g[g.n >= MIN_PRE]
    keep.to_parquet(os.path.join(OUT, "firm_list.parquet"), index=False)
    for c, x in g.groupby("country"):
        k = keep[keep.country == c]
        print(f"{c}: {len(x):,} firms, {len(k):,} with >= {MIN_PRE} pre postings, covering {100*k.n.sum()/x.n.sum():.1f}% of pre postings")

if __name__ == "__main__":
    main()
