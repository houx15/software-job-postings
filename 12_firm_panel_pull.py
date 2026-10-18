"""P2 (docs/did_design.md): firm x month x seniority group x SOC-2018 6-digit occupation x source group, US and China,
2021-01..2026-09, for firms with >= 50 pre-period (2021-01..2022-10) postings (data/firms/firm_list.parquet from 11).
Server-side aggregate, one scan per month (resumable). seniority group: early = 1-2, exp = 3-4 (5-7 dropped).
source group: li_only (LinkedIn and no other flag) / cn_board (zhaopin/51job/liepin, no LinkedIn) / other.
Output (git-ignored): data/firm_panel/YYYY-MM.parquet.  Usage: uv run python 12_firm_panel_pull.py 2021-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "firm_panel")
MAX_BYTES = 5 * 1024**3
OTHER = ["source_company_sites", "source_indeed", "source_zhaopin", "source_51job", "source_liepin",
         "source_other_aggregators", "source_staffingfirms", "source_regional_aggregators"]
SQL = """
with f as (select unnest(%(us)s::bigint[]) rcid, 'United States'::text country
           union all select unnest(%(cn)s::bigint[]), 'China')
select p.country, p.ultimate_parent_rcid rcid, left(p.onet_code, 7) soc6,
       case when p.seniority <= 2 then 'early' else 'exp' end sg,
       case when coalesce(p.source_linkedin, false) and not (""" + " or ".join(f"coalesce(p.{s}, false)" for s in OTHER) + """) then 'li_only'
            when (coalesce(p.source_zhaopin, false) or coalesce(p.source_51job, false) or coalesce(p.source_liepin, false))
                 and not coalesce(p.source_linkedin, false) then 'cn_board'
            else 'other' end src,
       count(*) n
from revelio.postings_cosmos p join f on f.rcid = p.ultimate_parent_rcid and f.country = p.country
where p.post_date >= %(start)s and p.post_date < %(end)s and p.country in ('United States', 'China')
  and p.seniority between 1 and 4 and p.onet_code is not null
group by 1, 2, 3, 4, 5
"""

def data_bytes():
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(HERE, "data")) for f in fs)

def main(a, b):
    os.makedirs(OUT, exist_ok=True)
    fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet"))
    us = [int(x) for x in fl[fl.country == "United States"].rcid]; cn = [int(x) for x in fl[fl.country == "China"].rcid]
    db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        if data_bytes() > MAX_BYTES:
            sys.exit("data/ over 5 GB guard, stopping")
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat(),
                                     "us": us, "cn": cn}).copy()
        df["n"] = df.n.astype("int32"); df["rcid"] = df.rcid.astype("int64")
        for c in ["country", "soc6", "sg", "src"]:
            df[c] = df[c].astype("category")
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: {int(df.n.sum()):,} postings, {len(df):,} rows, {os.path.getsize(f)/1e6:.1f} MB, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
