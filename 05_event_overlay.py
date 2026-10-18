"""Overlay AI-coding / LLM milestones (docs/ai_events.csv) on quarterly job-posting series, plus a
before/after table. DESCRIPTIVE ONLY: coincident shocks (2022-23 rate hikes, tech layoffs, China platform
regulation and slowdown, Revelio source changes) make these comparisons non-causal.

Series (quarterly, US vs China, computer occupations O*NET 15-12xx):
  early-career share (seniority 1-2)           <- data/agg (01), 2018Q1+; pre-2021 coverage unreliable (shaded)
  title stack shares: frontend/fullstack/backend/mobile   <- data/tags (03), 2021Q1+
  LLM/GenAI mention share; Python/JS/Java mention share   <- data/tags (03)
Figures -> figures/event_*.png ; table -> data/summary/event_before_after.csv (git-ignored; printed).
"""
import glob, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Hiragino Sans GB", "DejaVu Sans"]  # CJK fallback for event names

HERE = os.path.dirname(os.path.abspath(__file__))
FIG, SUM = os.path.join(HERE, "figures"), os.path.join(HERE, "data", "summary")
os.makedirs(SUM, exist_ok=True)
LAST_FULL = "2026-08"          # 2026Q3 = Jul+Aug only (partial quarter)
COUNTRIES = ["United States", "China"]
CAT_COL = {"coding_tool": "#d35400", "frontier_model": "#2c3e50", "china": "#c0392b"}

def to_q(month_str):
    y, m = int(month_str[:4]), int(month_str[5:7]); return f"{y}Q{(m - 1) // 3 + 1}"
def qpos(q):  # quarter midpoint in fractional years
    return int(q[:4]) + (int(q[-1]) - 1) / 4 + 0.125

ev = pd.read_csv(os.path.join(HERE, "docs", "ai_events.csv"))
ev["dt"] = pd.to_datetime(ev.date)
ev["x"] = ev.dt.dt.year + (ev.dt.dt.dayofyear - 1) / 365.25

# ---------------- series ----------------
agg = pd.concat([pd.read_parquet(f, columns=["month", "gset", "country", "seniority", "n_posts"])
                 for f in sorted(glob.glob(os.path.join(HERE, "data", "agg", "*.parquet")))])
agg = agg[(agg.gset == "onet") & (agg.month <= LAST_FULL)].copy()
agg["q"] = agg.month.map(to_q); agg["n_posts"] = agg.n_posts.astype(float)
tot = agg.groupby(["q", "country"]).n_posts.sum()
early = agg[agg.seniority <= 2].groupby(["q", "country"]).n_posts.sum()
S = {"early_share": (100 * early / tot).unstack("country")}

tg = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(HERE, "data", "tags", "*.parquet")))])
tg = tg[tg.month <= LAST_FULL].copy(); tg["q"] = tg.month.map(to_q)
num = [c for c in tg.columns if c not in ("month", "country", "sen_group", "q")]
tg[num] = tg[num].astype(float)
g = tg.groupby(["q", "country"])[num].sum()
for t in ["frontend", "fullstack", "backend", "mobile"]:
    S[t] = (100 * g[t] / g.n).unstack("country")
for t in ["llm_ai", "py", "js", "java"]:
    S[t] = (100 * g[t] / g.n_desc).unstack("country")
LABEL = {"early_share": "early-career (seniority 1-2) share", "frontend": "frontend", "fullstack": "full-stack",
         "backend": "backend", "mobile": "mobile", "llm_ai": "LLM/GenAI terms", "py": "Python", "js": "JavaScript/Node", "java": "Java"}

# ---------------- plotting helpers ----------------
def overlay(ax, show_labels):
    """Major events: dashed line + short label in a staggered band at the top; minor events: ticks at the bottom."""
    ymin, ymax = ax.get_ylim(); rng = ymax - ymin
    majors = ev[ev.major == 1].sort_values("x").reset_index(drop=True)
    for i, e in majors.iterrows():
        c = CAT_COL[e.category]
        ax.axvline(e.x, color=c, ls="--", lw=.9, alpha=.75)
        if show_labels:
            ax.text(e.x, ymax - (0.04 + 0.055 * (i % 4)) * rng, " " + e.label, fontsize=7, color=c, ha="left", va="center",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=.8, pad=.5))
    for _, e in ev[ev.major == 0].iterrows():
        ax.plot([e.x, e.x], [ymin, ymin + 0.035 * rng], color=CAT_COL[e.category], lw=1.2, alpha=.9)
    ax.set_ylim(ymin, ymax)

def draw(series_keys, fname, title, xmin=2018.0, shade_pre2021=True):
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.2), sharey=True)
    for ax, c in zip(axes, COUNTRIES):
        for i, k in enumerate(series_keys):
            s = S[k][c].dropna()
            ax.plot([qpos(q) for q in s.index], s.values, marker="o", ms=2.5, lw=1.7, label=LABEL[k], color=f"C{i}")
        ax.set_xlim(xmin, 2027.0); ax.grid(alpha=.25); ax.set_title(f"{c}: {title}", fontsize=10)
        if shade_pre2021 and xmin < 2021:
            ax.axvspan(xmin, 2021.0, color="grey", alpha=.12, lw=0)
            ax.text(xmin + .05, ax.get_ylim()[0], "pre-2021: Revelio coverage unreliable", fontsize=7, color="grey", va="bottom")
    lo = min(a.get_ylim()[0] for a in axes); hi0 = max(a.get_ylim()[1] for a in axes); hi = hi0 + 0.3 * (hi0 - lo)
    for i, ax in enumerate(axes):
        ax.set_ylim(lo, hi); overlay(ax, show_labels=True)
    axes[0].set_ylabel("% (quarterly)"); axes[0].legend(fontsize=8, loc="lower left")
    handles = [plt.Line2D([], [], color=v, ls="--", label=k.replace("_", " ")) for k, v in CAT_COL.items()]
    fig.legend(handles=handles, fontsize=8, loc="lower center", ncol=3, frameon=False,
               title="AI events (docs/ai_events.csv): dashed = major (labeled), bottom tick = minor", title_fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)

draw(["early_share"], "event_1_early_career_share.png", "early-career share of computer-occupation postings")
draw(["frontend", "fullstack", "backend", "mobile"], "event_2_stack_titles.png", "stack in job title, % of postings", xmin=2021.0)
draw(["llm_ai"], "event_3_llm_mentions.png", "postings mentioning LLM/GenAI terms, %", xmin=2021.0)
draw(["py", "js", "java"], "event_4_languages.png", "language mentioned in description, %", xmin=2021.0)

# event timeline strip (all events, readable list)
fig, ax = plt.subplots(figsize=(16, 7))
evs = ev.sort_values("dt").reset_index(drop=True)
for i, e in evs.iterrows():
    ax.plot(e.x, i, "o", color=CAT_COL[e.category], ms=6 if e.major else 4)
    ax.text(e.x + .04, i, f"{e.date}  {e.event}", fontsize=7, va="center", color=CAT_COL[e.category], fontweight="bold" if e.major else "normal")
ax.set_xlim(2021.3, 2028.6); ax.set_yticks([]); ax.invert_yaxis(); ax.grid(axis="x", alpha=.3)
ax.set_title("AI-coding / LLM milestones (docs/ai_events.csv; bold = major; orange coding tool, navy frontier model, red China)", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "event_0_timeline.png"), dpi=150); plt.close(fig)

# ---------------- before/after table ----------------
KEY = {"Copilot GA (2022-06-21)": "2022-06-21", "ChatGPT (2022-11-30)": "2022-11-30",
       "Claude Code GA / agentic coding (2025-05-22)": "2025-05-22"}
def shift(q, k):
    y, n = int(q[:4]), int(q[-1]) - 1 + k
    return f"{y + n // 4}Q{n % 4 + 1}"
rows = []
for name, d in KEY.items():
    eq = to_q(d)
    before = [shift(eq, -k) for k in range(4, 0, -1)]; after = [shift(eq, k) for k in range(1, 5)]
    for k, df in S.items():
        for c in COUNTRIES:
            s = df[c]
            b, a = s.reindex(before), s.reindex(after)
            rows.append(dict(event=name, series=LABEL[k], country=c, before_quarters=f"{before[0]}-{before[-1]}",
                             after_quarters=f"{after[0]}-{after[-1]}", before_mean=b.mean(), after_mean=a.mean(),
                             change_pp=a.mean() - b.mean(), n_before=int(b.notna().sum()), n_after=int(a.notna().sum())))
T = pd.DataFrame(rows)
T.round(2).to_csv(os.path.join(SUM, "event_before_after.csv"), index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print("NOTE: 4 quarters before vs 4 after the event quarter (event quarter excluded). Descriptive, not causal.")
print(T.round(1).to_string(index=False))
