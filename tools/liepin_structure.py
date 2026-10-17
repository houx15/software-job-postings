"""Section headers in Liepin full-page scrapes: show text in 120-char windows (positions only, 2 pages)."""
import sys, re; sys.path.insert(0, "tools")
from db import connect
db = connect()
y = db.raw_sql("""select regexp_replace(r.description, '\\s+', ' ', 'g') d from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id=p.job_id
  where p.post_date='2025-10-07' and p.country='China' and p.onet_code like '15-12%%' and p.job_id %% 20 = 0 and r.description like '%%-猎聘%%' limit 2""", params={"x": 1})
for d in y.d:
    print(len(d))
    for i in range(0, min(len(d), 3000), 300): print(i, "|", d[i:i+120])
    print("----")
