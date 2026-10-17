import sys, time, importlib.util; sys.path.insert(0, "tools")
spec = importlib.util.spec_from_file_location("m", "03_stack_language_tags.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from db import connect
db = connect()
mod = int(sys.argv[1]); s, e = sys.argv[2], sys.argv[3]
t = time.time(); d = db.raw_sql(m.build_sql(), params=m.params(s, e)); print(f"mod={mod} {s}..{e}: {time.time()-t:.1f}s, n={d.n.sum()}")
print(d[["country","sen_group","n","n_desc","no_stack_tag","fullstack","frontend","backend","mobile","ml_ai","py","java","js","go","c","llm_ai"]].to_string())
