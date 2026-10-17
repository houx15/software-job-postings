"""Diagnose scraped site-navigation boilerplate ("XX招聘 YY招聘 ...") in China descriptions. Prints only offsets + short context."""
import sys; sys.path.insert(0, "tools")
from db import connect
db = connect()
RUN = r"\S+招聘 \S+招聘 \S+招聘"
base = """from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
 where p.post_date=%(d)s and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0"""
P = {"d": sys.argv[1] if len(sys.argv) > 1 else "2025-10-07", "run": RUN, "ctx": "(.{0,100})(" + RUN + ")"}
d = db.raw_sql(f"""select length(r.description) dlen, strpos(r.description, '职能类别') pos_zn,
  strpos(r.description, (regexp_match(r.description, %(run)s))[1]) pos_run,
  (regexp_match(r.description, %(ctx)s))[1] before_run, p.source_51job s51, p.source_liepin slp, p.source_zhaopin szp
  {base} and r.description ~ %(run)s limit 8""", params=P)
for _, r in d.iterrows():
    print(r.dlen, r.pos_zn, r.pos_run, r.s51, r.slp, r.szp, "|", str(r.before_run).replace("\n", " ")[-100:])
print(db.raw_sql(f"""select count(*) n, sum((r.description ~ %(run)s)::int) n_boiler, sum(p.source_51job::int) n51,
  sum((p.source_51job and r.description ~ %(run)s)::int) n51_boiler {base}""", params=P).to_string())
