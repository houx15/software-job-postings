"""Tech-stack and programming-language tags for computer-occupation postings (O*NET 15-12xx), US vs China.

Server-side: postings_cosmos (date + country + onet filter, hash sample on job_id) JOIN postings_cosmos_raw (job_id
index), regex flags per posting, aggregated to month x country x seniority group. Only counts are downloaded.
Output: data/tags/YYYY-MM.parquet (resumable).  Usage: python3 03_stack_language_tags.py 2021-01 2026-09 [SAMPLE_MOD]

Text fields
  title = title_raw || jobtitle_translated   -> STACK tags (what the job is)
  desc  = description                        -> LANGUAGE / FRAMEWORK / AI tags (what the job asks for), plus *_d
                                                description-based stack mentions for robustness
Regex: PostgreSQL ARE; \\m / \\M = word start / end. '~*' = case-insensitive, '~' = case-sensitive (marked CS).
Seniority groups: early = 1-2, mid = 3, senior = 4 (senior IC), lead = 5-7.
Sampling: keep postings with job_id %% SAMPLE_MOD = 0 (job_id is a hash-like id; the raw table is hash-partitioned
on it). SAMPLE_MOD = 1 means no sampling. Counts must be multiplied by SAMPLE_MOD; shares need no scaling.
"""
import os, sys, time
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from db import connect

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "tags")
MAX_BYTES = 5 * 1024**3

# ---------- STACK (title) ----------
TITLE_TAGS = {
  "frontend":   r"front[- ]?end|\mui (developer|engineer)|前端",
  "backend":    r"(?<!digital )back[- ]?end|server[- ]?side|(?<!数字)后端|后台开发|服务端|服务器端",  # 'digital backend' = chip design
  "fullstack":  r"full[- ]?stack|全栈",
  "web":        r"\mweb\M|网页|网站",
  "desktop":    r"desktop (application|app|software|developer|engineer)|\mwindows (application|app|software|developer|client)|"
                r"\mclient[- ](side|developer|engineer|application|software)|\mwpf\M|\melectron\M|\mqt\M|桌面|客户端|pc端",
  "mobile":     r"\mmobile\M|\mios\M|android|flutter|react native|\mapp (developer|engineer)|移动端|移动开发|安卓|鸿蒙|harmonyos|小程序|\mapp开发",
  "data_eng":   r"data engineer|big data|\metl\M|data platform|数据工程|数据开发|大数据|数仓|数据仓库",
  "ml_ai":      r"machine learning|\mml\M|\mai\M(?!-link)|artificial intelligence|deep learning|\mnlp\M|computer vision|\mllm|genai|generative|"
                r"算法|大模型|人工智能|机器学习|深度学习|自然语言|计算机视觉|图像识别|aigc",
  "devops_cloud": r"devops|\msre\M|site reliability|\mcloud\M|platform engineer|kubernetes|infrastructure engineer|运维|云计算|云平台|\m云",
  "embedded":   r"embedded|firmware|嵌入式|固件|单片机|\mbsp\M|驱动开发",
  "swe_generic": r"software (engineer|developer|development)|programmer|\mdeveloper\M|软件工程师|软件开发|开发工程师|程序员|研发工程师",
}
# ---------- LANGUAGES / FRAMEWORKS / AI (description) ----------
DESC_TAGS = {
  "py":     r"\mpython\M",
  "js":     r"javascript|\mecmascript|\mnode\.?js\M|\mjs\M",
  "ts":     r"typescript",
  "java":   r"\mjava\M",                       # \M stops 'javascript'
  "cpp":    r"c\+\+|\mcpp\M",
  "c":      r"c语言|\mansi c\M|\membedded c\M",    # + case-sensitive list-context rule in DESC_CS
  "csharp": r"c#|c＃|\.net\M|asp\.net",
  "go":     r"golang|\mgo lang\M|\mgo (programming|language)",  # + case-sensitive list-context rule in DESC_CS
  "rust":   r"\mrust\M",
  "kotlin": r"\mkotlin\M",
  "swift":  r"\mswiftui\M",                         # + case-sensitive 'Swift' in DESC_CS
  "php":    r"\mphp\M|laravel",
  "ruby":   r"\mruby\M|\mrails\M",
  "scala":  r"\mscala\M",
  "sql":    r"\msql\M|mysql|postgres|\mt-sql\M|pl/sql|oracle database|sql server",
  "react":  r"\mreact(\.?js)?\M|react native",          # case-insensitive; 'react to' risk checked in validation
  "vue":    r"\mvue(\.?js)?\M|\mnuxt",
  "angular": r"\mangular(js|\.js)?\M",
  "electron": r"\melectron(js|\.js)?\M",
  "qt":     r"\mqt\M|\mqml\M",
  "wpf":    r"\mwpf\M|winforms|windows forms|\mwinui\M|\mmfc\M|\muwp\M",
  "llm_ai": r"large language model|\mllms?\M|generative ai|\mgen ?ai\M|chatgpt|\mgpt-?[0-9]?\M|langchain|\mrag\M|"
            r"retrieval[- ]augmented|prompt engineering|\maigc\M|大模型|大语言模型|生成式|提示词",
  "ml":     r"machine learning|deep learning|pytorch|tensorflow|scikit|\mkeras\M|机器学习|深度学习|神经网络",
  "fullstack_d": r"full[- ]?stack|全栈",
  "frontend_d":  r"front[- ]?end|前端",
  "backend_d":   r"back[- ]?end|后端|服务端",
}
# Case-sensitive alternatives (operator '~'), OR-ed with the case-insensitive pattern above. Needed where the token
# is also an English word / legal enumerator: 'Go' ("go to office"), 'C' ("(c) consistent with").
# Rule: the token must sit in a list of languages: after , / ( 、 and before , / ) 、 'or' 'and'.
DESC_CS = {
  "go": r"(,|/|\(|、|：|:|>) ?(Go|GO)( ?(,|/|\)|、|;|<)| or | and )",
  "c":  r"(,|/|\(|、|：|:|>) ?C( ?(,|/|\)|、|;|<)| or | and )|(?<!Objective[- ])\mC (programming|language|and C\+\+|or C\+\+|/C\+\+)",
  "swift": r"\mSwift\M(?! (message|messages|code|codes|payment|payments|network|transfer|resolution))",
}

def build_sql(sample_mod):
    flags = [f"(tt ~* %(t_{k})s)::int as {k}" for k in TITLE_TAGS] + \
            [(f"(coalesce(ds,'') ~* %(d_{k})s or coalesce(ds,'') ~ %(cs_{k})s)::int as {k}" if k in DESC_CS
              else f"(coalesce(ds,'') ~* %(d_{k})s)::int as {k}") for k in DESC_TAGS]
    sums = [f"sum({k}) as {k}" for k in list(TITLE_TAGS) + list(DESC_TAGS)]
    any_stack = " + ".join(k for k in TITLE_TAGS if k != "swe_generic")
    return f"""
with p as (
  select job_id, country,
         case when seniority <= 2 then 'early' when seniority = 3 then 'mid'
              when seniority = 4 then 'senior' else 'lead' end as sen_group
  from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s
    and country in ('United States', 'China') and onet_code like '15-12%%'
    and job_id %% {sample_mod} = 0
), t as (
  select p.country, p.sen_group,
         coalesce(r.title_raw, '') || ' | ' || coalesce(r.jobtitle_translated, '') as tt,
         r.description as ds
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
), f as (
  select country, sen_group, (ds is not null and length(ds) > 200)::int as has_desc, {", ".join(flags)} from t
)
select country, sen_group, count(*) as n, sum(has_desc) as n_desc,
       sum(case when ({any_stack}) = 0 then 1 else 0 end) as no_stack_tag,
       {", ".join(sums)}
from f group by 1, 2
"""

def params(start, end):
    p = {"start": start, "end": end}
    p.update({f"t_{k}": v for k, v in TITLE_TAGS.items()}); p.update({f"d_{k}": v for k, v in DESC_TAGS.items()})
    p.update({f"cs_{k}": v for k, v in DESC_CS.items()})
    return p

def data_bytes():
    root = os.path.join(HERE, "data")
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)

def main(a, b, sample_mod):
    os.makedirs(OUT, exist_ok=True)
    db, sql = connect(), build_sql(sample_mod)
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f):
            continue
        if data_bytes() > MAX_BYTES:
            sys.exit("data/ exceeds 5 GB, stopping")
        t = time.time()
        df = db.raw_sql(sql, params=params(m.start_time.date().isoformat(), (m + 1).start_time.date().isoformat())).copy()
        df.insert(0, "month", str(m)); df["sample_mod"] = sample_mod
        df.to_parquet(f, index=False)
        print(f"{m}: n={int(df.n.sum()):,} sampled postings, {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20)
