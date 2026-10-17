"""Face-validity check of Revelio seniority: title keywords x seniority, US + China computer occupations, one day."""
import sys, time; sys.path.insert(0, "tools")
from db import connect
db = connect()
SQL = """
with p as (
  select job_id, country, seniority from revelio.postings_cosmos
  where post_date = %(d)s and country in ('United States','China') and onet_code like '15-12%%'
), t as (
  select p.country, p.seniority, lower(coalesce(r.jobtitle_translated, r.title_raw)) tt, r.title_raw
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
)
select country, seniority,
  case when tt ~ '(intern|trainee|graduate|new grad|campus|实习|校招|应届)' then '1 intern/grad'
       when tt ~ '(junior|\\mjr\\M|entry|associate engineer|\\m(i|1)\\M$|初级)' then '2 junior/entry'
       when tt ~ '(principal|staff|distinguished|architect|架构)' then '5 staff/principal'
       when tt ~ '(director|vp|vice president|head of|总监)' then '6 director+'
       when tt ~ '(manager|lead|经理|主管)' then '4 manager/lead'
       when tt ~ '(senior|\\msr\\M|\\m(iii|3)\\M$|高级|资深)' then '3 senior'
       else '0 no keyword' end as kw,
  count(*) n
from t group by 1,2,3 order by 1,3,2
"""
t=time.time(); d=db.raw_sql(SQL, params={"d": "2024-03-05"}); print(f"{time.time()-t:.0f}s")
x=d.pivot_table(index=["country","kw"], columns="seniority", values="n", aggfunc="sum", fill_value=0)
print(x.to_string())
x.to_csv("docs/seniority_validation_2024-03-05.csv")
