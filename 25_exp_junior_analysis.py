"""Does AI exposure hit juniors specifically? Hires-only design with experience-based junior definitions and external hires.
Input: data/hires_exp/hires_exp.parquet (24_hires_exp_pull.py; 20% user sample, every position of a sampled user).
Cell: firm f (ultimate parent, P2 US list) x SOC6 occupation o x half-year t x group g (junior J / experienced X), 2019H1..2025H2.
Junior definitions (g):
  xf   : J = < 3 years since the user's first recorded position start; X = >= 3 years
  xg   : J = < 3 years since the last dated education end (end <= start + 6 months); X = >= 3; users without dated education dropped
  first: J = first recorded position (position_number 1); X = all other hires
  sen  : J = Revelio seniority 1-2; X = 3-4 (comparison with the earlier design; 5-7 dropped)
Hire types: main = external hires only = 'first' + 'ext' (previous position at a different known ultimate parent);
  internal moves ('int', previous position at the same parent) dropped; 'unk' (previous parent missing) dropped (robustness adds it).
Sample: pairs with >= MIN_PAIR sampled external hires in 2019H1-2022H2; balanced with zeros. Outcome log(1+n).
Specs (E = exposure z-score, ref 2022H2, SE clustered by occupation):
  level  : y_g ~ sum_k E x 1[t=k] | pair + firm x half                      (each group separately)
  triple : y ~ sum_k E x J x 1[t=k] | pair^g + firm^half^g + pair^half       (pair^half absorbs every firm x occupation x period
           shock common to juniors and experienced, incl. E x t and firm-level shocks; firm^half^g absorbs firm-wide junior shocks)
  pooled : E x J x Post, Post = 2023H1..2025H1 (2025H2 shown in event studies only: profile lag).
Lag checks: users whose profile was updated in 2026 only; ending in 2024H2; totals by half x update vintage.
HonestDiD (Rambachan-Roth) on the main triple event study via tools/honest_bounds.py in ~/.venvs/honestdid.
Outputs: outputs/explore/expj_*.png, outputs/explore/expj_tables.md, data/explore/expj_* (git-ignored).
Usage: uv run python 25_exp_junior_analysis.py
"""
import os, subprocess
import numpy as np, pandas as pd
import pyfixest as pf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data", "explore"); O = os.path.join(HERE, "outputs", "explore")
os.makedirs(D, exist_ok=True); os.makedirs(O, exist_ok=True)
HD_PY = os.path.expanduser("~/.venvs/honestdid/bin/python")
HALVES = [f"{y}H{h}" for y in range(2019, 2026) for h in (1, 2)]; REF = "2022H2"
PRE = [h for h in HALVES if h <= REF]; POST = ["2023H1", "2023H2", "2024H1", "2024H2", "2025H1"]
MIN_PAIR = int(os.environ.get("MIN_PAIR", 10))
EXPO = pd.read_csv(os.path.join(HERE, "data", "exposure", "exposure_soc6.csv")).set_index("soc6")
LOG = []
def log(s=""): print(s, flush=True); LOG.append(s)
def star(p): return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
def zs(col):
    e = EXPO[col].dropna(); return (e - e.mean()) / e.std()

DEFS = {"xf": ("xf", {"j": "J", "m": "X", "s": "X"}), "xg": ("xg", {"j": "J", "m": "X", "s": "X"}),
        "first": ("mv", {"first": "J", "ext": "X", "int": "X", "unk": "X"}), "sen": ("sg", {"early": "J", "exp": "X"})}
DLAB = {"xf": "<3 yrs since first position", "xg": "<3 yrs since education end", "first": "first recorded position",
        "sen": "Revelio seniority 1-2"}

def load():
    h = pd.read_parquet(os.path.join(HERE, "data", "hires_exp", os.environ.get("HIRES_FILE", "hires_exp.parquet")))
    for c in ["half", "soc6", "sg", "xf", "xg", "mv", "upd"]: h[c] = h[c].astype(str)
    return h

def describe(h):
    log(f"## 0. Descriptives of the sampled hires (1/{int(h['mod'].iloc[0])} of users; firm list; US)\n")
    t = h.groupby(["half", "mv"]).n.sum().unstack(fill_value=0); t["all"] = t.sum(1)
    log("Hires by move type (counts in the user sample):\n\n" + t.astype(int).to_markdown())
    u = h.groupby(["half", "upd"]).n.sum().unstack(fill_value=0)
    log("\nHires by profile-update vintage (u26 = updated in 2026, u25 = 2025, old = earlier/missing):\n\n" + u.astype(int).to_markdown())
    e = h[h.mv.isin(["first", "ext"])]
    for a, b in [("xf", "sg"), ("xg", "xf")]:
        c = pd.crosstab(e[a], e[b], values=e.n, aggfunc="sum", normalize="columns")
        log(f"\nExternal hires, column shares of {a} within {b}:\n\n" + c.round(3).to_markdown())
    j = e.assign(J=(e.xf == "j") * e.n).groupby("half")[["J", "n"]].sum()
    log("\nShare of external hires with <3 yrs since first position, by half: " + ", ".join(f"{k} {v:.3f}" for k, v in (j.J / j.n).items()))

def panel(h, dkey, types=("first", "ext"), upd=None, halves=HALVES):
    col, mp = DEFS[dkey]
    x = h[h.mv.isin(types) & h.half.isin(halves)]
    if upd: x = x[x.upd.isin(upd)]
    base = x
    if dkey == "xg": x = x[x.xg != "na"]
    x = x.assign(g=x[col].map(mp)).dropna(subset=["g"])
    pre = base[base.half.isin(PRE)].groupby(["rcid", "soc6"]).n.sum()
    pairs = pre[pre >= MIN_PAIR].reset_index()[["rcid", "soc6"]]; pairs = pairs[pairs.soc6.isin(EXPO.index)]
    a = x.groupby(["rcid", "soc6", "half", "g"]).n.sum()
    grid = pd.MultiIndex.from_frame(pairs.merge(pd.DataFrame({"half": halves}), how="cross").merge(pd.DataFrame({"g": ["J", "X"]}), how="cross"))
    a = a.reindex(grid, fill_value=0).reset_index()
    a["ly"] = np.log1p(a.n); a["J"] = (a.g == "J").astype(np.int8)
    a["pair"] = a.rcid.astype(str) + "_" + a.soc6; a["fh"] = a.rcid.astype(str) + "_" + a.half
    for c in ["pair", "fh", "soc6", "half", "g"]: a[c] = a[c].astype("category")
    return a

def addE(a, expo="eloundou_beta_gpt4"):
    a = a.copy(); a["E"] = a.soc6.astype(str).map(zs(expo)).astype(float); return a[a.E.notna()]

def ev_names(a, J=True):
    names = []
    w = (a.E * a.J).to_numpy() if J else a.E.to_numpy()
    for k in [h for h in HALVES if h in set(a.half.astype(str))]:
        if k == REF: continue
        nm = "k" + k; a[nm] = w * (a.half.astype(str) == k).to_numpy(); names.append(nm)
    return names

FE_T = "pair^g + fh^g + pair^half"
def triple(a, ev=True, post=POST):
    a = a.copy(); a["T"] = a.E * a.J * a.half.astype(str).isin(post)
    s = a[a.half.astype(str) <= post[-1]]
    m = pf.feols(f"ly ~ T | {FE_T}", data=s, vcov={"CRV1": "soc6"}); t = m.tidy().loc["T"]; out = dict(b=t.Estimate, se=t["Std. Error"], p=t["Pr(>|t|)"])
    if ev:
        names = ev_names(a); m = pf.feols("ly ~ " + " + ".join(names) + f" | {FE_T}", data=a, vcov={"CRV1": "soc6"})
        tt = m.tidy().loc[names]; leads = [n for n in names if n[1:] < REF]
        R = np.zeros((len(leads), len(names)))
        for i, n in enumerate(leads): R[i, names.index(n)] = 1
        w = m.wald_test(R=R)
        V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames).loc[names, names].to_numpy()
        out.update(ev=pd.DataFrame({"half": [n[1:] for n in names], "b": tt.Estimate.values, "se": tt["Std. Error"].values}),
                   chi2=float(w["statistic"]), pw=float(w["pvalue"]), V=V, npre=len(leads))
    return out

def level(a, grp, post=POST):
    s = a[(a.g == grp) & (a.half.astype(str) <= post[-1])].copy(); s["T"] = s.E * s.half.astype(str).isin(post)
    m = pf.feols("ly ~ T | pair + fh", data=s, vcov={"CRV1": "soc6"}); t = m.tidy().loc["T"]
    return t.Estimate, t["Std. Error"], t["Pr(>|t|)"]

def fmt(b, se, p): return f"{b:+.3f}{star(p)} ({se:.3f})"
SHOW = ["2019H1", "2020H1", "2021H1", "2022H1", "2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2"]

def row(lab, a, r):
    e = r["ev"].set_index("half")
    cells = " | ".join(f"{e.loc[k,'b']:+.3f} ({e.loc[k,'se']:.3f})" if k in e.index else "" for k in SHOW)
    log(f"| {lab} | {a.pair.nunique():,} | {int(a.n.sum()):,} | {fmt(r['b'], r['se'], r['p'])} | {r['chi2']:.1f} | {r['pw']:.3f} | {cells} |")

HDR = ("| Spec | pairs | hires | E x J x Post | pre χ²(7) | p | " + " | ".join(SHOW) + " |\n|---|---|---|---|---|---|" + "---|" * len(SHOW))

def fig(evs, fn, title):
    fig, ax = plt.subplots(figsize=(9, 4.6)); xs = np.arange(len(HALVES))
    for i, (lab, e) in enumerate(evs.items()):
        e = e.set_index("half").reindex(HALVES); e.loc[REF] = [0, 0]; off = (i - (len(evs) - 1) / 2) * .1
        ax.errorbar(xs + off, e.b, yerr=1.96 * e.se, marker="o", ms=3.5, capsize=2, label=lab)
    ax.axhline(0, c="k", lw=.6); ax.axvline(HALVES.index(REF) + .5, c="grey", ls="--", lw=.8)
    ax.axvspan(HALVES.index("2025H2") - .5, HALVES.index("2025H2") + .5, color="grey", alpha=.15)
    ax.set_xticks(xs); ax.set_xticklabels(HALVES, rotation=45); ax.set_ylabel("E x Junior x half (per SD), ref 2022H2")
    ax.set_title(title, fontsize=10); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(O, fn), dpi=140); plt.close(fig)

def honest(r, tag):
    ev = r["ev"]; npre = r["npre"]; post = list(ev.half[npre:]); npost = len(post); b = ev.b.to_numpy()
    la = np.array([1.0 if h in POST else 0.0 for h in post]); la /= la.sum()
    l1 = np.array([1.0 if h == "2024H1" else 0.0 for h in post])
    lz = np.array([1.0 if h in ("2024H2", "2025H1") else 0.0 for h in post]); lz /= lz.sum()
    Mmax = float(np.abs(np.diff(np.concatenate([b[:npre], [0.0]]), n=2)).max())
    npz = os.path.join(D, f"expj_hd_{tag}.npz")
    np.savez(npz, beta=b, sigma=r["V"], npre=npre, npost=npost, lvecs=np.vstack([l1, la, lz]),
             lnames=np.array(["2024H1", "avg 2023H1-2025H1", "avg 2024H2-2025H1"]),
             Mvec=np.array([0.0] + [round(f * Mmax, 5) for f in (0.5, 1.0, 2.0)]), Mbarvec=np.array([0.5, 1.0, 2.0]))
    if not os.path.exists(HD_PY): log("HonestDiD venv missing; skipped"); return
    p = subprocess.run([HD_PY, os.path.join(HERE, "tools", "honest_bounds.py"), npz, os.path.join(D, f"expj_hd_{tag}")], capture_output=True, text=True)
    log(f"\nHonestDiD ({tag}): exit {p.returncode}; max |2nd diff| of leads = {Mmax:.4f}; M grid = 0, 0.5, 1, 2 x that; Mbar = 0.5, 1, 2\n")
    log("| target | restriction | M / Mbar | lb | ub |\n|---|---|---|---|---|")
    for suf in ["_sd.csv", "_rm.csv"]:
        f = os.path.join(D, f"expj_hd_{tag}{suf}")
        if not os.path.exists(f): log(p.stderr[-800:]); continue
        x = pd.read_csv(f)
        for _, z in x.iterrows():
            mm = z["M"] if "M" in x else z["Mbar"]
            log(f"| {z.target} | {z.restriction} | {'' if pd.isna(mm) else f'{mm:.4g}'} | {z.lb:.3f} | {z.ub:.3f} |")

def main():
    h = load(); describe(h)
    log("\n## 1. Triple difference, external hires (first + ext), Eloundou GPT-4 beta\n\n" + HDR)
    evs, main_r, A = {}, {}, {}
    for d in ["xf", "xg", "first", "sen"]:
        a = addE(panel(h, d)); r = triple(a); row(DLAB[d], a, r); evs[DLAB[d]] = r["ev"]; main_r[d] = r; A[d] = a
    pd.concat(evs).to_csv(os.path.join(D, "expj_event_main.csv"))
    fig(evs, "expj_1_triple_defs.png", "Junior vs experienced external hires, within firm x occupation x half (Eloundou beta)")
    log("\n## 2. Levels by group (pair + firm x half FE; E x Post)\n\n| Definition | junior | experienced |\n|---|---|---|")
    for d in ["xf", "xg", "first", "sen"]:
        log(f"| {DLAB[d]} | {fmt(*level(A[d], 'J'))} | {fmt(*level(A[d], 'X'))} |")
    log("\n## 3. Robustness of the triple difference (definition xf unless noted)\n\n" + HDR)
    for col, lab in [("felten_lm_aioe", "Felten LM-AIOE"), ("felten_aioe", "Felten AIOE (pre-LLM)"), ("eloundou_beta_human", "Eloundou beta, human")]:
        for d in ["xf", "xg"]:
            a = addE(panel(h, d), col); row(f"{lab}, {DLAB[d]}", a, triple(a))
    a = addE(panel(h, "xf", types=("first", "ext", "int", "unk"))); row("all moves incl. internal + unknown", a, triple(a))
    a = addE(panel(h, "xf", types=("first", "ext", "unk"))); row("external + unknown previous parent", a, triple(a))
    a = addE(panel(h, "xf", types=("int",))); row("internal moves only (placebo-ish)", a, triple(a))
    a = A["xf"]; a2 = a[~a.soc6.astype(str).str.startswith("15-12")]; row("excluding computer occupations 15-12xx", a2, triple(a2))
    log("\n## 4. Profile-update lag checks (definition xf)\n\n" + HDR)
    a = addE(panel(h, "xf", upd=("u26",))); r26 = triple(a); row("users updated in 2026 only", a, r26)
    a = addE(panel(h, "xf", upd=("u26", "u25"))); row("users updated 2025-2026", a, triple(a))
    a = addE(panel(h, "xg", upd=("u26",))); row("users updated in 2026, def xg", a, triple(a))
    a = A["xf"]; a3 = a[a.half.astype(str) <= "2024H2"]; r = triple(a3, post=POST[:-1]); row("end 2024H2 (Post 2023H1-2024H2)", a3, r)
    fig({"all users": main_r["xf"]["ev"], "profile updated 2026": r26["ev"]}, "expj_2_lag.png", "Lag check: triple diff (<3 yrs since first position)")
    log("\n## 5. HonestDiD, main triple difference\n")
    honest(main_r["xf"], "xf"); honest(main_r["xg"], "xg")
    with open(os.path.join(O, "expj_tables.md"), "w") as f: f.write("# Experience-based junior tables (generated by 25_exp_junior_analysis.py)\n\n" + "\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
