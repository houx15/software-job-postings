"""Probe: underlying table and indexes of revelio.individual_positions (to plan an external-hire flag)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect
db = connect()
print(db.raw_sql("select pg_get_viewdef('revelio.individual_positions'::regclass) d").d[0][:600])
print(db.raw_sql("""select schemaname, tablename, indexname, indexdef from pg_indexes
                    where tablename ilike '%%individual_position%%'""").to_string())
