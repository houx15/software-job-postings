"""Design A with firm fixed effects (P2 panel, data/firm_panel from 12_firm_panel_pull.py).

Cell: firm f (Revelio ultimate_parent_rcid) x SOC-2018 6-digit occupation o x seniority group s (early 1-2 / exp 3-4) x quarter t.
Sample: firms with >= 50 pre-period postings (11); firm x occupation pairs with >= MIN_CELL pre-period (2021Q1-2022Q3)
postings in EACH seniority group; balanced over 2021Q1..LAST_FULL_Q with zeros. Outcome log(1+n).
Main:  ly ~ Early*E*Post + Early*E*Post2 | f^t + o^t + o^s + s^t, SE clustered by occupation.  (f^t = firm x quarter FE:
       compares early vs experienced postings of the same firm in the same quarter, across occupations of different exposure.)
E = Eloundou GPT-4 beta, z-scored across all scored occupations (same as 10_designA.py). Post = 2023Q1+, Post2 = 2025Q3+.
Event study: Early*E*1[t=k], reference 2022Q3 (avoids the anomalous 2022Q4 / Jan-Feb 2023 seniority-3 spike), joint Wald on leads.
Honest DiD (Rambachan-Roth 2023): tools/honest_bounds.py in ~/.venvs/honestdid (SD and RM), plus own closed-form identified sets.
Outputs: figures/designA_firmFE_*.png, docs/designA_firmFE_tables.md; coefficient files under data/firmFE/ (git-ignored).
Usage: uv run python 13_designA_firmFE.py
"""
import glob, os, subprocess, sys, time
import numpy as np, pandas as pd
import pyfixest as pf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, "figures"); OUT = os.path.join(HERE, "data", "firmFE")
HD_PY = os.path.expanduser("~/.venvs/honestdid/bin/python")
LAST_FULL_Q = "2026Q2"; REF = "2022Q3"; POST1 = "2023Q1"; POST2 = "2025Q3"; PRE_END = "2022Q3"
MIN_CELL = int(os.environ.get("MIN_CELL", 5))
EXPO = pd.read_csv(os.path.join(HERE, "data", "exposure", "exposure_soc6.csv")).set_index("soc6")
STAFF = set(pd.read_csv(os.path.join(HERE, "data", "staffing_rcids.csv")).rcid.astype("int64"))
FE_MAIN = "rcid^q + soc6^q + soc6^sg + sg^q"
LOG = []

def log(s):
    print(s, flush=True); LOG.append(s)

_cache = {}
def load(country, srcs, last_q):
    key = (country, tuple(srcs), last_q)
    if key in _cache: return _cache[key]
    parts = []
    for f in sorted(glob.glob(os.path.join(HERE, "data", "firm_panel", "*.parquet"))):
        q = str(pd.Period(os.path.basename(f)[:7], "M").asfreq("Q"))
        if q > last_q: continue
        x = pd.read_parquet(f, columns=["country", "rcid", "soc6", "sg", "src", "n"])
        x = x[(x.country == country) & x.src.isin(srcs)]
        x = x.groupby(["rcid", "soc6", "sg"], observed=True).n.sum().reset_index(); x["q"] = q
        parts.append(x)
    d = pd.concat(parts, ignore_index=True)
    d["soc6"] = d.soc6.astype(str); d["sg"] = d.sg.astype(str)
    d = d.groupby(["rcid", "soc6", "sg", "q"]).n.sum().reset_index()
    _cache[key] = d
    return d

def cells(country="United States", srcs=("li_only", "other"), drop_staff=False, last_q=LAST_FULL_Q, expo="eloundou_beta_gpt4",
          min_cell=MIN_CELL):
    d = load(country, list(srcs), last_q)
    if drop_staff: d = d[~d.rcid.isin(STAFF)]
    e = EXPO[expo].dropna(); z = (e - e.mean()) / e.std()
    d = d[d.soc6.isin(z.index)]
    pre = d[d.q <= PRE_END].pivot_table(index=["rcid", "soc6"], columns="sg", values="n", aggfunc="sum", fill_value=0)
    pairs = pre[(pre.get("early", 0) >= min_cell) & (pre.get("exp", 0) >= min_cell)].reset_index()[["rcid", "soc6"]]
    qs = [str(q) for q in pd.period_range("2021Q1", last_q, freq="Q")]; Q = len(qs)
    pairs["pid"] = np.arange(len(pairs))
    x = d.merge(pairs, on=["rcid", "soc6"])
    key = x.pid.to_numpy() * 2 * Q + (x.sg == "exp").to_numpy() * Q + x.q.map({q: i for i, q in enumerate(qs)}).to_numpy()
    n = np.zeros(len(pairs) * 2 * Q, dtype=np.float64); np.add.at(n, key, x.n.to_numpy())
    pid = np.repeat(np.arange(len(pairs)), 2 * Q); sgi = np.tile(np.repeat([0, 1], Q), len(pairs)); qi = np.tile(np.arange(Q), 2 * len(pairs))
    g = pd.DataFrame({"rcid": pairs.rcid.to_numpy()[pid], "soc6": pairs.soc6.to_numpy()[pid], "sg": np.where(sgi == 0, "early", "exp"),
                      "qi": qi, "q": np.array(qs)[qi], "n": n})
    g["ly"] = np.log1p(g.n); g["early"] = 1 - sgi; g["E"] = g.soc6.map(z).astype(float)
    g["post"] = (g.q >= POST1).astype(int); g["post2"] = (g.q >= POST2).astype(int); g["pid"] = pid
    return g

def desc(g, lab):
    log(f"SAMPLE {lab}: {g.rcid.nunique():,} firms, {g.soc6.nunique()} occupations, {g.pid.nunique():,} firm-occ pairs, "
        f"{len(g):,} cells, {int(g.n.sum()):,} postings")

def did(g, fe=FE_MAIN, vcov=None, extra_rhs=""):
    g = g.copy(); g["T1"] = g.early * g.E * g.post; g["T2"] = g.early * g.E * g.post2
    if extra_rhs: g["EP1"] = g.E * g.post; g["EP2"] = g.E * g.post2
    m = pf.feols(f"ly ~ T1 + T2{extra_rhs} | {fe}", data=g, vcov=vcov or {"CRV1": "soc6"})
    return m.tidy()

def star(p): return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
def fmt(t, term):
    if term not in t.index: return "n/a"
    r = t.loc[term]; return f"{r['Estimate']:.3f}{star(r['Pr(>|t|)'])} ({r['Std. Error']:.3f})"

def event(g, fe=FE_MAIN, ref=REF):
    g = g.copy(); qs = sorted(g.q.unique()); names = []
    for q in qs:
        if q == ref: continue
        nm = "k_" + q; g[nm] = (g.early * g.E * (g.q == q)).astype(float); names.append(nm)
    m = pf.feols("ly ~ " + " + ".join(names) + f" | {fe}", data=g, vcov={"CRV1": "soc6"})
    b = m.coef()[names].to_numpy(); V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames).loc[names, names].to_numpy()
    leads = [n for n in names if n[2:] < ref]
    R = np.zeros((len(leads), len(names)))
    for i, n in enumerate(leads): R[i, names.index(n)] = 1
    w = m.wald_test(R=R)
    t = pd.DataFrame({"q": [n[2:] for n in names], "b": b, "se": np.sqrt(np.diag(V))})
    return t, b, V, len(leads), float(w["statistic"]), float(w["pvalue"])

# ---------- own closed-form identified sets (cross-check of honestdid; documented in docs/designA_firmFE_results.md)
def own_bounds(b, V, npre, l, Mvec, Mbar):
    """b, V: event coefficients without ref, pre first (t=-npre..-1), post (k=1..npost). l: weights on post.
    SD(M): delta_0 = 0; delta_k = k*(delta_0 - delta_-1) +- M*k(k+1)/2  (RR Delta^SD, last-slope extrapolation).
    'reg' variant: slope from OLS through the origin on all pre coefficients (a smoother, more stable extrapolation).
    RM(Mbar): |delta_{k}-delta_{k-1}| <= Mbar * max pre |first difference| -> theta in l'b_post -+ Mbar*G*sum l_k k.
    Naive CI = identified set +- 1.96 SE of the point (not RR's FLCI/ARP; slightly anti-conservative when M>0)."""
    npost = len(b) - npre; k = np.arange(1, npost + 1); t = np.arange(-npre, 0)
    out = []
    a = np.zeros(len(b)); a[npre:] = l; a[npre - 1] = l @ k            # theta_last = l'b_post + b_{-1} * sum l_k k
    tw = t / (t @ t); a2 = np.zeros(len(b)); a2[npre:] = l; a2[:npre] = -(l @ k) * tw
    for nm, aa in [("SD last-slope", a), ("SD reg-slope", a2)]:
        th = aa @ b; se = np.sqrt(aa @ V @ aa)
        for M in Mvec:
            h = M * (l @ (k * (k + 1) / 2))
            out.append(dict(method=nm, M=M, point=th, se=se, id_lb=th - h, id_ub=th + h, ci_lb=th - h - 1.96 * se, ci_ub=th + h + 1.96 * se))
    G = np.abs(np.diff(np.concatenate([b[:npre], [0.0]]))).max()
    th = l @ b[npre:]; se = np.sqrt(l @ V[npre:, npre:] @ l)
    for mb in Mbar:
        h = mb * G * (np.abs(l) @ k)
        out.append(dict(method="RM", M=mb, point=th, se=se, id_lb=th - h, id_ub=th + h, ci_lb=th - h - 1.96 * se, ci_ub=th + h + 1.96 * se))
    return pd.DataFrame(out), G

def main():
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    rows = []
    def row(lab, g, **kw):
        t0 = time.time(); t = did(g, **kw)
        rows.append((lab, fmt(t, "T1"), fmt(t, "T2"), g.rcid.nunique(), g.pid.nunique(), len(g)))
        log(f"DID {lab}: T1 {fmt(t,'T1')}  T2 {fmt(t,'T2')}  [{time.time()-t0:.0f}s]")

    US = cells(); desc(US, "US all sources (main)")
    row("Main: US all sources, FE f^t + o^t + o^s + s^t", US)
    row("FE as specified (f^t + o^s + s^t; E x Post, E x Post2 as controls)", US, fe="rcid^q + soc6^sg + sg^q", extra_rhs=" + EP1 + EP2")
    row("No firm FE (o^t + o^s + s^t), same firm sample", US, fe="soc6^q + soc6^sg + sg^q")
    row("+ firm x occ x seniority FE", US, fe="rcid^q + soc6^q + rcid^soc6^sg + sg^q")
    row("+ firm x seniority x quarter FE", US, fe="rcid^sg^q + soc6^q + soc6^sg")
    row("Two-way cluster (occupation + firm)", US, vcov={"CRV1": "soc6+rcid"})
    LI = cells(srcs=("li_only",)); desc(LI, "US LinkedIn-only")
    row("US LinkedIn-only postings", LI)
    XS = cells(drop_staff=True); desc(XS, "US ex staffing")
    row("Excluding staffing/outsourcing parents", XS)
    row("LinkedIn-only and excluding staffing", cells(srcs=("li_only",), drop_staff=True))
    row("Exposure = Felten LM-AIOE", cells(expo="felten_lm_aioe"))
    row("Larger cells (>= 20 pre postings per seniority group)", cells(min_cell=20))
    # YoY: 4-quarter log difference within cell; treatment terms as in 10_designA.py
    g = US.sort_values(["pid", "early", "qi"]).copy(); g["dy"] = g.ly - g.groupby(["pid", "early"]).ly.shift(4)
    g = g[g.qi >= 4].copy(); g["ly"] = g.dy
    row("Outcome = YoY log change (from 2022Q1)", g)
    # placebo in time: fake event 2022Q1, pre-period only
    g = US[US.q <= PRE_END].copy(); g["post"] = (g.q >= "2022Q1").astype(int); g["post2"] = 0
    g["T1"] = g.early * g.E * g.post
    m = pf.feols(f"ly ~ T1 | {FE_MAIN}", data=g, vcov={"CRV1": "soc6"}); tt = m.tidy()
    rows.append(("Placebo: fake event 2022Q1, data to 2022Q3", fmt(tt, "T1"), "", g.rcid.nunique(), g.pid.nunique(), len(g)))
    log(f"PLACEBO 2022Q1: {fmt(tt,'T1')}")
    CN = cells(country="China", srcs=("cn_board",), last_q="2025Q2"); desc(CN, "China CN boards")
    row("China, CN boards only (to 2025Q2; descriptive)", CN)

    # ---------- event studies
    ev, pre_tests = {}, []
    for lab, g in [("US all sources, firm FE", US), ("US all sources, no firm FE", None), ("US LinkedIn-only, firm FE", LI),
                   ("US ex staffing, firm FE", XS), ("China CN boards, firm FE", CN)]:
        t0 = time.time()
        if lab == "US all sources, no firm FE":
            t, b, V, npre, F, p = event(US, fe="soc6^q + soc6^sg + sg^q")
        else:
            t, b, V, npre, F, p = event(g)
        ev[lab] = (t, b, V, npre); pre_tests.append((lab, F, p, npre))
        t.to_csv(os.path.join(OUT, "event_" + lab.replace(" ", "_").replace(",", "") + ".csv"), index=False)
        log(f"EVENT {lab}: pre-trend Wald F={F:.2f} p={p:.4f} ({npre} leads) [{time.time()-t0:.0f}s]")

    # ---------- honest DiD on the main US event study and LinkedIn-only
    hd_tabs = {}
    for lab in ["US all sources, firm FE", "US LinkedIn-only, firm FE"]:
        t, b, V, npre = ev[lab]; post_q = list(t.q[npre:]); npost = len(post_q)
        l1 = np.array([1.0 if q == POST1 else 0.0 for q in post_q])
        la = np.array([1.0 if q >= POST1 else 0.0 for q in post_q]); la /= la.sum()
        l2 = np.array([1.0 if q >= POST2 else 0.0 for q in post_q]); l2 /= l2.sum()
        sd2 = np.abs(np.diff(np.concatenate([b[:npre], [0.0]]), n=2)); Mmax = float(sd2.max())
        Mvec = [0.0] + [round(f * Mmax, 5) for f in (0.25, 0.5, 1.0)]; Mbar = [0.25, 0.5, 1.0, 1.5, 2.0]
        tag = "hd_" + ("main" if lab.startswith("US all") else "li")
        npz = os.path.join(OUT, tag + ".npz")
        np.savez(npz, beta=b, sigma=V, npre=npre, npost=npost, lvecs=np.vstack([l1, la, l2]),
                 lnames=np.array(["2023Q1", "avg 2023Q1-2026Q2", "avg 2025Q3-2026Q2"]), Mvec=np.array(Mvec), Mbarvec=np.array(Mbar))
        own = pd.concat([own_bounds(b, V, npre, l, Mvec, Mbar)[0].assign(target=nm)
                         for l, nm in [(l1, "2023Q1"), (la, "avg 2023Q1-2026Q2"), (l2, "avg 2025Q3-2026Q2")]])
        own.to_csv(os.path.join(OUT, tag + "_own.csv"), index=False)
        t0 = time.time()
        r = subprocess.run([HD_PY, os.path.join(HERE, "tools", "honest_bounds.py"), npz, os.path.join(OUT, tag)], capture_output=True, text=True)
        log(f"HONESTDID {lab}: exit {r.returncode} [{time.time()-t0:.0f}s] max pre 2nd diff {Mmax:.4f}")
        if r.returncode: log(r.stderr[-2000:])
        hd_tabs[lab] = (own, Mvec, Mmax)

    # ---------- write tables
    with open(os.path.join(HERE, "docs", "designA_firmFE_tables.md"), "w") as f:
        f.write(f"<!-- generated by 13_designA_firmFE.py; MIN_CELL={MIN_CELL} -->\n\n")
        f.write("| Specification | Early x E x Post (2023Q1+) | Early x E x Post2 (2025Q3+) | firms | firm-occ pairs | cells |\n|---|---|---|---|---|---|\n")
        for r_ in rows: f.write(f"| {r_[0]} | {r_[1]} | {r_[2]} | {r_[3]:,} | {r_[4]:,} | {r_[5]:,} |\n")
        f.write(f"\nEvent-study pre-trend tests (joint Wald on leads 2021Q1-2022Q2, ref {REF}):\n\n| Event study | F | p | leads |\n|---|---|---|---|\n")
        for lab, F, p, k in pre_tests: f.write(f"| {lab} | {F:.2f} | {p:.4f} | {k} |\n")
        f.write("\nEvent-study coefficients (Early x E x quarter, SE clustered by occupation):\n\n| quarter | " + " | ".join(ev) + " |\n|---|" + "---|" * len(ev) + "\n")
        allq = sorted(set().union(*[set(v[0].q) for v in ev.values()]) | {REF})
        for q in allq:
            cells_ = []
            for v in ev.values():
                x = v[0].set_index("q")
                cells_.append("0 (ref)" if q == REF else (f"{x.loc[q,'b']:.3f} ({x.loc[q,'se']:.3f})" if q in x.index else ""))
            f.write(f"| {q} | " + " | ".join(cells_) + " |\n")
        for lab, (own, Mvec, Mmax) in hd_tabs.items():
            tag = "hd_" + ("main" if lab.startswith("US all") else "li")
            f.write(f"\n### Honest DiD, {lab}\n\nMax |2nd difference| of pre-period coefficients = {Mmax:.4f}.\n\n")
            for suf, nm in [("_sd.csv", "honestdid package, Delta^SD(M), FLCI 95%"), ("_rm.csv", "honestdid package, Delta^RM(Mbar), C-LF 95%")]:
                p_ = os.path.join(OUT, tag + suf)
                if os.path.exists(p_):
                    x = pd.read_csv(p_); f.write(f"{nm}:\n\n| target | restriction | M / Mbar | lb | ub |\n|---|---|---|---|---|\n")
                    for _, z in x.iterrows():
                        mm = z.get("M", np.nan) if "M" in x else z.get("Mbar")
                        f.write(f"| {z.target} | {z.restriction} | {'' if pd.isna(mm) else f'{mm:.4g}'} | {z.lb:.3f} | {z.ub:.3f} |\n")
                    f.write("\n")
            f.write("Own closed-form identified sets (naive CI = set +- 1.96 SE):\n\n| target | method | M / Mbar | point | SE | identified set | naive 95% CI |\n|---|---|---|---|---|---|---|\n")
            for _, z in own.iterrows():
                f.write(f"| {z.target} | {z.method} | {z.M:.4g} | {z.point:.3f} | {z.se:.3f} | [{z.id_lb:.3f}, {z.id_ub:.3f}] | [{z.ci_lb:.3f}, {z.ci_ub:.3f}] |\n")
        f.write("\nLog:\n\n```\n" + "\n".join(LOG) + "\n```\n")

    # ---------- figures
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, lab in enumerate(["US all sources, firm FE", "US all sources, no firm FE", "US LinkedIn-only, firm FE", "US ex staffing, firm FE"]):
        t = ev[lab][0].copy(); t = pd.concat([t, pd.DataFrame({"q": [REF], "b": [0.0], "se": [0.0]})]).sort_values("q")
        x = np.arange(len(t)) + (i - 1.5) * 0.12
        ax.errorbar(x, t.b, yerr=1.96 * t.se, fmt="o-", ms=3.5, lw=1.2, capsize=2, label=lab)
    ax.set_xticks(np.arange(len(t))); ax.set_xticklabels(t.q, rotation=60, fontsize=8)
    ax.axhline(0, color="k", lw=.6); ax.axvline(list(t.q).index(REF), color="gray", ls=":", lw=1)
    ax.axvline(list(t.q).index("2022Q4") + .5, color="tab:red", ls="--", lw=1); ax.text(list(t.q).index("2022Q4") + .6, ax.get_ylim()[1] * .9, "ChatGPT", color="tab:red", fontsize=8)
    ax.axvline(list(t.q).index(POST2) - .5, color="tab:purple", ls="--", lw=1)
    ax.set_title(f"Early x AI-exposure (Eloundou GPT-4 beta, z) x quarter, firm-level panel, ref {REF}, 95% CI clustered by occupation", fontsize=10)
    ax.set_ylabel("log points per SD of exposure"); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(os.path.join(FIG, "designA_firmFE_1_event_us.png"), dpi=150); plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
    tag = "hd_main"; sd_p = os.path.join(OUT, tag + "_sd.csv"); rm_p = os.path.join(OUT, tag + "_rm.csv")
    own = hd_tabs["US all sources, firm FE"][0]
    for ax, tg in zip(axs, ["2023Q1", "avg 2023Q1-2026Q2", "avg 2025Q3-2026Q2"]):
        if os.path.exists(sd_p):
            x = pd.read_csv(sd_p); x = x[(x.target == tg) & (x.restriction == "SD")]
            ax.vlines(np.arange(len(x)), x.lb, x.ub, color="tab:blue", lw=3, label="HonestDiD SD FLCI")
            ax.set_xticks(np.arange(len(x))); ax.set_xticklabels([f"{m:.3g}" for m in x.M])
        o = own[(own.target == tg) & (own.method == "SD reg-slope")]
        ax.vlines(np.arange(len(o)) + .2, o.ci_lb, o.ci_ub, color="tab:orange", lw=3, label="own, reg-slope extrapolation")
        ax.axhline(0, color="k", lw=.6); ax.set_title(tg, fontsize=10); ax.set_xlabel("M (smoothness, log pts / quarter^2)")
    axs[0].legend(fontsize=7); axs[0].set_ylabel("effect, log points per SD exposure")
    fig.suptitle("Rambachan-Roth bounds: US all sources, firm FE; M = 0 means the pre-trend continues linearly", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "designA_firmFE_2_honest_sd.png"), dpi=150); plt.close(fig)

    if os.path.exists(rm_p):
        x = pd.read_csv(rm_p); fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
        for ax, tg in zip(axs, ["2023Q1", "avg 2023Q1-2026Q2", "avg 2025Q3-2026Q2"]):
            y = x[x.target == tg]; ax.vlines(y.Mbar, y.lb, y.ub, lw=4); ax.axhline(0, color="k", lw=.6); ax.set_title(tg, fontsize=10)
            ax.set_xlabel("Mbar (post violation relative to max pre violation)")
        fig.suptitle("Rambachan-Roth relative-magnitude bounds (C-LF 95%), US all sources, firm FE", fontsize=10)
        fig.tight_layout(); fig.savefig(os.path.join(FIG, "designA_firmFE_3_honest_rm.png"), dpi=150); plt.close(fig)

    t = ev["China CN boards, firm FE"][0]; t = pd.concat([t, pd.DataFrame({"q": [REF], "b": [0.0], "se": [0.0]})]).sort_values("q")
    fig, ax = plt.subplots(figsize=(10, 4.5)); ax.errorbar(np.arange(len(t)), t.b, yerr=1.96 * t.se, fmt="o-", ms=3.5, capsize=2, color="tab:red")
    ax.set_xticks(np.arange(len(t))); ax.set_xticklabels(t.q, rotation=60, fontsize=8); ax.axhline(0, color="k", lw=.6)
    ax.set_title("China CN boards (Zhaopin/51job/Liepin), firm FE event study, ref 2022Q3. Descriptive: boards re-coded seniority in 2023", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "designA_firmFE_4_event_china.png"), dpi=150); plt.close(fig)
    log(f"DONE in {time.time()-T0:.0f}s")

if __name__ == "__main__":
    main()
