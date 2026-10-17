import sys, time; sys.path.insert(0, "tools")
from db import connect
db = connect()
def q(label, sql, p={"x":1}):
    t=time.time(); d=db.raw_sql(sql, params=p); print(f"\n--- {label} ({time.time()-t:.1f}s)"); print(d.to_string(index=False)); sys.stdout.flush(); return d
q("overview", "select count(*) n, min(notice_date) mn, max(notice_date) mx, count(distinct state) n_states, sum(num_employees) emp from revelio.layoffs")
q("by year", "select extract(year from notice_date)::int y, count(*) n, sum(num_employees) emp from revelio.layoffs group by 1 order by 1")
q("layoff_type", "select layoff_type, count(*) n from revelio.layoffs group by 1 order by 2 desc limit 20")
q("sample", "select company_raw, company, state, city, notice_date, layoff_date, layoff_type, num_employees, ultimate_parent_company_name from revelio.layoffs order by notice_date desc limit 10")
q("top parents 2023", "select ultimate_parent_company_name, count(*) n, sum(num_employees) emp from revelio.layoffs where notice_date>='2023-01-01' and notice_date<'2024-01-01' group by 1 order by 3 desc nulls last limit 25")
