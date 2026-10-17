import sys; sys.path.insert(0, "tools")
from db import connect
db = connect()
tabs = ["postings_cosmos","postings_cosmos_raw","postings_role_lookup_v2","postings_role_lookup_v3",
        "layoffs","individual_positions","individual_user_skills","workforce_dynamics_geo"]
print("ALL TABLES:", db.list_tables(library="revelio"))
for t in tabs:
    try:
        d = db.raw_sql(f"select column_name, data_type from information_schema.columns where table_schema='revelio' and table_name='{t}' order by ordinal_position")
        print(f"\n=== {t} ({len(d)} cols)"); print(d.to_string(index=False))
    except Exception as e:
        print(t, "ERR", e)
