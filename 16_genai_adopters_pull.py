"""Benchmark replication input (Hosseini Maasoum & Lichtinger 2025, SSRN 5425555): firm GenAI adoption proxied by postings
for GenAI "integrator" roles. HL flag GenAI keywords then LLM-screen; here we use Revelio's role taxonomy instead:
role_k17000_v3 in ('Generative AI Engineer', 'Conversational AI Engineer') (cheap, server-side, no text download).
US, all firms, 2021-01..2026-09, monthly counts per ultimate parent. Output (git-ignored, company IDs stay in data/):
data/genai/YYYY-MM.parquet.  Usage: uv run python 16_genai_adopters_pull.py 2021-01 2026-09
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "genai")
SQL = """
select ultimate_parent_rcid rcid, role_k17000_v3 role, count(*) n
from revelio.postings_cosmos
where post_date >= %(start)s and post_date < %(end)s and country = 'United States' and ultimate_parent_rcid is not null
  and role_k17000_v3 in ('Generative AI Engineer', 'Conversational AI Engineer')
group by 1, 2
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True); db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f): continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat()}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        print(f"{m}: {len(df):,} firms, {int(df.n.sum()):,} GenAI postings, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
