"""Show this WRDS user's active queries (state, runtime, wait event) to monitor long background pulls."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect
db = connect()
print(db.raw_sql("""select pid, state, now() - query_start as runtime, wait_event_type, wait_event, left(query, 60) q
  from pg_stat_activity where usename = current_user and pid <> pg_backend_pid()""").to_string())
