"""Design A (docs/did_design.md): triple difference early vs experienced x occupation AI exposure x post-ChatGPT,
on Revelio COSMOS postings for ALL occupations (P1, data/occ_panel), main sample US LinkedIn-only.

Cell: SOC-2018 6-digit occupation o x seniority group s (early = Revelio 1-2, experienced = 3-4; 5-7 dropped) x quarter t.
Outcome: log(postings + 1).  FE: o x t, s x t, o x s.  SE clustered by occupation.
Treatment intensity: Eloundou et al. GPT-4 beta (z-score across occupations, unweighted) [main];
  Felten LM-AIOE, Felten AIOE; Felten image-generation AIOE as a less-relevant-technology contrast;
  Webb pct_ai is not public (see docs/exposure.md) -> replaced by a placebo-in-time test.
Events: ChatGPT 2022-11-30 -> post = 2023Q1+, reference quarter 2022Q4; agentic coding (Claude Code GA 2025-05-22) -> post2 = 2025Q3+.
Outputs: figures/designA_*.png, docs/designA_tables.md (pasted into docs/designA_results.md), stdout.
"""
import glob, os
import numpy as np, pandas as pd
import pyfixest as pf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, "figures")
LAST_FULL_Q = "2026Q2"          # 2026Q3 only has Jul-Sep partially (Sep may be incomplete) -> drop
REF = "2022Q4"; POST1 = "2023Q1"; POST2 = "2025Q3"
MIN_PRE = 50                    # min pre-period (2021Q1-2022Q3) postings in EACH seniority group of an occupation
SOFTWARE = ["15-1251", "15-1252", "15-1253", "15-1254"]

# ---------- data
def load_panel():
    d = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(HERE, "data", "occ_panel", "*.parquet"))))
    d = d[d.onet_code.notna() & d.seniority.between(1, 4)].copy()
    d["soc6"] = d.onet_code.str[:7]
    d["sg"] = np.where(d.seniority <= 2, "early", "exp")
    d["q"] = pd.PeriodIndex(d.month, freq="M").asfreq("Q").astype(str)
    d["n"] = d.n.astype(float); d["staff"] = d.staff.astype(bool)
    return d

EXPO = pd.read_csv(os.path.join(HERE, "data", "exposure", "exposure_soc6.csv")).set_index("soc6")

def cells(d, country, srcs, drop_staff=False, last_q=LAST_FULL_Q):
    x = d[(d.country == country) & d.src.isin(srcs) & (d.q <= last_q)]
    if drop_staff:
        x = x[~x.staff]
    g = x.groupby(["soc6", "sg", "q"]).n.sum()
    occs = g.index.get_level_values(0).unique(); qs = sorted(x.q.unique())
    full = pd.MultiIndex.from_product([occs, ["early", "exp"], qs], names=["soc6", "sg", "q"])
    g = g.reindex(full, fill_value=0).reset_index()
    pre = g[g.q < "2022Q4"].groupby(["soc6", "sg"]).n.sum().unstack()
    keep = pre[(pre.min(axis=1) >= MIN_PRE)].index
    g = g[g.soc6.isin(keep)].copy()
    g["ly"] = np.log1p(g.n); g["early"] = (g.sg == "early").astype(int)
    g["os"] = g.soc6 + "_" + g.sg
    g["post"] = (g.q >= POST1).astype(int); g["post2"] = (g.q >= POST2).astype(int)
    g["qoy"] = g.q.str[-1]
    g = g.merge(pre.sum(axis=1).rename("w_pre").reset_index(), on="soc6")
    return g

def add_exposure(g, col):
    e = EXPO[col].dropna()
    z = (e - e.mean()) / e.std()       # z across all scored occupations
    g = g[g.soc6.isin(z.index)].copy(); g["E"] = g.soc6.map(z)
    return g

def did(g, extra_fe="", weights=None, post2=True, trend=False):
    g = g.copy(); g["T1"] = g.early * g.E * g.post; g["T2"] = g.early * g.E * g.post2
    rhs = "T1 + T2" if post2 else "T1"
    if trend:   # differential linear trend Early x E x t, so T1/T2 are deviations from the (pre+post) linear trend
        qi = {q: i for i, q in enumerate(sorted(g.q.unique()))}; g["TR"] = g.early * g.E * g.q.map(qi); rhs += " + TR"
    m = pf.feols(f"ly ~ {rhs} | soc6^q + sg^q + os{extra_fe}", data=g, vcov={"CRV1": "soc6"}, weights=weights)
    t = m.tidy()
    return t, m

def event(g, ref=REF):
    g = g.copy(); qs = sorted(g.q.unique()); names = []
    for q in qs:
        if q == ref: continue
        nm = "k_" + q; g[nm] = g.early * g.E * (g.q == q); names.append(nm)
    m = pf.feols("ly ~ " + " + ".join(names) + " | soc6^q + sg^q + os", data=g, vcov={"CRV1": "soc6"})
    t = m.tidy().reset_index().rename(columns={"Coefficient": "term"})
    t["q"] = t.term.str[2:]
    leads = [n for n in names if n[2:] < ref]
    R = np.zeros((len(leads), len(names)))
    for i, n in enumerate(leads): R[i, names.index(n)] = 1
    w = m.wald_test(R=R)
    return t, w, leads

def fmt(t, term):
    r = t.loc[term]
    star = "***" if r["Pr(>|t|)"] < .01 else "**" if r["Pr(>|t|)"] < .05 else "*" if r["Pr(>|t|)"] < .1 else ""
    return f"{r['Estimate']:.3f}{star} ({r['Std. Error']:.3f})"

if __name__ == "__main__":
    d = load_panel()
    out = []                         # rows for the results table
    US_LI = cells(d, "United States", ["li_only"])
    print("US LinkedIn-only: occupations", US_LI.soc6.nunique(), "quarters", US_LI.q.nunique(), "cells", len(US_LI),
          "postings", int(US_LI.n.sum()))
    def row(label, g, **kw):
        t, m = did(g, **kw)
        out.append(dict(spec=label, post_chatgpt=fmt(t, "T1"), post_agentic=fmt(t, "T2") if "T2" in t.index else "",
                        n_occ=g.soc6.nunique(), n_obs=int(m._N)))
        print(label, out[-1])
    main = add_exposure(US_LI, "eloundou_beta_gpt4")
    row("Main: US LinkedIn-only, Eloundou beta (GPT-4), z", main)
    row("Eloundou beta (human raters)", add_exposure(US_LI, "eloundou_beta_human"))
    row("Felten LM-AIOE", add_exposure(US_LI, "felten_lm_aioe"))
    row("Felten AIOE (2021, pre-LLM abilities)", add_exposure(US_LI, "felten_aioe"))
    row("Felten image-generation AIOE (contrast)", add_exposure(US_LI, "felten_ig_aioe"))
    row("Excluding staffing/outsourcing parents", add_exposure(cells(d, "United States", ["li_only"], drop_staff=True), "eloundou_beta_gpt4"))
    row("+ occupation x seniority x quarter-of-year FE", main, extra_fe=" + os^qoy")
    row("Weighted by pre-period postings", main, weights="w_pre")
    row("+ differential linear trend (Early x E x t)", main, trend=True)
    row("Sample from 2022Q1 (after 2021 LinkedIn coverage ramp-up)", main[main.q >= "2022Q1"])
    row("Drop 2022Q4-2023Q1 (Jan-Feb 2023 seniority spike)", main[~main.q.isin(["2022Q4", "2023Q1"])])
    big = cells(d, "United States", ["li_only"]); pre = big[big.q < "2022Q4"].groupby(["soc6", "sg"]).n.sum().unstack().min(axis=1)
    row("Large occupations only (>=2,000 pre-period postings per seniority group)", add_exposure(big[big.soc6.isin(pre[pre >= 2000].index)], "eloundou_beta_gpt4"))
    row("All US sources (LinkedIn-only + LI-plus + other)", add_exposure(cells(d, "United States", ["li_only", "li_plus", "other"]), "eloundou_beta_gpt4"))
    # binary: top vs bottom quartile
    gb = main.copy(); qtl = gb.drop_duplicates("soc6").E.quantile([.25, .75])
    gb = gb[(gb.E <= qtl[.25]) | (gb.E >= qtl[.75])].copy(); gb["E"] = (gb.E >= qtl[.75]).astype(float)
    row("Binary: top vs bottom exposure quartile", gb)
    # software dummy (Westby-style): software developers vs all other occupations
    gs = main.copy(); gs["E"] = gs.soc6.isin(SOFTWARE).astype(float)
    row("Treatment = software developer occs (15-1251..54) vs rest", gs)
    # YoY outcome: 4-quarter log difference
    gy = main.sort_values(["os", "q"]).copy(); gy["ly"] = gy.groupby("os").ly.diff(4); gy = gy.dropna(subset=["ly"])
    row("Outcome = YoY log change (from 2022Q1)", gy)
    # placebo in time: pre-period only, fake post = 2022Q1+ (data 2021Q1-2022Q3)
    gp = main[main.q <= "2022Q3"].copy(); gp["post"] = (gp.q >= "2022Q1").astype(int)
    row("Placebo: fake event 2022Q1, sample 2021Q1-2022Q3", gp, post2=False)
    # early-share outcome
    sh = main.pivot_table(index=["soc6", "q", "E", "post", "post2"], columns="sg", values="n").reset_index()
    sh = sh[(sh.early + sh.exp) > 0]; sh["share"] = 100 * sh.early / (sh.early + sh.exp)
    sh["T1"] = sh.E * sh.post; sh["T2"] = sh.E * sh.post2
    ms = pf.feols("share ~ T1 + T2 | soc6 + q", data=sh, vcov={"CRV1": "soc6"}); ts = ms.tidy()
    out.append(dict(spec="Outcome = early share (pp), exposure x post, occ + quarter FE", post_chatgpt=fmt(ts, "T1"),
                    post_agentic=fmt(ts, "T2"), n_occ=sh.soc6.nunique(), n_obs=int(ms._N)))
    print(out[-1])
    # China (descriptive; source breaks)
    for lab, srcs, lq in [("China LinkedIn-only (descriptive)", ["li_only"], LAST_FULL_Q),
                          ("China Zhaopin/51job/Liepin (descriptive, to 2025Q3)", ["cn_board"], "2025Q3")]:
        gc = add_exposure(cells(d, "China", srcs, last_q=lq), "eloundou_beta_gpt4")
        if gc.soc6.nunique() > 20:
            row(lab, gc)
    T = pd.DataFrame(out); T.to_csv(os.path.join(HERE, "docs", "designA_table.csv"), index=False)  # git-ignored csv
    with open(os.path.join(HERE, "docs", "designA_tables.md"), "w") as f:
        f.write("| Specification | Early x Exposure x Post-ChatGPT (2023Q1+) | x Post-agentic (2025Q3+, additional) | occupations | obs |\n|---|---|---|---|---|\n")
        for r in out:
            f.write(f"| {r['spec']} | {r['post_chatgpt']} | {r['post_agentic']} | {r['n_occ']} | {r['n_obs']} |\n")

    # ---------- event studies
    ES = {}
    for lab, g in [("US LinkedIn-only, Eloundou beta", main), ("US LinkedIn-only, Felten LM-AIOE", add_exposure(US_LI, "felten_lm_aioe")),
                   ("US LinkedIn-only, ex staffing", add_exposure(cells(d, "United States", ["li_only"], drop_staff=True), "eloundou_beta_gpt4")),
                   ("US, software occs vs rest", gs)]:
        t, w, leads = event(g); ES[lab] = (t, w)
        print(f"EVENT {lab}: pre-trend Wald F={float(w['statistic']):.2f}, p={float(w['pvalue']):.3f}, {len(leads)} leads")
    for lab, srcs, lq in [("China LinkedIn-only", ["li_only"], LAST_FULL_Q), ("China CN boards (to 2025Q3)", ["cn_board"], "2025Q3")]:
        gc = add_exposure(cells(d, "China", srcs, last_q=lq), "eloundou_beta_gpt4")
        t, w, leads = event(gc); ES[lab] = (t, w)
        print(f"EVENT {lab}: pre-trend Wald F={float(w['statistic']):.2f}, p={float(w['pvalue']):.3f}")
    with open(os.path.join(HERE, "docs", "designA_tables.md"), "a") as f:
        f.write("\n\nEvent-study pre-trend tests (joint Wald on all leads 2021Q1-2022Q3, ref 2022Q4):\n\n| Event study | F | p |\n|---|---|---|\n")
        for lab, (t, w) in ES.items():
            f.write(f"| {lab} | {float(w['statistic']):.2f} | {float(w['pvalue']):.3f} |\n")
        f.write("\nEvent-study coefficients (main):\n\n| quarter | coef | se |\n|---|---|---|\n")
        t = ES["US LinkedIn-only, Eloundou beta"][0]
        for _, r in t.iterrows():
            f.write(f"| {r.q} | {r.Estimate:.3f} | {r['Std. Error']:.3f} |\n")
    pd.concat({k: v[0] for k, v in ES.items()}).to_csv(os.path.join(HERE, "docs", "designA_event.csv"))

    qx = lambda q: int(q[:4]) + (int(q[-1]) - 1) / 4
    def plot(keys, fname, title):
        fig, axes = plt.subplots(1, len(keys), figsize=(6.2 * len(keys), 4.4), squeeze=False)
        for ax, k in zip(axes[0], keys):
            t, w = ES[k]; x = np.array([qx(q) for q in t.q]); b = t.Estimate.values; se = t["Std. Error"].values
            x = np.append(x, qx(REF)); b = np.append(b, 0); se = np.append(se, 0); o = np.argsort(x)
            ax.fill_between(x[o], (b - 1.96 * se)[o], (b + 1.96 * se)[o], color="C0", alpha=.2)
            ax.plot(x[o], b[o], "o-", color="C0", ms=3.5); ax.axhline(0, color="k", lw=.8)
            for xv, lab, c in [(qx("2022Q4") + 2 / 12, "ChatGPT", "navy"), (qx("2025Q2") + 1.7 / 12, "Claude Code GA", "darkorange"),
                               (qx("2022Q2") + 2.7 / 12, "Copilot GA", "darkorange")]:
                ax.axvline(xv, ls="--", color=c, lw=1); ax.text(xv, ax.get_ylim()[1], " " + lab, fontsize=7, color=c, va="top")
            ax.set_title(f"{k}\npre-trend F={float(w['statistic']):.2f}, p={float(w['pvalue']):.3f}", fontsize=9)
            ax.set_xlabel("quarter (ref = 2022Q4)")
        axes[0][0].set_ylabel("Early x Exposure(z) x quarter: log postings")
        fig.suptitle(title, fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=140); plt.close(fig)
    plot(["US LinkedIn-only, Eloundou beta", "US LinkedIn-only, Felten LM-AIOE", "US LinkedIn-only, ex staffing"],
         "designA_1_event_us.png", "Design A event study, US LinkedIn-only postings. 95% CI, SE clustered by occupation. FE: occ x q, seniority x q, occ x seniority")
    plot(["US, software occs vs rest", "China LinkedIn-only", "China CN boards (to 2025Q3)"],
         "designA_2_event_software_china.png", "Design A event study: software-occupation dummy (US) and China (descriptive: source breaks 2023-01, 2023-08, 2023-10, 2025-10)")

    # raw descriptive: early/exp log ratio by exposure tercile
    m0 = main.copy(); terc = m0.drop_duplicates("soc6").set_index("soc6").E.rank(pct=True)
    m0["tercile"] = pd.cut(m0.soc6.map(terc), [0, 1 / 3, 2 / 3, 1], labels=["low", "mid", "high"])
    r = m0.groupby(["tercile", "q", "sg"], observed=True).n.sum().unstack()
    r = np.log(r.early / r.exp).unstack(0); r = r - r.loc[REF]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for c in r.columns:
        ax.plot([qx(q) for q in r.index], r[c], "o-", ms=3, label=f"{c} exposure tercile")
    ax.axhline(0, color="k", lw=.7); ax.axvline(qx("2022Q4") + 2 / 12, ls="--", color="navy")
    ax.set_title("US LinkedIn-only: log(early / experienced postings), normalised to 2022Q4, by Eloundou-beta tercile", fontsize=9)
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(FIG, "designA_3_raw_terciles.png"), dpi=140); plt.close(fig)
    print("done")
