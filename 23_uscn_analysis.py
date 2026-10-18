"""Exploration B: US-China comparison with the China data breaks made explicit.

Inputs (all git-ignored): data/occ_panel (09: month x country x O*NET x seniority x source group, all occupations),
data/sources (06: computer occupations, per-board flags), data/expreq (21: title keywords and required experience by source,
computer occupations, job_id sample), data/tags_src (20: stack tags by source, computer occupations, job_id sample).
Source groups: li_only (LinkedIn only), li_plus (LinkedIn + another source; occ_panel only), cn_board (Zhaopin/51job/Liepin, no
LinkedIn), other. Consistent-source windows: China = cn_board 2021-01..2025-08 (boards stop in 2025-09); US = all sources
and LinkedIn-only, 2021-01..2026-06.
Outputs: outputs/explore/uscn_*.png, outputs/explore/uscn_tables.md, data/explore/uscn_*.csv
Usage: uv run python 23_uscn_analysis.py
"""
import glob, os
import numpy as np, pandas as pd
import pyfixest as pf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data"); O = os.path.join(HERE, "outputs", "explore")
os.makedirs(O, exist_ok=True); os.makedirs(os.path.join(D, "explore"), exist_ok=True)
EXPO = pd.read_csv(os.path.join(D, "exposure", "exposure_soc6.csv")).set_index("soc6")
LOG = []
def log(s=""): print(s, flush=True); LOG.append(s)
def half(m): return m.str[:4] + "H" + np.where(m.str[5:7].astype(int) <= 6, "1", "2")
def rd(sub): return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(D, sub, "*.parquet")))], ignore_index=True)
CN_END = "2025-08"; US_END = "2026-06"
BREAKS = [("2021-07", "LinkedIn China ramps up"), ("2022-12", "51job seniority shift"), ("2023-05", "InCareer closure announced"),
          ("2023-08", "InCareer closes (9 Aug)"), ("2023-10", "Zhaopin/Liepin seniority shift"), ("2025-07", "China 'other' source surge"),
          ("2025-09", "CN boards stop")]

def coverage(op, src):
    log("## B1. Coverage by source (postings, thousands; all occupations, seniority 1-7)\n")
    op = op.copy(); op["half"] = half(op.month)
    t = (op.groupby(["half", "country", "src"]).n.sum().unstack(["country", "src"]) / 1e3).round(0)
    log(t.fillna(0).astype(int).to_markdown()); t.to_csv(os.path.join(D, "explore", "uscn_coverage.csv"))
    s = src[src.country == "China"].copy(); s["half"] = half(s.month)
    t2 = (s.groupby("half")[["n", "n_linkedin", "n_zhaopin", "n_51job", "n_liepin", "n_company_sites", "p_cn_board_only"]].sum() / 1e3).round(1)
    log("\nChina computer occupations (15-12xx), per-board flags (overlap allowed), thousands:\n\n" + t2.to_markdown())
    m = op.groupby(["month", "country", "src"]).n.sum().unstack(["country", "src"])
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2), sharey=True)
    for ax, c in zip(axs, ["China", "United States"]):
        for s_ in ["li_only", "li_plus", "cn_board", "other"]:
            if (c, s_) in m and m[(c, s_)].sum() > 1e5: ax.plot(pd.to_datetime(m.index), m[(c, s_)] / 1e3, label=s_)
        if c == "China":
            for b, lab in BREAKS: ax.axvline(pd.to_datetime(b), c="grey", lw=.6, ls=":")
        ax.set_yscale("log"); ax.set_title(f"{c}: postings by source group (thousands, log)"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(O, "uscn_1_coverage.png"), dpi=140); plt.close(fig)

def label_break(src, ex):
    log("\n## B2. Seniority-label breaks: Revelio early share (1-2) within each board vs title keywords\n")
    s = src.copy(); s["early"] = s.seniority <= 2
    rows = {}
    for c, flags in [("China", ["n_zhaopin", "n_51job", "n_liepin", "n_linkedin"]), ("United States", ["n_linkedin", "n_indeed", "n_company_sites"])]:
        x = s[s.country == c]
        for b in flags:
            y = x.groupby(["month", "early"])[b].sum().unstack(); rows[(c, b[2:])] = y[True] / y.sum(1)
    es = pd.DataFrame(rows)
    sel = ["2022-06", "2022-11", "2023-01", "2023-06", "2023-09", "2023-11", "2024-06", "2025-06"]
    log("Revelio early share (seniority 1-2 / 1-7), computer occupations, by board flag:\n\n" + es.loc[sel].round(2).to_markdown())
    e = ex.copy(); e["early"] = e.seniority <= 2
    k = e.groupby(["month", "country", "src", "kw"]).n.sum().unstack("kw").fillna(0)
    k = k.div(k.sum(1), axis=0); k["junior_kw"] = k.get("intern_grad", 0) + k.get("junior", 0)
    kk = k[["junior_kw", "senior_plus"]].unstack(["country", "src"])
    log("\nTitle-keyword shares by source (seniority-model-free): junior_kw = intern/graduate/campus/实习/校招/应届/junior/初级/助理; "
        "senior_plus = senior/lead/manager/高级/资深/专家/经理/总监/架构:\n")
    cols = [("junior_kw", "China", "cn_board"), ("senior_plus", "China", "cn_board"), ("junior_kw", "China", "li_only"),
            ("junior_kw", "United States", "li_only"), ("junior_kw", "United States", "other"), ("senior_plus", "United States", "li_only")]
    cols = [c for c in cols if c in kk.columns]
    log(kk.loc[[m for m in sel if m in kk.index], cols].round(3).to_markdown())
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
    for col in es.columns:
        if col[0] == "China": axs[0].plot(pd.to_datetime(es.index), es[col], label=f"Revelio 1-2 share, {col[1]}")
    for col in [("junior_kw", "China", "cn_board"), ("senior_plus", "China", "cn_board")]:
        if col in kk: axs[0].plot(pd.to_datetime(kk.index), kk[col].rolling(3, min_periods=1).mean(), ls="--", label=f"title kw {col[0]}, CN boards (3m MA)")
    axs[0].set_title("China computer occupations: label share jumps within each board, title keywords do not", fontsize=9)
    for col in es.columns:
        if col[0] == "United States": axs[1].plot(pd.to_datetime(es.index), es[col], label=f"Revelio 1-2 share, {col[1]}")
    for col in [("junior_kw", "United States", "li_only"), ("junior_kw", "United States", "other")]:
        if col in kk: axs[1].plot(pd.to_datetime(kk.index), kk[col].rolling(3, min_periods=1).mean(), ls="--", label=f"title kw junior, US {col[2]} (3m MA)")
    axs[1].set_title("US computer occupations", fontsize=9)
    for a in axs: a.set_xlim(pd.to_datetime("2021-01"), pd.to_datetime("2026-09")); a.legend(fontsize=6)
    for b, lab in BREAKS: axs[0].axvline(pd.to_datetime(b), c="grey", lw=.6, ls=":")
    fig.tight_layout(); fig.savefig(os.path.join(O, "uscn_2_label_break.png"), dpi=140); plt.close(fig)
    return k

def junior_measures(ex):
    log("\n## B3. Junior measures by consistent source, computer occupations, half-year\n")
    e = ex.copy(); e["half"] = half(e.month)
    e = e[((e.country == "China") & (e.month <= CN_END)) | ((e.country == "United States") & (e.month <= US_END))]
    e["kwj"] = e.kw.isin(["intern_grad", "junior"]) * e.n; e["kws"] = (e.kw == "senior_plus") * e.n
    e["has_y"] = e.yoe.notna() * e.n; e["y_le2"] = ((e.yoe <= 2) & e.yoe.notna()) * e.n; e["zero_n"] = e.zero.astype(bool) * e.n
    e["early_n"] = (e.seniority <= 2) * e.n
    g = e.groupby(["country", "src", "half"])[["n", "early_n", "kwj", "kws", "has_y", "y_le2", "zero_n"]].sum()
    r = pd.DataFrame({"n_sample": g.n, "Revelio 1-2 share": g.early_n / g.n, "title junior kw": g.kwj / g.n, "title senior kw": g.kws / g.n,
                      "share stating years": g.has_y / g.n, "req <= 2 yrs | stated": g.y_le2 / g.has_y, "no-exp/grad phrase": g.zero_n / g.n})
    keep = [("China", "cn_board"), ("China", "li_only"), ("United States", "li_only"), ("United States", "other")]
    r = r[[i[:2] in keep for i in r.index]]
    log(r.round(3).to_markdown()); r.to_csv(os.path.join(D, "explore", "uscn_junior_measures.csv"))
    return r

def zs(col="eloundou_beta_gpt4"):
    e = EXPO[col].dropna(); return (e - e.mean()) / e.std()

def exposure_trends(op):
    log("\n## B4. AI-exposed occupations: postings by exposure, US vs China (occupation x source x half-year)\n")
    op = op.copy(); op["soc6"] = op.onet_code.str[:7]; op["half"] = half(op.month)
    op = op[((op.country == "China") & (op.month <= CN_END)) | ((op.country == "United States") & (op.month <= US_END))]
    op = op[op.month >= "2021-01"]
    a = op.groupby(["country", "src", "soc6", "half"]).n.sum().reset_index()
    z = zs(); a = a[a.soc6.isin(z.index)]; a["E"] = a.soc6.map(z)
    cuts = z.quantile([1/3, 2/3]).values; a["terc"] = np.where(a.E <= cuts[0], "low", np.where(a.E <= cuts[1], "mid", "high"))
    # (i) share of postings in high-exposure tercile occupations
    sh = a.groupby(["country", "src", "half", "terc"]).n.sum().unstack("terc"); sh = sh.div(sh.sum(1), axis=0)["high"].unstack(["country", "src"])
    cols = [c for c in [("United States", "li_only"), ("United States", "li_plus"), ("United States", "other"), ("China", "cn_board"), ("China", "li_only")] if c in sh]
    log("Share of postings in top-tercile Eloundou-exposure occupations (all seniorities):\n\n" + sh[cols].round(3).to_markdown())
    # (ii) exposure gradient event study: log(1+n_ost) ~ E x half | occ x src + src x half, ref 2022H2, cluster occ
    halves = sorted(a.half.unique()); res = {}
    def grad(x, lab):
        x = x.copy(); pre = x[x.half <= "2022H2"].groupby(["soc6", "src"]).n.sum(); okp = pre[pre >= 200].index
        x = x.set_index(["soc6", "src"]).loc[lambda t: t.index.isin(okp)].reset_index()
        full = x[["soc6", "src", "E"]].drop_duplicates().merge(pd.DataFrame({"half": halves}), how="cross")
        x = full.merge(x[["soc6", "src", "half", "n"]], on=["soc6", "src", "half"], how="left").fillna({"n": 0})
        x = x[x.half <= x.half[x.n > 0].max()]
        x["ly"] = np.log1p(x.n); x["os"] = x.soc6 + "_" + x.src; x["sh"] = x.src + "_" + x.half; names = []
        for k in sorted(x.half.unique()):
            if k == "2022H2": continue
            nm = "k" + k; x[nm] = x.E * (x.half == k); names.append(nm)
        m = pf.feols("ly ~ " + " + ".join(names) + " | os + sh", data=x, vcov={"CRV1": "soc6"}); t = m.tidy().loc[names]
        res[lab] = pd.DataFrame({"half": [n[1:] for n in names], "b": t.Estimate.values, "se": t["Std. Error"].values})
        return x.soc6.nunique()
    specs = [("US all sources (src x half FE)", a[a.country == "United States"]), ("US LinkedIn-only", a[(a.country == "United States") & (a.src == "li_only")]),
             ("China CN boards only (consistent source)", a[(a.country == "China") & (a.src == "cn_board")]),
             ("China all sources (src x half FE)", a[a.country == "China"]),
             ("China LinkedIn-only (InCareer break)", a[(a.country == "China") & (a.src == "li_only")])]
    nocc = {lab: grad(x, lab) for lab, x in specs}
    log("\nExposure gradient of log postings (coef. on E z-score x half, ref 2022H2; occ x source FE + source x half FE; SE by occupation; "
        "occupations with >= 200 pre-period postings in that source):\n")
    show = ["2021H1", "2021H2", "2022H1", "2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2", "2026H1"]
    log("| Spec | occs | " + " | ".join(show) + " |"); log("|---|---|" + "---|" * len(show))
    for lab in res:
        e = res[lab].set_index("half")
        log(f"| {lab} | {nocc[lab]} | " + " | ".join(f"{e.loc[k,'b']:+.3f} ({e.loc[k,'se']:.3f})" if k in e.index else "" for k in show) + " |")
    pd.concat(res).to_csv(os.path.join(D, "explore", "uscn_exposure_gradient.csv"))
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for i, lab in enumerate(["US all sources (src x half FE)", "US LinkedIn-only", "China CN boards only (consistent source)", "China all sources (src x half FE)"]):
        e = res[lab].set_index("half").reindex(halves); e.loc["2022H2"] = [0, 0]; e = e.dropna()
        xs = np.array([halves.index(h) for h in e.index]) + (i - 1.5) * .1
        ax.errorbar(xs, e.b, yerr=1.96 * e.se, marker="o", ms=3.5, capsize=2, label=lab)
    ax.axhline(0, c="k", lw=.6); ax.axvline(halves.index("2022H2") + .5, c="grey", ls="--", lw=.8)
    ax.set_xticks(range(len(halves))); ax.set_xticklabels(halves, rotation=45)
    ax.set_ylabel("log postings per SD of exposure, ref 2022H2"); ax.legend(fontsize=7)
    ax.set_title("Exposure gradient of postings, US vs China (occupation level, no seniority labels)", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(O, "uscn_3_exposure_gradient.png"), dpi=140); plt.close(fig)

def stacks(tg):
    log("\n## B5. Tech stack (title tags), share of sampled computer-occupation postings, by consistent source\n")
    t = tg.copy(); t["half"] = half(t.month)
    t = t[((t.country == "China") & (t.month <= CN_END)) | ((t.country == "United States") & (t.month <= US_END))]
    tags = ["frontend", "backend", "fullstack", "mobile", "data_eng", "ml_ai", "devops_cloud", "embedded"]
    g = t.groupby(["country", "src", "half"])[["n", "n_desc", "llm_ai"] + tags].sum()
    r = g[tags].div(g.n, axis=0); r["desc available"] = g.n_desc / g.n; r["llm_ai | desc"] = g.llm_ai / g.n_desc.replace(0, np.nan)
    keep = [("China", "cn_board"), ("United States", "li_only"), ("United States", "other")]
    r = r[[i[:2] in keep for i in r.index]]
    log(r.round(3).to_markdown()); r.to_csv(os.path.join(D, "explore", "uscn_stacks.csv"))
    ge = t[t.sen_group == "early"].groupby(["country", "src", "half"])[["n"] + tags].sum()
    re_ = ge[tags].div(ge.n, axis=0); re_ = re_[[i[:2] in keep for i in re_.index]]
    log("\nSame, early-career (Revelio 1-2) postings only (China values affected by the label breaks of B2):\n\n" + re_.round(3).to_markdown())
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    for ax, k in zip(axs, keep):
        x = r.loc[k]
        for tg_ in ["frontend", "backend", "mobile", "ml_ai", "data_eng", "embedded"]: ax.plot(x.index, x[tg_], marker="o", ms=3, label=tg_)
        ax.set_title(f"{k[0]} - {k[1]}", fontsize=9); ax.tick_params(axis="x", rotation=45)
    axs[0].legend(fontsize=7); axs[0].set_ylabel("share of postings with title tag")
    fig.tight_layout(); fig.savefig(os.path.join(O, "uscn_4_stacks.png"), dpi=140); plt.close(fig)

def main():
    op = rd("occ_panel"); src = rd("sources")
    coverage(op, src)
    have_ex = len(glob.glob(os.path.join(D, "expreq", "*.parquet"))) >= 60
    if have_ex:
        ex = rd("expreq"); label_break(src, ex); junior_measures(ex)
    exposure_trends(op)
    if len(glob.glob(os.path.join(D, "tags_src", "*.parquet"))) >= 60: stacks(rd("tags_src"))
    with open(os.path.join(O, "uscn_tables.md"), "w") as f: f.write("# Exploration B tables (generated by 23_uscn_analysis.py)\n\n" + "\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
