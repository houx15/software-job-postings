"""P1 for Design A (docs/did_design.md): ALL occupations, month x country x O*NET code x seniority x source group x staffing flag.
Server-side aggregate, one date-indexed scan per month, resumable. Output: data/occ_panel/YYYY-MM.parquet.
source group (mutually exclusive):
  li_only   : source_linkedin and no other source flag
  li_plus   : source_linkedin plus at least one other source
  cn_board  : zhaopin / 51job / liepin, no LinkedIn
  other     : everything else (company sites, Indeed, aggregators, staffing boards ...)
staffing : ultimate_parent_rcid in data/staffing_rcids.csv (git-ignored; built from data/agg parent names) (parents whose name matches the staffing/outsourcing regex of 02/08 and
           with >=100 computer-occupation postings 2020-2026 in data/agg; 890 parents) or source_staffingfirms.
           (A per-row name regex made each month take ~330 s; the rcid hash join is much cheaper.)
Usage: uv run python 09_occ_panel_pull.py 2021-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "occ_panel")
MAX_BYTES = 5 * 1024**3
STAFF_RE = (r"staffing|lynx|robert half|allegis|insight global|teksystems|randstad|adecco|manpower|kforce|everforth|recruit|"
            r"apex systems|kelly services|hays|michael page|cybercoders|chinasoft|farben|法本|中软|wicresoft|archermind|fesco|"
            r"人力|外包|northking|isoftstone|hirain")
OTHER = ["source_company_sites", "source_indeed", "source_zhaopin", "source_51job", "source_liepin",
         "source_other_aggregators", "source_staffingfirms", "source_regional_aggregators"]
SQL = """
with b as (
  select country, onet_code, seniority,
         coalesce(source_linkedin, false) li,
         (""" + " or ".join(f"coalesce({f}, false)" for f in OTHER) + """) any_other,
         (coalesce(source_zhaopin, false) or coalesce(source_51job, false) or coalesce(source_liepin, false)) cn,
         (coalesce(source_staffingfirms, false) or s.rcid is not null) staff
  from revelio.postings_cosmos p
  left join (select unnest(%(rcids)s::bigint[]) rcid) s on s.rcid = p.ultimate_parent_rcid
  where post_date >= %(start)s and post_date < %(end)s and country in ('United States', 'China')
)
select country, onet_code, seniority,
       case when li and not any_other then 'li_only' when li then 'li_plus' when cn then 'cn_board' else 'other' end src,
       staff, count(*) n
from b group by 1, 2, 3, 4, 5
"""

RCIDS = [int(x) for x in pd.read_csv(os.path.join(HERE, "data", "staffing_rcids.csv")).rcid]

def data_bytes():
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(HERE, "data")) for f in fs)

def main(a, b):
    os.makedirs(OUT, exist_ok=True)
    db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        if data_bytes() > MAX_BYTES:
            sys.exit("data/ over 5 GB guard, stopping")
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat(),
                                     "rcids": RCIDS}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: {int(df.n.sum()):,} postings, {len(df):,} cells, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
