"""Figures from data/tags (output of 03): tech-stack and language shares, US vs China, computer occupations.

Shares: title (stack) tags / all sampled postings; description (language/framework/AI) tags / postings with a
description (n_desc). Sampling: US job_id%50, China %20 (deterministic), so shares need no weights.
Monthly series are 3-month moving averages; seniority splits use quarters to reduce sampling noise.
Figures -> figures/stack_*.png ; tables -> data/summary/tags_*.csv (git-ignored).
"""
import glob, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG, SUM = os.path.join(HERE, "figures"), os.path.join(HERE, "data", "summary")
os.makedirs(FIG, exist_ok=True); os.makedirs(SUM, exist_ok=True)
LAST_FULL = "2026-08"
COUNTRIES = ["United States", "China"]
STACK = ["frontend", "backend", "fullstack", "web", "desktop", "mobile", "data_eng", "ml_ai", "devops_cloud", "embedded"]
LANG_MAJOR = ["py", "java", "js", "ts", "sql", "cpp", "c", "csharp", "go"]
LANG_MINOR = ["rust", "kotlin", "swift", "php", "ruby", "scala"]
FRAMEWORK = ["react", "vue", "angular", "electron", "qt", "wpf"]
AI = ["llm_ai", "ml"]
LABEL = {"py": "Python", "java": "Java", "js": "JavaScript/Node", "ts": "TypeScript", "sql": "SQL", "cpp": "C++", "c": "C",
         "csharp": "C#/.NET", "go": "Go", "rust": "Rust", "kotlin": "Kotlin", "swift": "Swift", "php": "PHP", "ruby": "Ruby",
         "scala": "Scala", "react": "React", "vue": "Vue", "angular": "Angular", "electron": "Electron", "qt": "Qt", "wpf": "WPF/WinForms/MFC",
         "llm_ai": "LLM / GenAI terms", "ml": "ML / deep learning", "data_eng": "data eng.", "ml_ai": "ML/AI/algorithm",
         "devops_cloud": "DevOps/cloud/ops", "fullstack": "full-stack"}
SEN = ["early", "mid", "senior", "lead"]

files = sorted(glob.glob(os.path.join(HERE, "data", "tags", "*.parquet")))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d = d[d.month <= LAST_FULL].copy()
num = [c for c in d.columns if c not in ("month", "country", "sen_group")]
d[num] = d[num].astype("float64")
d["quarter"] = d.month.str[:4] + "Q" + ((d.month.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
months = sorted(d.month.unique()); quarters = sorted(d.quarter.unique())
print(f"{len(files)} month files, {months[0]}..{months[-1]}; sampled postings: "
      + ", ".join(f"{c} {int(d[d.country == c].n.sum()):,}" for c in COUNTRIES))

def xaxis(ax, keys):
    ticks = [i for i, k in enumerate(keys) if k.endswith("-01") or k.endswith("Q1")]
    ax.set_xticks(ticks); ax.set_xticklabels([keys[i][:4] for i in ticks]); ax.set_xlim(0, len(keys) - 1); ax.grid(alpha=.3)

def shares(df, tags, denom, by="month", keys=None):
    g = df.groupby([by, "country"])[tags + [denom]].sum()
    s = 100 * g[tags].div(g[denom], axis=0)
    return s

def plot_panels(tags, denom, title, fname, ncol=2):
    s = shares(d, tags, denom)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    cmap = plt.cm.tab20(np.linspace(0, 1, 20))
    for ax, c in zip(axes, COUNTRIES):
        x = s.xs(c, level="country").reindex(months).rolling(3, min_periods=1).mean()
        for i, t in enumerate(tags):
            ax.plot(x[t].values, color=cmap[i * 2 % 20], lw=1.6, label=LABEL.get(t, t))
        ax.set_title(f"{c}: {title}", fontsize=10); xaxis(ax, months)
    axes[0].set_ylabel("% of postings (3-mo MA)"); axes[1].legend(fontsize=8, loc="center left", bbox_to_anchor=(1, .5), ncol=1)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)
    return s

s_stack = plot_panels(STACK, "n", "tech stack in job title, % of computer-occupation postings", "stack_1_title_stack_shares.png")
s_lmaj = plot_panels(LANG_MAJOR, "n_desc", "major languages mentioned in description, %", "stack_2a_languages_major.png")
s_lmin = plot_panels(LANG_MINOR, "n_desc", "other languages mentioned in description, %", "stack_2b_languages_minor.png")
s_fw = plot_panels(FRAMEWORK, "n_desc", "front-end / desktop frameworks in description, %", "stack_2c_frameworks.png")

# ---- stack x seniority: early-career share within each stack (quarterly) + stack share within early vs senior
q = d.groupby(["quarter", "country", "sen_group"])[STACK + ["n"]].sum()
fig, axes = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
for j, c in enumerate(COUNTRIES):
    x = q.xs(c, level="country")
    tot = x.groupby(level="quarter").sum()
    early = x.xs("early", level="sen_group").reindex(tot.index).fillna(0)
    ax = axes[0, j]
    for t, ls in [("fullstack", "-"), ("frontend", "-"), ("backend", "-"), ("mobile", "--"), ("ml_ai", "--")]:
        ax.plot((100 * early[t] / tot[t]).reindex(quarters).values, ls=ls, lw=1.6, label=LABEL.get(t, t))
    ax.plot((100 * early.n / tot.n).reindex(quarters).values, color="black", lw=2.2, label="all computer occ.")
    ax.set_title(f"{c}: early-career (seniority 1-2) share WITHIN each stack, %", fontsize=10); xaxis(ax, quarters)
    ax = axes[1, j]
    for t in ["fullstack", "frontend", "backend"]:
        for sg, ls in [("early", "-"), ("senior", ":")]:
            y = x.xs(sg, level="sen_group").reindex(quarters)
            ax.plot((100 * y[t] / y.n).values, ls=ls, lw=1.6, label=f"{LABEL.get(t, t)} | {sg}",
                    color={"fullstack": "C0", "frontend": "C1", "backend": "C2"}[t])
    ax.set_title(f"{c}: stack share among early (solid) vs senior-IC (dotted) postings, %", fontsize=10); xaxis(ax, quarters)
axes[0, 1].legend(fontsize=8); axes[1, 1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "stack_3_stack_by_seniority.png"), dpi=150); plt.close(fig)

# ---- LLM / GenAI mention share, by country and seniority group (quarterly)
qa = d.groupby(["quarter", "country", "sen_group"])[AI + ["n_desc"]].sum()
fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
for ax, c in zip(axes, COUNTRIES):
    x = qa.xs(c, level="country")
    tot = x.groupby(level="quarter").sum().reindex(quarters)
    ax.plot((100 * tot.llm_ai / tot.n_desc).values, color="black", lw=2.4, label="LLM/GenAI, all")
    ax.plot((100 * tot.ml / tot.n_desc).values, color="grey", lw=1.6, ls="--", label="ML/deep learning, all")
    for sg in SEN:
        y = x.xs(sg, level="sen_group").reindex(quarters)
        ax.plot((100 * y.llm_ai / y.n_desc).values, lw=1.1, label=f"LLM/GenAI, {sg}")
    ax.set_title(f"{c}: share of postings mentioning LLM/GenAI terms in description, % (quarterly)", fontsize=10); xaxis(ax, quarters)
axes[1].legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "stack_4_llm_genai_mentions.png"), dpi=150); plt.close(fig)

# ---- yearly summary table
d["year"] = d.month.str[:4]
yr = d.groupby(["country", "year"])[STACK + LANG_MAJOR + LANG_MINOR + FRAMEWORK + AI + ["n", "n_desc"]].sum()
out = pd.concat([100 * yr[STACK].div(yr.n, axis=0),
                 100 * yr[LANG_MAJOR + LANG_MINOR + FRAMEWORK + AI].div(yr.n_desc, axis=0), yr[["n", "n_desc"]]], axis=1)
ye = d[d.sen_group == "early"].groupby(["country", "year"])[["fullstack", "frontend", "backend", "n"]].sum()
for t in ["fullstack", "frontend", "backend"]:
    out[f"early_share_within_{t}"] = 100 * ye[t] / yr[t]
out["early_share_all"] = 100 * ye.n / yr.n
out.round(2).to_csv(os.path.join(SUM, "tags_yearly.csv"))
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
print(out.round(1).T.to_string())
