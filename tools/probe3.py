import sys, time; sys.path.insert(0, "tools")
from db import connect
db = connect()
P={"s":"2024-03-01","e":"2024-04-01"}
def q(label, sql, p=P):
    t=time.time(); d=db.raw_sql(sql, params=p); print(f"\n--- {label} ({time.time()-t:.1f}s)"); print(d.to_string(index=False)); sys.stdout.flush(); return d
q("date range", "select min(post_date) mn, max(post_date) mx from revelio.postings_cosmos where %(s)s=%(s)s")
q("country top 40, 1 month", "select country, count(*) n from revelio.postings_cosmos where post_date>=%(s)s and post_date<%(e)s group by 1 order by 2 desc limit 40")
q("SWE (15-12) by country x seniority, 1 month, US/China/HK/TW", "select country, seniority, count(*) n, avg(salary) avg_sal, sum(expected_hires) eh, avg(salary_predicted::int) share_pred from revelio.postings_cosmos where post_date>=%(s)s and post_date<%(e)s and country in ('United States','China','Hong Kong','Taiwan') and onet_code like '15-12%%' group by 1,2 order by 1,2")
q("SWE source mix, US/China", "select country, avg(source_company_sites::int) cs, avg(source_linkedin::int) li, avg(source_indeed::int) ind, avg(source_zhaopin::int) zp, avg(source_51job::int) j51, avg(source_liepin::int) lp, avg(source_other_aggregators::int) oth, avg(source_staffingfirms::int) staff, avg(source_regional_aggregators::int) reg, count(distinct ultimate_parent_rcid) n_parents from revelio.postings_cosmos where post_date>=%(s)s and post_date<%(e)s and country in ('United States','China') and onet_code like '15-12%%' group by 1")
q("top SWE roles by seniority sample US", "select seniority, role_k1500_v2, count(*) n from revelio.postings_cosmos where post_date>=%(s)s and post_date<%(e)s and country='United States' and onet_code like '15-12%%' group by 1,2 order by 3 desc limit 40")
q("monthly totals overall (yearly sample, date index)", "select date_trunc('year',post_date)::date y, count(*) n from revelio.postings_cosmos where post_date>='2016-01-01' and post_date<'2016-01-08' group by 1", {})
