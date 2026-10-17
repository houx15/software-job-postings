"""Hand-validation helper: for a small sample, show the text around each regex hit. Output stays on this Mac
(data/validation/, git-ignored). Usage: python3 tools/tag_snippets.py TAG [N] [DATE] [COUNTRY]"""
import sys, os, importlib.util; sys.path.insert(0, "tools")
spec = importlib.util.spec_from_file_location("m", "03_stack_language_tags.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from db import connect
tag = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
day = sys.argv[3] if len(sys.argv) > 3 else "2024-03-05"; ctry = sys.argv[4] if len(sys.argv) > 4 else "United States"
title = tag in m.TITLE_TAGS; pat = m.TITLE_TAGS.get(tag) or m.DESC_TAGS[tag]
col = "coalesce(r.title_raw,'')||' | '||coalesce(r.jobtitle_translated,'')" if title else "coalesce(" + m.CLEAN_DESC + ",'')"
db = connect()
d = db.raw_sql(f"""select left(r.title_raw,50) title, (regexp_match({col}, '(.{{0,45}}(?:' || %(p)s || ').{{0,30}})', 'i'))[1] hit, (regexp_match({col}, '(.{{0,45}}(?:' || %(cs)s || ').{{0,30}})'))[1] hit2
  from revelio.postings_cosmos p join revelio.postings_cosmos_raw r on r.job_id = p.job_id
  where p.post_date = %(d)s and p.country = %(c)s and p.onet_code like '15-12%%' and p.job_id %% 20 = 0
    and ({col} ~* %(p)s or {col} ~ %(cs)s) limit %(n)s""", params={"desc_start": m.DESC_START, "desc_end": m.DESC_END, "p": pat, "cs": m.DESC_CS.get(tag, "^\\b$NEVER"), "d": day, "c": ctry, "n": n})
os.makedirs("data/validation", exist_ok=True)
d.to_csv(f"data/validation/{tag}_{ctry[:2]}_{day}.csv", index=False)
for _, r in d.iterrows(): print(f"[{r.title}] ...{(r.hit if isinstance(r.hit, str) else (r.hit2 if isinstance(r.hit2, str) else '')).replace(chr(10),' ')}...")
