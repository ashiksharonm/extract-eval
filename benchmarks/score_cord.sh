#!/usr/bin/env bash
# Score both Donut variants and compare them. Run from the repo root after run_cord.py.
set -euo pipefail
D=benchmarks/cord_v2
for v in full trunc; do
  extract-eval score --gold $D/gold.jsonl --pred $D/preds_$v.jsonl \
    --config benchmarks/cord.yaml --out $D/report_$v.json
done
extract-eval compare --a $D/report_trunc.json --b $D/report_full.json --out $D/comparison.json
