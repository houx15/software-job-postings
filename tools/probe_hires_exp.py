"""Smoke test of 24's SQL on a tiny user sample (mod 2000) to check runtime and output shape before the full run."""
import importlib.util, os, sys, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, "tools"))
import pandas as pd
from db import connect
spec = importlib.util.spec_from_file_location("p24", os.path.join(HERE, "24_hires_exp_pull.py")); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
fl = pd.read_parquet(os.path.join(HERE, "data", "firms", "firm_list.parquet")); us = [int(x) for x in fl[fl.country == "United States"].rcid]
db = connect(); t = time.time(); m = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
d = db.raw_sql(P.SQL, params={"us": us, "mod": m}); print(len(d), int(d.n.sum()), f"{time.time()-t:.0f}s")
for c in ["sg", "xf", "xg", "mv", "upd", "half"]: print(d.groupby(c).n.sum().to_dict())
print(pd.crosstab(d.xf, d.sg, values=d.n, aggfunc="sum")); print(pd.crosstab(d.xg, d.xf, values=d.n, aggfunc="sum"))
