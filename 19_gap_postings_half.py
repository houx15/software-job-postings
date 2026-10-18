"""Exploration A, step 1: US postings at firm x SOC6 x half-year x seniority group x source group, from the P2 monthly
files (data/firm_panel, 12_firm_panel_pull.py). Pure local aggregation, no WRDS.
Output (git-ignored): data/explore/postings_fo_half.parquet (columns half, rcid, soc6, sg, src, n).
Usage: uv run python 19_gap_postings_half.py
"""
import glob, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "data", "explore"); os.makedirs(OUT, exist_ok=True)
parts = []
for f in sorted(glob.glob(os.path.join(HERE, "data", "firm_panel", "*.parquet"))):
    m = pd.Period(os.path.basename(f)[:7], "M"); half = f"{m.year}H{1 if m.month <= 6 else 2}"
    x = pd.read_parquet(f, columns=["country", "rcid", "soc6", "sg", "src", "n"])
    x = x[x.country == "United States"].drop(columns="country")
    x = x.groupby(["rcid", "soc6", "sg", "src"], observed=True).n.sum().reset_index(); x["half"] = half
    parts.append(x)
d = pd.concat(parts, ignore_index=True)
for c in ["soc6", "sg", "src"]: d[c] = d[c].astype(str)
d = d.groupby(["half", "rcid", "soc6", "sg", "src"]).n.sum().reset_index()
d["n"] = d.n.astype("int32")
for c in ["half", "soc6", "sg", "src"]: d[c] = d[c].astype("category")
d.to_parquet(os.path.join(OUT, "postings_fo_half.parquet"), index=False)
print(len(d), int(d.n.sum()), d.groupby("half", observed=True).n.sum().to_string())
