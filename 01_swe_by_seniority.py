"""第一版：头部科技公司软件类岗位，按职级 × 月份计数（美国 vs 中国）。
在 Princeton 的电脑上运行：pip install wrds pandas；首次运行会提示输入 WRDS 用户名和密码。
TABLE 需要先确认：在 WRDS 网页的 Revelio 页面，或运行 db.list_tables('revelio') 查看真实表名。
"""
import wrds, pandas as pd

db = wrds.Connection()
print(db.list_tables(library="revelio"))   # 先看表名，把下一行改对
TABLE = "revelio.postings_cosmos"           # 占位，可能不是真实表名

# Revelio 的 seniority 分 1–7 档：1 入门，2 初级，3 中级，4 经理，5 总监，6 高管，7 高级高管（以字典为准）
SQL = f"""
select date_trunc('month', post_date) as month,
       country, seniority,
       ultimate_parent_company_name as parent,
       count(*) as n_posts,
       sum(expected_hires) as exp_hires,
       avg(salary) as avg_salary
from {TABLE}
where post_date >= %(start)s and post_date < %(end)s
  and country in ('United States','China')
  and onet_code like '15-12%%'              -- 计算机职业，含 15-1252 软件开发
group by 1,2,3,4
"""
frames = []
for y in range(2018, 2027):                 # 按年分批，避开单次查询太大
    df = db.raw_sql(SQL, params={"start": f"{y}-01-01", "end": f"{y+1}-01-01"})
    df.to_parquet(f"swe_{y}.parquet"); frames.append(df); print(y, len(df))
pd.concat(frames).to_parquet("swe_monthly_by_seniority.parquet")
