import sys, time; sys.path.insert(0, "tools")
from db import connect
db = connect()
def q(label, sql):
    t=time.time(); d=db.raw_sql(sql); print(f"\n--- {label} ({time.time()-t:.1f}s)"); print(d.to_string(index=False)); sys.stdout.flush(); return d
q("relkind", "select c.relname, c.relkind from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='revelio' and c.relname in ('postings_cosmos','postings_cosmos_raw','layoffs')")
q("seniority, 1 month all countries", "select seniority, count(*) n from revelio.postings_cosmos where post_date>='2024-03-01' and post_date<'2024-04-01' group by 1 order by 1")
q("country spellings (China-ish), 1 month", "select country, count(*) n from revelio.postings_cosmos where post_date>='2024-03-01' and post_date<'2024-04-01' and (country ilike '%china%' or country ilike '%united states%' or country ilike '%hong kong%' or country ilike '%taiwan%') group by 1")
q("seniority x title SWE US 1 month", "select seniority, count(*) n, avg(salary) avg_sal, mode() within group (order by role_k1500_v2) top_role from revelio.postings_cosmos where post_date>='2024-03-01' and post_date<'2024-04-01' and country='United States' and onet_code like '15-12%' group by 1 order by 1")
