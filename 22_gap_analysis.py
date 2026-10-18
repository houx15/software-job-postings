"""Exploration A: is the posting-hire gap real within firm x occupation cells?

Cell: firm f (ultimate_parent_rcid, P2 US firm list) x SOC-2018 6-digit occupation o x half-year t, 2021H1..2025H2.
  Postings P (19_gap_postings_half.py, from postings_cosmos via 12): P_early = Revelio seniority 1-2, P_exp = 3-4,
           P_all = 1-4; P_li = LinkedIn-only source; all sources otherwise.
  Hires    H (18_firm_occ_hires_pull.py, individual_positions = new positions on LinkedIn-style profiles, by startdate):
           H_early = seniority 1-2; H_first = position_number 1 (first recorded position: labour-market entrant, a junior
           definition that does not use the seniority model); H_all = 1-4. Unweighted counts (Revelio sampling weights
           vary by occupation x location and are absorbed by the pair FE).
  Outcomes log(1+x); gap = log(1+H) - log(1+P), i.e. a log fill ratio (hires per posting).
Sample: pairs with >= MIN_P pre-period (2021H1-2022H2) postings (seniority 1-4) and >= MIN_H pre-period hires; balanced with zeros.
Exposure E: Eloundou GPT-4 beta z-score (Felten LM-AIOE and Eloundou human beta as robustness).
Spec:   y = sum_k b_k E x 1[t=k] + pair FE + firm x half FE, ref 2022H2, SE clustered by occupation.
        Pooled: E x Post, Post = 2023H1..2025H1 (2025H2 dropped from pooled: profile-update lag).
Outputs: data/explore/gap_*.csv (git-ignored), outputs/explore/gap_*.png, outputs/explore/gap_tables.md
Usage: uv run python 22_gap_analysis.py
"""
import os
import numpy as np, pandas as pd
import pyfixest as pf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data", "explore"); O = os.path.join(HERE, "outputs", "explore")
os.makedirs(O, exist_ok=True)
HALVES = [f"{y}H{h}" for y in range(2021, 2026) for h in (1, 2)]; REF = "2022H2"; PRE = HALVES[:4]
POST = ["2023H1", "2023H2", "2024H1", "2024H2", "2025H1"]
MIN_P = int(os.environ.get("MIN_P", 20)); MIN_H = int(os.environ.get("MIN_H", 5))
EXPO = pd.read_csv(os.path.join(HERE, "data", "exposure", "exposure_soc6.csv")).set_index("soc6")
STAFF = set(pd.read_csv(os.path.join(HERE, "data", "staffing_rcids.csv")).rcid.astype("int64"))
LOG = []
def log(s): print(s, flush=True); LOG.append(s)

def build():
    p = pd.read_parquet(os.path.join(D, "postings_fo_half.parquet"))
    p = p[p.half.isin(HALVES)]
    h = pd.read_parquet(os.path.join(HERE, "data", "hires_fo", "hires_fo.parquet"), columns=["half", "rcid", "soc6", "sg", "pn", "n"])
    h = h[h.half.isin(HALVES)]
    # select pairs on pre-period totals first (keeps memory low), then reshape
    pp = p[p.half.isin(PRE)].groupby(["rcid", "soc6"], observed=True).n.sum()
    hp = h[h.half.isin(PRE)].groupby(["rcid", "soc6"], observed=True).n.sum()
    pre = pd.concat({"P": pp, "H": hp}, axis=1).fillna(0)
    pre = pre[(pre.P >= MIN_P) & (pre.H >= MIN_H)].reset_index()
    pre["soc6"] = pre.soc6.astype(str); pairs = pre[pre.soc6.isin(EXPO.index)][["rcid", "soc6"]]
    key = pd.MultiIndex.from_frame(pairs)
    def keep(x):
        x = x.copy(); x["soc6"] = x.soc6.astype(str); x["half"] = x.half.astype(str)
        return x[pd.MultiIndex.from_frame(x[["rcid", "soc6"]]).isin(key)]
    p = keep(p); h = keep(h)
    p["c"] = "P_" + p.sg.astype(str) + np.where(p.src.astype(str) == "li_only", "_li", "_nl")
    h["c"] = "H_" + h.sg.astype(str) + "_" + h.pn.astype(str)
    P = p.groupby(["rcid", "soc6", "half", "c"]).n.sum().unstack("c", fill_value=0)
    H = h.groupby(["rcid", "soc6", "half", "c"]).n.sum().unstack("c", fill_value=0)
    x = P.join(H, how="outer").fillna(0)
    grid = pd.MultiIndex.from_frame(pairs.merge(pd.DataFrame({"half": HALVES}), how="cross"))
    x = x.reindex(grid, fill_value=0).reset_index()
    g = lambda pre: x.filter(like=pre).sum(axis=1)
    c0 = lambda c: x[c] if c in x else 0
    out = pd.DataFrame({"rcid": x.rcid, "soc6": x.soc6, "half": x.half,
        "P_early": c0("P_early_li") + c0("P_early_nl"), "P_exp": c0("P_exp_li") + c0("P_exp_nl"),
        "P_early_li": c0("P_early_li"), "P_all_li": c0("P_early_li") + c0("P_exp_li"),
        "H_early": g("H_early_"), "H_exp": g("H_exp_"), "H_first": g("_first"), "H_first_early": c0("H_early_first")})
    out["P_all"] = out.P_early + out.P_exp; out["H_all"] = out.H_early + out.H_exp
    return out

def zs(col):
    e = EXPO[col].dropna(); return (e - e.mean()) / e.std()

def prep(d, expo="eloundou_beta_gpt4"):
    d = d.copy(); d["E"] = d.soc6.map(zs(expo)); d = d[d.E.notna()]
    d["pair"] = d.rcid.astype(str) + "_" + d.soc6; d["fh"] = d.rcid.astype(str) + "_" + d.half
    d["post"] = d.half.isin(POST).astype(int)
    for k in ["P_early", "P_exp", "P_all", "P_early_li", "P_all_li", "H_early", "H_exp", "H_all", "H_first", "H_first_early"]:
        d["l_" + k] = np.log1p(d[k])
    d["gap_early"] = d.l_H_early - d.l_P_early            # Revelio seniority on both sides
    d["gap_first"] = d.l_H_first - d.l_P_all              # seniority-model-free: entrants per posting
    d["gap_early_li"] = d.l_H_early - d.l_P_early_li      # LinkedIn-only postings (same platform as profiles)
    d["gap_first_li"] = d.l_H_first - d.l_P_all_li
    d["gap_exp"] = d.l_H_exp - d.l_P_exp
    d["dd_early_exp"] = d.gap_early - d.gap_exp           # junior gap minus experienced gap, same cell
    return d

def star(p): return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
def pooled(d, y, fe="pair + fh"):
    h = d[d.half != "2025H2"].copy(); h["EP"] = h.E * h.post
    m = pf.feols(f"{y} ~ EP | {fe}", data=h, vcov={"CRV1": "soc6"}); t = m.tidy().loc["EP"]
    return t["Estimate"], t["Std. Error"], t["Pr(>|t|)"]

def event(d, y, fe="pair + fh"):
    h = d[[y, "pair", "fh", "soc6", "rcid", "half"]].copy(); names = []
    for k in HALVES:
        if k == REF: continue
        nm = "k" + k; h[nm] = d.E.to_numpy() * (d.half == k).to_numpy(); names.append(nm)
    m = pf.feols(f"{y} ~ " + " + ".join(names) + f" | {fe}", data=h, vcov={"CRV1": "soc6"})
    t = m.tidy().loc[names]; leads = [n for n in names if n[1:] < REF]
    R = np.zeros((len(leads), len(names)))
    for i, n in enumerate(leads): R[i, names.index(n)] = 1
    w = m.wald_test(R=R)
    return pd.DataFrame({"half": [n[1:] for n in names], "b": t["Estimate"].values, "se": t["Std. Error"].values}), float(w["statistic"]), float(w["pvalue"])

OUTCOMES = [("l_H_early", "Hires, seniority 1-2"), ("l_P_early", "Postings, seniority 1-2"), ("gap_early", "Gap: log H_early - log P_early"),
            ("l_H_first", "Hires, first position (entrants)"), ("l_P_all", "Postings, seniority 1-4"), ("gap_first", "Gap: log H_first - log P_all"),
            ("l_P_early_li", "Postings 1-2, LinkedIn-only"), ("gap_early_li", "Gap vs LinkedIn-only postings 1-2"),
            ("gap_first_li", "Gap entrants vs LinkedIn-only postings 1-4"),
            ("gap_exp", "Gap experienced: log H_exp - log P_exp"), ("dd_early_exp", "Junior gap - experienced gap")]

def table(d, lab, outcomes=OUTCOMES, fe="pair + fh", ev=True):
    log(f"\n### {lab}\n\nSample: {d.rcid.nunique():,} firms, {d.soc6.nunique()} occupations, {d.pair.nunique():,} firm x occupation pairs, "
        f"{len(d):,} cells; postings {int(d.P_all.sum()):,}, hires {int(d.H_all.sum()):,}, entrant hires {int(d.H_first.sum()):,}. FE: {fe}.\n")
    log("| Outcome | E x Post (2023H1-2025H1) | pre-trend Wald chi2 (3 leads) | p | 2021H1 | 2022H1 | 2023H2 | 2024H2 | 2025H1 | 2025H2 (lag) |")
    log("|---|---|---|---|---|---|---|---|---|---|")
    evs = {}
    for y, nm in outcomes:
        b, se, p = pooled(d, y, fe)
        if ev:
            e, w, wp = event(d, y, fe); evs[y] = e; ee = e.set_index("half")
            cells = " | ".join(f"{ee.loc[k,'b']:+.3f} ({ee.loc[k,'se']:.3f})" for k in ["2021H1", "2022H1", "2023H2", "2024H2", "2025H1", "2025H2"])
            log(f"| {nm} | {b:+.3f}{star(p)} ({se:.3f}) | {w:.1f} | {wp:.3f} | {cells} |")
        else:
            log(f"| {nm} | {b:+.3f}{star(p)} ({se:.3f}) | | | | | | | | |")
    return evs

def fig(evs, keys, fn, title):
    fig, ax = plt.subplots(figsize=(8, 4.5)); xs = np.arange(len(HALVES))
    for i, (y, nm) in enumerate(keys):
        e = evs[y].set_index("half").reindex(HALVES); e.loc[REF] = [0, 0]
        off = (i - (len(keys) - 1) / 2) * 0.12
        ax.errorbar(xs + off, e.b, yerr=1.96 * e.se, marker="o", ms=4, capsize=2, label=nm)
    ax.axhline(0, c="k", lw=.6); ax.axvline(HALVES.index("2022H2") + .5, c="grey", ls="--", lw=.8)
    ax.axvspan(HALVES.index("2025H2") - .5, HALVES.index("2025H2") + .5, color="grey", alpha=.15)
    ax.set_xticks(xs); ax.set_xticklabels(HALVES, rotation=45); ax.set_ylabel("coef. on E (per SD) x half, ref 2022H2")
    ax.set_title(title, fontsize=10); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(O, fn), dpi=140); plt.close(fig)

def main():
    raw = build(); raw.to_parquet(os.path.join(D, "gap_panel.parquet"), index=False)
    d = prep(raw)
    log("# Exploration A tables (generated by 22_gap_analysis.py)")
    tot = d.groupby("half")[["P_early", "P_all", "H_early", "H_first", "H_all"]].sum()
    log("\nTotals in the estimation sample by half-year (counts):\n\n" + tot.astype(int).to_markdown())
    evs = table(d, "Main: Eloundou GPT-4 beta, pair FE + firm x half FE")
    pd.concat({k: v for k, v in evs.items()}).to_csv(os.path.join(D, "gap_event_main.csv"))
    fig(evs, [("l_H_early", "hires 1-2"), ("l_P_early", "postings 1-2"), ("gap_early", "gap (fill ratio) 1-2")],
        "gap_1_event_seniority.png", "Within firm x occupation: junior hires, junior postings, and their log ratio (Eloundou beta)")
    fig(evs, [("l_H_first", "entrant hires"), ("l_P_all", "postings 1-4"), ("gap_first", "gap entrants / postings")],
        "gap_2_event_entrants.png", "Seniority-model-free version: first-position hires vs all postings")
    short = [o for o in OUTCOMES if o[0] in ("l_H_early", "l_P_early", "gap_early", "l_H_first", "gap_first")]
    table(d, "No firm x half FE (pair FE + half FE)", short, fe="pair + half", ev=False)
    for col, lab in [("felten_lm_aioe", "Felten LM-AIOE"), ("felten_aioe", "Felten AIOE (pre-LLM)"), ("eloundou_beta_human", "Eloundou beta, human raters")]:
        table(prep(raw, col), f"Exposure = {lab}", short)
    ns = d[~d.soc6.str.startswith("15-12")]
    table(ns, "Excluding computer occupations (SOC 15-12xx): Section 174 / tech-cycle check", short)
    sw = d[d.soc6.str.startswith("15-")]
    log(f"\n(Computer & math occupations alone have {sw.soc6.nunique()} codes, too few for an exposure gradient; not estimated.)")
    table(d[~d.rcid.isin(STAFF)], "Excluding staffing parents", short, ev=False)
    big = d.groupby("pair").P_all.transform("sum") >= 100
    table(d[big], "Pairs with >= 100 postings over 2021H1-2025H2", short, ev=False)
    with open(os.path.join(O, "gap_tables.md"), "w") as f: f.write("\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
