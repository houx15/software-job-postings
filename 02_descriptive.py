"""Descriptive figures from data/agg (output of 01). Months are 'YYYY-MM' strings (no pandas datetime ops:
pandas 2.2.3 datetime code segfaults on this Python 3.14 build).

Figures -> figures/ ; summary tables -> data/summary/ (derived WRDS data, kept out of git).
Measures:
  computer occupations = O*NET 15-12xx (includes IT support, network admin, etc.)
  software (narrow)    = 15-1252 software developers, 15-1253 QA/testers, 15-1254 web developers
  entry share          = seniority 1 / all;  early-career share = seniority 1+2 / all
"""
import glob, os, re
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG, SUM = os.path.join(HERE, "figures"), os.path.join(HERE, "data", "summary")
os.makedirs(FIG, exist_ok=True); os.makedirs(SUM, exist_ok=True)
NARROW = {"15-1252", "15-1253", "15-1254"}
STAFFING = re.compile(r"staffing|lynx|robert half|allegis|insight global|teksystems|randstad|adecco|manpower|kforce|"
                      r"cybercoders|apex systems|kelly services|hays|aerotek|collabera|infosys bpm|dataannotation", re.I)
COL = {"United States": "#1f4e79", "China": "#c0392b"}
LAST_FULL = "2026-08"   # 2026-09 is partial (data end 2026-09-06)

files = sorted(glob.glob(os.path.join(HERE, "data", "agg", "*.parquet")))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d = d[d.month <= LAST_FULL]
for c in ["n_posts", "seniority", "swe_parent"]:
    d[c] = d[c].astype("float64")
months = sorted(d.month.unique())
print(f"{len(files)} month files, {months[0]}..{months[-1]}, {len(d):,} aggregate rows")

def xaxis(ax):
    ticks = [i for i, m in enumerate(months) if m.endswith("-01")]
    ax.set_xticks(ticks); ax.set_xticklabels([months[i][:4] for i in ticks])
    ax.set_xlim(0, len(months) - 1); ax.grid(alpha=.3)

def series(df, by=("month", "country")):
    return df.groupby(list(by)).n_posts.sum().unstack("country").reindex(months)

onet, occ2, par = d[d.gset == "onet"], d[d.gset == "occ2"], d[d.gset == "parent"]
comp = series(onet)
narrow = series(onet[onet.swe_onet.isin(NARROW)])
allp = series(occ2)

def index_to(s, year):
    base = s.loc[[m for m in months if m.startswith(year)]].mean()
    return 100 * s / base

# ---- Fig 1: monthly postings, indexed to 2019 and 2022 (3-month moving average)
fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
for row, (lab, s) in enumerate([("Computer occupations (O*NET 15-12xx)", comp), ("Software dev/QA/web (15-1252/53/54)", narrow)]):
    for col, yr in enumerate(["2019", "2022"]):
        ax = axes[row, col]
        for c in COL:
            ax.plot(index_to(s[c], yr).rolling(3, min_periods=1).mean().values, color=COL[c], label=c)
        ax.axhline(100, color="grey", lw=.8); ax.set_title(f"{lab}\nindex, {yr} avg = 100 (3-mo MA)", fontsize=10); xaxis(ax)
axes[0, 0].legend(); fig.suptitle("Revelio COSMOS new job postings, US vs China", fontsize=12); fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_monthly_postings_index.png"), dpi=150); plt.close(fig)

# ---- Fig 1b: raw monthly counts + software share of all postings (coverage check)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
for c in COL:
    axes[0].plot(comp[c].values / 1e3, color=COL[c], label=f"{c}: computer occ.")
    axes[0].plot(narrow[c].values / 1e3, color=COL[c], ls="--", label=f"{c}: software (narrow)")
    axes[1].plot(100 * comp[c].values / allp[c].values, color=COL[c], label=c)
axes[0].set_title("New postings per month (thousands)"); axes[0].legend(fontsize=8)
axes[1].set_title("Computer occupations as % of all postings in country"); axes[1].legend()
for ax in axes: xaxis(ax)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1b_counts_and_share_of_all.png"), dpi=150); plt.close(fig)

# ---- Fig 2: seniority composition over time (stacked shares), computer occupations
sen = onet.groupby(["month", "country", "seniority"]).n_posts.sum()
fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
labels = {1: "1 Entry", 2: "2 Junior", 3: "3 Associate", 4: "4 Manager/Sr IC", 5: "5 Director", 6: "6 Exec", 7: "7 Sr Exec"}
for ax, c in zip(axes, COL):
    t = sen.xs(c, level="country").unstack("seniority").reindex(months).fillna(0)
    sh = t.div(t.sum(1), axis=0).rolling(3, min_periods=1).mean()
    ax.stackplot(range(len(months)), *[sh[k].values for k in sh.columns], labels=[labels[int(k)] for k in sh.columns],
                 colors=plt.cm.viridis(np.linspace(0, 1, len(sh.columns))))
    ax.set_title(f"{c}: seniority mix of computer-occupation postings (3-mo MA)", fontsize=10); xaxis(ax); ax.set_ylim(0, 1)
axes[1].legend(loc="center left", bbox_to_anchor=(1, .5), fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_seniority_mix.png"), dpi=150); plt.close(fig)

# ---- Fig 3: entry and early-career shares: computer occ. vs software vs all occupations, and ex-staffing
def share(df, levels):
    g = df.groupby(["month", "country"]).n_posts.sum()
    h = df[df.seniority.isin(levels)].groupby(["month", "country"]).n_posts.sum()
    return (100 * h / g).unstack("country").reindex(months)
non_staff = par[~par.parent_name.fillna("").str.contains(STAFFING)]
out = {}
fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=False)
for ax, (lev, name) in zip(axes, [([1], "Entry (level 1)"), ([1, 2], "Early career (levels 1+2)")]):
    for c in COL:
        for df, ls, lab in [(onet, "-", "computer occ."), (onet[onet.swe_onet.isin(NARROW)], "--", "software (narrow)"),
                            (non_staff, ":", "computer occ. ex-staffing"), (occ2, "-.", "all occupations")]:
            s = share(df, lev)[c]; out[(name, c, lab)] = s
            ax.plot(s.rolling(3, min_periods=1).mean().values, color=COL[c], ls=ls, lw=1.4 if ls == "-" else 1, label=f"{c}: {lab}")
    ax.set_title(f"{name} share of postings, % (3-mo MA)", fontsize=10); xaxis(ax)
axes[1].legend(fontsize=7, loc="center left", bbox_to_anchor=(1, .5))
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_entry_share.png"), dpi=150); plt.close(fig)

# ---- Fig 4: postings by seniority group, indexed to 2019 and 2022
grp = onet.assign(g=np.select([onet.seniority <= 2, onet.seniority == 3, onet.seniority == 4], ["1-2 early", "3 associate", "4 mgr/sr IC"], "5-7 director+"))
fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
for i, c in enumerate(COL):
    t = grp[grp.country == c].groupby(["month", "g"]).n_posts.sum().unstack("g").reindex(months)
    for j, yr in enumerate(["2019", "2022"]):
        ax = axes[i, j]
        for k in t.columns:
            ax.plot(index_to(t[k], yr).rolling(3, min_periods=1).mean().values, label=k)
        ax.axhline(100, color="grey", lw=.8); ax.set_title(f"{c}: computer-occ. postings by seniority, {yr} avg = 100", fontsize=10); xaxis(ax)
axes[0, 0].legend(fontsize=8); fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_seniority_index.png"), dpi=150); plt.close(fig)

# ---- summary numbers
def yavg(s, y): return s.loc[[m for m in months if m.startswith(y)]].mean()
rows = []
for c in COL:
    for y in ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
        rows.append(dict(country=c, year=y, comp_posts_per_month=yavg(comp[c], y), narrow_posts_per_month=yavg(narrow[c], y),
                         comp_share_of_all_pct=yavg(100 * comp[c] / allp[c], y),
                         entry_share_comp=yavg(out[("Entry (level 1)", c, "computer occ.")], y),
                         early_share_comp=yavg(out[("Early career (levels 1+2)", c, "computer occ.")], y),
                         early_share_narrow=yavg(out[("Early career (levels 1+2)", c, "software (narrow)")], y),
                         early_share_comp_exstaff=yavg(out[("Early career (levels 1+2)", c, "computer occ. ex-staffing")], y),
                         early_share_allocc=yavg(out[("Early career (levels 1+2)", c, "all occupations")], y)))
S = pd.DataFrame(rows)
S.to_csv(os.path.join(SUM, "yearly_summary.csv"), index=False)
pd.set_option("display.width", 250); print(S.round(1).to_string(index=False))
# top posters (concentration check)
top = par.groupby(["country", "parent_name"]).n_posts.sum().sort_values(ascending=False).groupby(level=0).head(10)
top.to_csv(os.path.join(SUM, "top_parents.csv")); print(top)
