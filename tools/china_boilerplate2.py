"""After cutting at end-of-posting markers, how much navigation boilerplate remains? (context printed briefly)"""
import sys; sys.path.insert(0, "tools")
import importlib.util
spec = importlib.util.spec_from_file_location("m", "03_stack_language_tags.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from db import connect
db = connect()
RUN = r"\S+招聘 \S+招聘 \S+招聘"
CUT = r"(相关推荐|为你优选|相似职位推荐|暂无相似职位|地区人才网招聘|热门招聘|热门城市|热门职位|猜你喜欢|推荐职位|相关职位|职位推荐|附近职位).*$"
d = sys.argv[1] if len(sys.argv) > 1 else "2025-10-07"
x = db.raw_sql("""with t as (select r.description ds, regexp_replace(r.description, %(cut)s, '') c
  from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
  where p.post_date=%(d)s and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0)
  select count(*) n, sum((ds ~ %(run)s)::int) boiler_raw, sum((c ~ %(run)s)::int) boiler_after_cut,
    avg(length(ds)) len_raw, avg(length(c)) len_cut,
    sum((ds ~* %(llm)s)::int) llm_raw, sum((c ~* %(llm)s)::int) llm_cut,
    sum((ds ~* %(go)s)::int) go_raw, sum((c ~* %(go)s)::int) go_cut,
    sum((ds ~* %(java)s)::int) java_raw, sum((c ~* %(java)s)::int) java_cut from t""",
  params={"d": d, "cut": CUT, "run": RUN, "llm": m.DESC_TAGS["llm_ai"], "go": m.DESC_TAGS["go"], "java": m.DESC_TAGS["java"]})
print(x.T.to_string())
y = db.raw_sql("""select (regexp_match(regexp_replace(r.description, %(cut)s, ''), %(ctx)s))[1] ctx
  from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
  where p.post_date=%(d)s and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0
  and regexp_replace(r.description, %(cut)s, '') ~ %(run)s limit 5""", params={"d": d, "cut": CUT, "run": RUN, "ctx": "(.{0,80}" + RUN + ".{0,40})"})
for c in y.ctx: print("|", str(c).replace("\n", " "))
