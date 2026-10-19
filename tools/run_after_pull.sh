#!/bin/bash
# Wait for a 24_hires_exp_pull.py output, then run 25 on it and keep a tagged copy of its tables. Usage: tools/run_after_pull.sh FILE TAG
cd "$(dirname "$0")/.."
while [ ! -f "data/hires_exp/$1" ]; do sleep 30; done
HIRES_FILE="$1" uv run python -u 25_exp_junior_analysis.py > "logs/25_$2.log" 2>&1
cp outputs/explore/expj_tables.md "outputs/explore/expj_tables_$2.md"
for f in outputs/explore/expj_1_triple_defs.png outputs/explore/expj_2_lag.png; do cp "$f" "${f%.png}_$2.png"; done
echo done >> "logs/25_$2.log"
