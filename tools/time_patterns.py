import sys, time, importlib.util; sys.path.insert(0, "tools")
spec = importlib.util.spec_from_file_location("m", "03_stack_language_tags.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from db import connect
db = connect()
base = """from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id = p.job_id where p.post_date>='2024-03-05' and p.post_date<'2024-03-06'
 and p.country in ('United States','China') and p.onet_code like '15-12%%' and p.job_id %% 100 = 0"""
for k, v in list(m.TITLE_TAGS.items()) + list(m.DESC_TAGS.items()):
    col = "coalesce(r.title_raw,'')||' | '||coalesce(r.jobtitle_translated,'')" if k in m.TITLE_TAGS else "coalesce(r.description,'')"
    t = time.time(); n = db.raw_sql(f"select sum(({col} ~* %(p)s)::int) n {base}", params={"p": v}).n[0]
    print(f"{k:14s} {time.time()-t:6.2f}s  n={n}", flush=True)
