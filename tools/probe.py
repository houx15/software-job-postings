import sys, time; sys.path.insert(0, "tools")
from db import connect
db = connect()
def q(label, sql):
    t=time.time(); d=db.raw_sql(sql); print(f"\n--- {label} ({time.time()-t:.1f}s)"); print(d.to_string(index=False)); sys.stdout.flush()
q("indexes", "select indexname, indexdef from pg_indexes where schemaname='revelio' and tablename in ('postings_cosmos','postings_cosmos_raw','layoffs')")
q("est rows", "select relname, reltuples::bigint, pg_size_pretty(pg_total_relation_size(oid)) from pg_class where relname in ('postings_cosmos','postings_cosmos_raw','layoffs','postings_cosmos_raw_p0') and relnamespace='revelio'::regnamespace")
q("sample 5", "select job_id, company, country, onet_code, seniority, role_k1500_v2, post_date, salary from revelio.postings_cosmos limit 5")
