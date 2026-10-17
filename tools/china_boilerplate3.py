"""Where do the cut markers fall? Show length buckets and short context for early cuts."""
import sys; sys.path.insert(0, "tools")
from db import connect
db = connect()
CUT = r"(相关推荐|为你优选|相似职位推荐|暂无相似职位|地区人才网招聘|热门招聘|热门城市|热门职位|猜你喜欢|推荐职位|相关职位|职位推荐|附近职位)"
base = """from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
  where p.post_date='2025-10-07' and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0"""
x = db.raw_sql(f"""select (regexp_match(r.description, %(cut)s))[1] marker,
   width_bucket(strpos(r.description, (regexp_match(r.description, %(cut)s))[1]), 0, 3000, 6) b, count(*) n
   {base} group by 1,2 order by 3 desc limit 25""", params={"cut": CUT})
print(x.to_string())
y = db.raw_sql(f"""select left(regexp_replace(r.description, '\\s+', ' ', 'g'), 260) head {base}
   and strpos(r.description, (regexp_match(r.description, %(cut)s))[1]) between 1 and 300 limit 4""", params={"cut": CUT})
for h in y["head"]: print("|", h)
