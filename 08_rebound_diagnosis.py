"""Why does the early-career share (seniority 1-2) of computer-occupation postings dip and rebound (e.g. 2023)?
Decomposes the quarterly share into numerator/denominator, source composition (06), large posters / staffing (01 parent
gset), a title-keyword check of the seniority model (07), and seasonality (month-of-year, YoY, seasonally adjusted).
Inputs: data/agg (01), data/sources (06), data/titlekw (07).  Outputs: figures/rebound_*.png, docs/rebound_*.csv (git-ignored).
Descriptive only.
"""
import glob, os, re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, "figures"); DOC = os.path.join(HERE, "docs")
LAST_FULL, FIRST = "2026-08", "2019-01"
C = ["United States", "China"]
STAFFING = re.compile(r"staffing|lynx|robert half|allegis|insight global|teksystems|randstad|adecco|manpower|kforce|"
                      r"everforth|recruit|apex systems|kelly services|hays|michael page|cybercoders|dice|"
                      r"chinasoft|farben|法本|中软|wicresoft|archermind|fesco|人力|外包|northking|isoftstone|hirain", re.I)

def load(sub):
    d = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(HERE, "data", sub, "*.parquet"))))
    d = d[(d.month >= FIRST) & (d.month <= LAST_FULL)].copy()
    d["q"] = pd.PeriodIndex(d.month, freq="M").asfreq("Q").astype(str)
    return d

agg, src, tk = load("agg"), load("sources"), load("titlekw")
onet, par = agg[agg.gset == "onet"], agg[agg.gset == "parent"]
early = lambda df: df.seniority <= 2
qx = lambda q: int(q[:4]) + (int(q[-1]) - 0.5) / 4

# ---- A. numerator / denominator by quarter
A = onet.assign(num=np.where(early(onet), onet.n_posts, 0), s1=np.where(onet.seniority == 1, onet.n_posts, 0),
                s3=np.where(onet.seniority == 3, onet.n_posts, 0), s4p=np.where(onet.seniority >= 4, onet.n_posts, 0)
                ).groupby(["country", "q"])[["n_posts", "num", "s1", "s3", "s4p"]].sum().rename(columns={"n_posts": "den"})
A["share"] = 100 * A.num / A.den

# ---- B. source composition: mutually exclusive buckets
src["p_other"] = src.n - src[[c for c in src if c.startswith("p_")]].sum(axis=1)
BUCK = {"p_linkedin_only": "LinkedIn only", "p_cn_board_only": "Zhaopin/51job/Liepin (no LinkedIn)",
        "p_indeed_no_li": "Indeed (no LinkedIn)", "p_company_site_only": "company site only", "p_other": "other / multi-source"}
long = src.melt(id_vars=["month", "q", "country", "seniority"], value_vars=list(BUCK), var_name="b", value_name="k")
long["e"] = np.where(long.seniority <= 2, long.k, 0)
B = long.groupby(["country", "q", "b"])[["k", "e"]].sum()
B["share"] = 100 * B.e / B.k
B["w"] = B.k / B.groupby(level=[0, 1]).k.transform("sum")

def shift_share(c, q0, q1):
    x0, x1 = B.loc[(c, q0)], B.loc[(c, q1)]
    s0, s1, w0, w1 = x0.share.fillna(0), x1.share.fillna(0), x0.w, x1.w
    return dict(country=c, q0=q0, q1=q1, share0=(w0 * s0).sum(), share1=(w1 * s1).sum(),
                between=((w1 - w0) * (s0 + s1) / 2).sum(), within=(((w0 + w1) / 2) * (s1 - s0)).sum())

# ---- C. excluding top posters / staffing (parent gset = postings with a parent company)
par = par.assign(name=par.parent_name.fillna(""))
tot = par.groupby(["country", "name"]).n_posts.sum()
top = {c: set(tot.loc[c].drop("", errors="ignore").sort_values(ascending=False).head(20).index) for c in C}  # named parents only
def share_of(df):
    g = df.assign(e=np.where(early(df), df.n_posts, 0)).groupby(["country", "q"])[["n_posts", "e"]].sum()
    return 100 * g.e / g.n_posts
Cser = pd.DataFrame({"with parent id": share_of(par),
                     "ex top-20 posters": share_of(par[[n not in top[c] for c, n in zip(par.country, par.name)]]),
                     "ex staffing/outsourcing": share_of(par[~par.name.str.contains(STAFFING)])})
topq = par[[n in top[c] for c, n in zip(par.country, par.name)]].groupby(["country", "q"]).n_posts.sum()
Cser["top-20 % of postings"] = 100 * topq / par.groupby(["country", "q"]).n_posts.sum()
Cser["no parent id %"] = 100 * par[par.name == ""].groupby(["country", "q"]).n_posts.sum() / par.groupby(["country", "q"]).n_posts.sum()
Cser["ex no-parent-id"] = share_of(par[par.name != ""])

# ---- D. seniority model vs title keywords (sampled)
tk["early_model"] = tk.seniority <= 2
D = tk.assign(kw_early=tk.kw.isin(["intern_grad", "junior"]) * tk.n, kw_senior=(tk.kw == "senior_plus") * tk.n,
              model_early=tk.early_model * tk.n, model_early_senior_kw=(tk.early_model & (tk.kw == "senior_plus")) * tk.n
              ).groupby(["country", "q"])[["n", "kw_early", "kw_senior", "model_early", "model_early_senior_kw"]].sum()
D["model early share (sample)"] = 100 * D.model_early / D.n
D["title intern/junior share"] = 100 * D.kw_early / D.n
D["title senior+ share"] = 100 * D.kw_senior / D.n
D["% of model-early with senior title"] = 100 * D.model_early_senior_kw / D.model_early

# ---- E. seasonality (monthly)
M = onet.assign(e=np.where(early(onet), onet.n_posts, 0)).groupby(["country", "month"])[["n_posts", "e"]].sum()
M = M.astype(float); M["share"] = 100 * M.e / M.n_posts
E = {}
for c in C:
    m = M.loc[c].copy(); m.index = pd.PeriodIndex(m.index, freq="M"); m = m[m.index >= pd.Period("2021-01", "M")]
    trend = m.share.rolling(13, center=True).mean()            # 2x12-ish centered MA
    m["dev"] = m.share - trend
    moy = m.groupby(m.index.month).dev.mean()
    m["sa"] = m.share - m.index.month.map(moy).values
    m["yoy"] = m.share - m.share.shift(12)
    m["num_yoy"] = 100 * (m.e / m.e.shift(12) - 1); m["den_yoy"] = 100 * (m.n_posts / m.n_posts.shift(12) - 1)
    E[c] = (m, moy)

# ---- outputs
A.round(2).to_csv(os.path.join(DOC, "rebound_quarterly.csv"))
B.round(3).to_csv(os.path.join(DOC, "rebound_by_source.csv"))
Cser.round(2).to_csv(os.path.join(DOC, "rebound_ex_posters.csv"))
D.round(2).to_csv(os.path.join(DOC, "rebound_titlekw.csv"))
pd.DataFrame({c: E[c][1] for c in C}).round(2).to_csv(os.path.join(DOC, "rebound_month_of_year.csv"))
SS = pd.DataFrame([shift_share(c, a, b) for c in C for a, b in [("2023Q1", "2023Q4"), ("2023Q1", "2024Q1"), ("2022Q2", "2023Q1"),
                                                                  ("2024Q2", "2024Q4"), ("2025Q3", "2026Q2")]])
SS.round(2).to_csv(os.path.join(DOC, "rebound_shift_share.csv"), index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
sl = lambda df: df.loc[(slice(None), slice("2021Q1", "2026Q3")), :]
print("A. numerator/denominator (k)\n", (sl(A)[["den", "num", "s1", "s3", "s4p"]] / 1e3).round(0).join(sl(A).share.round(1)).to_string())
print("\nB. early share by source bucket\n", B.share.unstack("b").rename(columns=BUCK).loc[(slice(None), slice("2021Q1", "2026Q3")), :].round(1).to_string())
print("\nB. source mix (% of postings)\n", (100 * B.w).unstack("b").rename(columns=BUCK).loc[(slice(None), slice("2021Q1", "2026Q3")), :].round(1).to_string())
print("\nshift-share\n", SS.round(2).to_string())
print("\nC.\n", sl(Cser).round(1).to_string())
print("\nD.\n", sl(D).iloc[:, -4:].round(1).to_string())
for c in C:
    print("\nE.", c, "month-of-year deviation (pp):", E[c][1].round(2).to_dict())
    print(E[c][0].loc["2022-07":"2024-06", ["share", "sa", "yoy", "num_yoy", "den_yoy"]].round(1).to_string())

# ---- Figure 1: decomposition (rows = country)
fig, ax = plt.subplots(2, 3, figsize=(17, 9))
for i, c in enumerate(C):
    a = A.loc[c]; a = a[a.index >= "2021Q1"]; x = [qx(q) for q in a.index]
    ax[i, 0].plot(x, a.den / 1e3, "k-o", ms=3, label="all (denominator)")
    ax[i, 0].plot(x, a.num / 1e3, "C0-o", ms=3, label="seniority 1-2 (numerator)")
    ax[i, 0].plot(x, a.s3 / 1e3, "C1--", label="seniority 3"); ax[i, 0].plot(x, a.s4p / 1e3, "C2--", label="seniority 4+")
    ax2 = ax[i, 0].twinx(); ax2.plot(x, a.share, color="C3", lw=2.2, label="early share (rhs)"); ax2.set_ylabel("%", color="C3")
    ax[i, 0].set_title(f"{c}: counts (thousand postings / quarter)", fontsize=10); ax[i, 0].legend(fontsize=7, loc="upper right")
    b = B.share.unstack("b").loc[c]; w = B.w.unstack("b").loc[c]; b = b[b.index >= "2021Q1"]
    for k in ["p_linkedin_only", "p_cn_board_only", "p_indeed_no_li", "p_other"]:
        ok = (w.loc[b.index, k] > 0.03).values
        ax[i, 1].plot(np.array([qx(q) for q in b.index])[ok], b[k].values[ok], "-o", ms=3, label=BUCK[k])
    cs = Cser.loc[c]; cs = cs[cs.index >= "2021Q1"]
    ax[i, 1].plot([qx(q) for q in cs.index], cs["ex top-20 posters"], "k:", lw=2, label="ex top-20 posters")
    ax[i, 1].plot([qx(q) for q in cs.index], cs["ex staffing/outsourcing"], "k--", lw=1.2, label="ex staffing/outsourcing")
    d = D.loc[c]; d = d[d.index >= "2021Q1"]
    ax[i, 1].plot([qx(q) for q in d.index], d["title intern/junior share"] * 4, color="grey", lw=1, label="title intern/junior share x4 (sample)")
    ax[i, 1].set_title(f"{c}: early share by source / excluding big posters (%)", fontsize=10); ax[i, 1].legend(fontsize=6.5)
    m, moy = E[c]
    ax[i, 2].bar(moy.index, moy.values, color=["C3" if v < 0 else "C0" for v in moy.values])
    ax[i, 2].set_xticks(range(1, 13)); ax[i, 2].axhline(0, color="k", lw=.8)
    ax[i, 2].set_title(f"{c}: month-of-year deviation from 13-mo centered MA (pp), 2021-2026", fontsize=10)
fig.suptitle("Early-career share decomposition, computer occupations (Revelio COSMOS). Descriptive.", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "rebound_1_decomposition.png"), dpi=140); plt.close(fig)

# ---- Figure 2: monthly raw vs seasonally adjusted vs YoY
fig, ax = plt.subplots(1, 2, figsize=(15, 4.8))
for i, c in enumerate(C):
    m = E[c][0]; x = m.index.year + (m.index.month - .5) / 12
    ax[i].plot(x, m.share, color="lightgrey", lw=1.2, label="monthly share (raw)")
    ax[i].plot(x, m.sa, color="C0", lw=1.6, label="seasonally adjusted (month effects removed)")
    ax[i].plot(x, m.sa.rolling(3, center=True).mean(), color="C0", lw=2.6, alpha=.5, label="SA, 3-mo MA")
    a2 = ax[i].twinx(); a2.bar(x, m.yoy.fillna(0), width=1 / 13, color=["C3" if v < 0 else "C2" for v in m.yoy.fillna(0)], alpha=.35)
    a2.set_ylabel("YoY change, pp (bars)"); a2.axhline(0, color="k", lw=.5)
    ax[i].set_title(f"{c}: early-career share, raw vs SA; bars = YoY change", fontsize=10); ax[i].legend(fontsize=7, loc="lower left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "rebound_2_seasonal.png"), dpi=140); plt.close(fig)
print("figures written")
