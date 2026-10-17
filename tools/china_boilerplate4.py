"""Test the content-block extraction for scraped Chinese job pages (51job-style full-page scrapes)."""
import sys; sys.path.insert(0, "tools")
import importlib.util
spec = importlib.util.spec_from_file_location("m", "03_stack_language_tags.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from db import connect
db = connect()
START = "职位信息"
END = r"(工作地址|上班地址|公司信息|微信分享|相关推荐|为你优选|相似职位推荐|暂无相似职位|地区人才网招聘|热门招聘|热门城市|热门职位|猜你喜欢|推荐职位|相关职位|附近职位).*$"
RUN = r"\S+招聘 \S+招聘 \S+招聘"
CLEAN = "regexp_replace(case when strpos(ds, %(st)s) > 0 then substr(ds, strpos(ds, %(st)s)) else ds end, %(end)s, '')"
P = {"d": sys.argv[1] if len(sys.argv) > 1 else "2025-10-07", "st": START, "end": END, "run": RUN,
     "llm": m.DESC_TAGS["llm_ai"], "java": m.DESC_TAGS["java"], "py": m.DESC_TAGS["py"]}
base = """with t0 as (select r.description ds from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
  where p.post_date=%(d)s and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0),
  t as (select ds, """ + CLEAN + """ c from t0)"""
x = db.raw_sql(base + """ select count(*) n, sum((ds ~ %(run)s)::int) boiler_raw, sum((c ~ %(run)s)::int) boiler_after,
   avg(length(ds)) len_raw, avg(length(c)) len_clean, sum((length(c) < 150)::int) n_short,
   sum((ds ~* %(llm)s)::int) llm_raw, sum((c ~* %(llm)s)::int) llm_clean, sum((ds ~* %(java)s)::int) java_raw,
   sum((c ~* %(java)s)::int) java_clean, sum((ds ~* %(py)s)::int) py_raw, sum((c ~* %(py)s)::int) py_clean from t""", params=P)
print(x.T.to_string())
y = db.raw_sql(base + " select left(regexp_replace(c, '\\s+', ' ', 'g'), 160) h, right(regexp_replace(c, '\\s+', ' ', 'g'), 100) tl from t where ds ~ %(run)s limit 4", params=P)
for _, r in y.iterrows(): print("HEAD|", r.h, "\nTAIL|", r.tl)
