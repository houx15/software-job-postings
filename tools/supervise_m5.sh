#!/bin/bash
# Wait for the running m5 chain (pid $1) to exit; if the pull did not produce data/hires_exp/hires_exp.parquet, restart the chunked
# pull (finished buckets are skipped), up to 3 times. Then make sure 25 has produced outputs/explore/expj_tables_m5.md.
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 60; done
for i in 1 2 3; do
  [ -f data/hires_exp/hires_exp.parquet ] && break
  echo "$(date) restart $i" >> logs/supervise_m5.log
  MOD=5 uv run python -u 24_hires_exp_pull.py >> logs/24_m5.log 2>&1
done
if [ -f data/hires_exp/hires_exp.parquet ] && [ ! -f outputs/explore/expj_tables_m5.md ]; then
  # wait for a run_after_pull already in progress, else run it
  while pgrep -f "run_after_pull.sh hires_exp.parquet m5" >/dev/null; do sleep 60; done
  [ -f outputs/explore/expj_tables_m5.md ] || tools/run_after_pull.sh hires_exp.parquet m5
fi
echo "$(date) supervisor done; tables: $(ls outputs/explore/expj_tables_m5.md 2>/dev/null)" >> logs/supervise_m5.log
