"""Exploration B: an experience-based junior measure that does not use Revelio's seniority model, US vs China.
Computer occupations (O*NET 15-12xx), same deterministic job_id sample as 03/07 (US 1/50, China 1/20), 2021-01..2026-09.
Server-side, per posting:
  yoe  = minimum required years of experience, first match in the description (footer / link-farm text of the Chinese
         full-page scrapes removed with the DESC_END markers of 03; the 51job/Liepin header with "3-4年经验" is kept):
         Chinese: "N(-M)年(以上)(工作/相关/开发)经验", "经验N(-M)年", Chinese numerals 一..九 mapped to 1..9;
         English: "N(+)( - M) years ... experience" (regex of 15).  Capped at 30 (larger -> NULL).
  zero = 1 if the text says experience is not required / targets graduates: 经验不限|不限经验|无需经验|无经验要求|
         应届|在校生|毕业生|no experience (required|necessary)|new grad|recent graduate|entry[- ]level
  kw   = title-keyword class of 07 (intern_grad / junior / senior_plus / none)
  src  = source group of 12 (li_only / cn_board / other)
Only aggregated counts leave WRDS: month x country x src x seniority x yoe x zero x kw.
Output (git-ignored): data/expreq/YYYY-MM.parquet.  Usage: uv run python 21_exp_req_pull.py 2021-01 2026-09
"""
import importlib.util, os, sys, time
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
from db import connect
spec = importlib.util.spec_from_file_location("tags20", os.path.join(HERE, "20_tags_by_source_pull.py"))
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
OUT = os.path.join(HERE, "data", "expreq")
P = {"cn_re": r"([0-9一二三四五六七八九]{1,2})\s*(?:-|~|～|至|到|—)?\s*[0-9一二三四五六七八九十]{0,2}\s*年\s*(?:以上|及以上)?\s*(?:的)?\s*(?:工作|相关|开发|行业|项目)?\s*经验",
     "cn_re2": r"经验\s*[:：]?\s*([0-9]{1,2})\s*(?:-|~|～|至|到)?\s*[0-9]{0,2}\s*年",
     "en_re": r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)[^.;\n]{0,40}experience",
     "zero_re": r"经验不限|不限经验|无需经验|无经验要求|应届|在校生|毕业生|no experience (required|necessary)|new grad|recent graduate|entry[- ]level",
     "desc_end": T.T.DESC_END,
     "kw_intern": r"intern|trainee|graduate|new grad|campus|实习|校招|校园|应届|管培",
     "kw_junior": r"junior|\mjr\M|entry|associate engineer|\m(i|1)\M\s*$|初级|助理",
     "kw_senior": r"senior|\msr\M|staff|principal|\mlead|manager|director|architect|head of|\mvp\M|高级|资深|专家|主管|经理|总监|架构"}
SQL = f"""
with p as (
  select job_id, country, seniority, {T.SRC} as src
  from revelio.postings_cosmos
  where post_date >= %(start)s and post_date < %(end)s and country in ('United States', 'China') and onet_code like '15-12%%'
    and job_id %% (case when country = 'China' then 20 else 50 end) = 0
), t as (
  select p.country, p.src, p.seniority,
         lower(coalesce(r.title_raw, '') || ' | ' || coalesce(r.jobtitle_translated, '')) tt,
         lower(regexp_replace(coalesce(r.description, ''), %(desc_end)s, '')) ds
  from p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
), y as (
  select country, src, seniority, tt, ds,
         coalesce(translate(substring(ds from %(cn_re)s), '一二三四五六七八九', '123456789'),
                  substring(ds from %(cn_re2)s), substring(ds from %(en_re)s))::int yoe
  from t
)
select country, src, seniority, case when yoe > 30 then null else yoe end yoe, (ds ~* %(zero_re)s) zero,
  case when tt ~* %(kw_intern)s then 'intern_grad' when tt ~* %(kw_junior)s then 'junior'
       when tt ~* %(kw_senior)s then 'senior_plus' else 'none' end kw, count(*) n
from y group by 1, 2, 3, 4, 5, 6
"""

def main(a, b):
    os.makedirs(OUT, exist_ok=True); db = connect()
    for m in pd.period_range(a, b, freq="M"):
        f = os.path.join(OUT, f"{m}.parquet")
        if os.path.exists(f): continue
        t = time.time()
        df = db.raw_sql(SQL, params={"start": m.start_time.date().isoformat(), "end": (m + 1).start_time.date().isoformat(), **P}).copy()
        df.insert(0, "month", str(m)); df.to_parquet(f + ".tmp", index=False); os.replace(f + ".tmp", f)
        cn = df[df.country == "China"]
        print(f"{m}: {int(df.n.sum()):,} sampled; China {int(cn.n.sum()):,}, {100*cn[cn.yoe.notna()].n.sum()/max(cn.n.sum(),1):.0f}% with years, "
              f"{100*cn[cn.zero].n.sum()/max(cn.n.sum(),1):.0f}% zero-phrase; {time.time()-t:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
