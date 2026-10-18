"""Probe: where the experience requirement sits in CN-board descriptions (snippets around 经验; inspection only)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect
db = connect()
y = db.raw_sql("""select p.source_zhaopin z, p.source_51job j, p.source_liepin l, length(r.description) len,
  regexp_replace(r.description, '\\s+', ' ', 'g') d
  from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
  where p.post_date = '2024-03-05' and p.country = 'China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0
    and not coalesce(p.source_linkedin, false) and (p.source_zhaopin or p.source_51job or p.source_liepin) limit 12""")
for _, r in y.iterrows():
    d = r.d or ""
    print("Z" if r.z else "", "J" if r.j else "", "L" if r.l else "", r.len, "| head:", d[:200])
    for m in list(re.finditer("经验|年以上|学历", d))[:4]:
        print("   ...", d[max(0, m.start()-50): m.end()+30])
    print("---")
