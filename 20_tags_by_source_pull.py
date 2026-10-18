"""Exploration B: the tech-stack / language / AI tags of 03_stack_language_tags.py, re-pulled with a source-group split so
that China (and US) stack trends can be computed within a consistent source. Same regexes, same Chinese boilerplate
cleaning, same deterministic job_id sample (US 1/50, China 1/20); 03 is imported, nothing is redefined.
source group (mutually exclusive, as in 12): li_only = LinkedIn and no other flag; cn_board = zhaopin/51job/liepin and
not LinkedIn; other = everything else.
Output (git-ignored): data/tags_src/YYYY-MM.parquet.  Usage: uv run python 20_tags_by_source_pull.py 2021-01 2026-09
"""
import importlib.util, os, sys, time
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
from db import connect
spec = importlib.util.spec_from_file_location("tags03", os.path.join(HERE, "03_stack_language_tags.py"))
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
OUT = os.path.join(HERE, "data", "tags_src")
OTHER = ["source_company_sites", "source_indeed", "source_zhaopin", "source_51job", "source_liepin",
         "source_other_aggregators", "source_staffingfirms", "source_regional_aggregators"]
SRC = ("case when coalesce(source_linkedin, false) and not (" + " or ".join(f"coalesce({s}, false)" for s in OTHER) +
       ") then 'li_only' when (coalesce(source_zhaopin, false) or coalesce(source_51job, false) or coalesce(source_liepin, false))"
       " and not coalesce(source_linkedin, false) then 'cn_board' else 'other' end")

def build_sql():
    flags = [f"(tt ~* %(t_{k})s)::int as {k}" for k in T.TITLE_TAGS] + \
            [(f"(coalesce(ds,'') ~* %(d_{k})s or coalesce(ds,'') ~ %(cs_{k})s)::int as {k}" if k in T.DESC_CS
              else f"(coalesce(ds,'') ~* %(d_{k})s)::int as {k}") for k in T.DESC_TAGS]
    sums = [f"sum({k}) as {k}" for k in list(T.TITLE_TAGS) + list(T.DESC_TAGS)]
    any_stack = " + ".join(k for k in T.TITLE_TAGS if k != "swe_generic")
    return f"""
with p as (
  select job_id, country, {SRC} as src,
         case when seniority <= 2 then 'early' when seniority = 3 then 'mid'
              when seniority = 4 then 'senior' else 'lead' end as sen_group
  from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s
    and country in ('United States', 'China') and onet_code like '15-12%%'
    and job_id %% (case when country = 'China' then {T.SAMPLE_MOD['China']} else {T.SAMPLE_MOD['United States']} end) = 0
), t as (
  select p.country, p.src, p.sen_group,
         coalesce(r.title_raw, '') || ' | ' || coalesce(r.jobtitle_translated, '') as tt,
         {T.CLEAN_DESC} as ds
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
), f as (
  select country, src, sen_group, (ds is not null and length(ds) > 150)::int as has_desc, {", ".join(flags)} from t
)
select country, src, sen_group, count(*) as n, sum(has_desc) as n_desc,
       sum(case when ({any_stack}) = 0 then 1 else 0 end) as no_stack_tag, {", ".join(sums)}
from f group by 1, 2, 3
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True); db, sql = connect(), build_sql()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f): continue
        if T.data_bytes() > T.MAX_BYTES: sys.exit("data/ exceeds 5 GB, stopping")
        t = time.time()
        df = db.raw_sql(sql, params=T.params(m.start_time.date().isoformat(), (m + 1).start_time.date().isoformat())).copy()
        df.insert(0, "month", str(m)); df["sample_mod"] = df.country.map(T.SAMPLE_MOD)
        df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: n={int(df.n.sum()):,} sampled postings, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
