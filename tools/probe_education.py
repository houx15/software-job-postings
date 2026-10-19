"""Probe: Revelio individual tables available (education?), column types of individual_positions, position_number semantics."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect
db = connect()
print(db.raw_sql("select table_name from information_schema.tables where table_schema='revelio' and table_name ilike 'individual%%'").to_string())
print(db.raw_sql("""select table_name, column_name, data_type from information_schema.columns where table_schema='revelio'
  and (table_name ilike '%%educ%%' or (table_name='individual_positions' and column_name in ('user_id','position_number','startdate','enddate')))""").to_string())
x = db.raw_sql("""select user_id, position_number, startdate, enddate, ultimate_parent_rcid, seniority, left(onet_code,7) soc6, country
  from revelio.individual_positions where user_id in (select user_id from revelio.individual_positions where startdate='2024-03-01' and country='United States' limit 3)
  order by user_id, position_number""")
print(x.to_string())
