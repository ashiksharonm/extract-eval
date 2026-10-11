# extract-eval

Evaluate structured extraction (LLM, OCR, document-AI) against ground truth. Handles the parts that make extraction scoring fiddly: repeated line items that come back in a different order, numbers written as `"$1,234.50"` vs `1234.5`, dates in different styles, and the need for confidence intervals and run-to-run comparison instead of a single F1.

- Field matchers: `exact`, `text` (normalized), `numeric` (tolerance, currency/thousands parsing, `us`/`eu`/`auto` locales), `date`, `fuzzy` (rapidfuzz).
- Line items are aligned with the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) before per-field scoring; unmatched gold items count as FN, unmatched predicted items as FP.
- Per-field precision/recall/F1, micro and macro averages, per-document scores, bootstrap 95% CIs over documents.
- Error buckets: `missing`, `extra`, `mismatch`, `format_only` (right value, wrong formatting).
- Run comparison: per-field deltas, paired-bootstrap CI, documents flipping pass/fail.
- YAML config, CLI with markdown reports and `--fail-under`, and `assert_min_scores()` for CI gates.

## Why Hungarian matching matters

Gold has three line items; the model returns the same three in a different order.

```python
from extract_eval import Config, score_document

cfg = Config.from_dict({"line_items": {"items": {"fields": {"name": "text", "price": "numeric"}}}})
gold = {"items": [{"name": "Latte", "price": "4.50"}, {"name": "Tea", "price": "3.00"},
                  {"name": "Cake", "price": "5.00"}]}
pred = {"items": [{"name": "Tea", "price": "3.00"}, {"name": "Cake", "price": "5.00"},
                  {"name": "Latte", "price": "4.50"}]}
score_document("d", gold, pred, cfg).counts
# {'items.name': [3, 0, 0], 'items.price': [3, 0, 0]}   # [TP, FP, FN]: perfect
```

Comparing item *i* with item *i* gets 0 of 6 values right on the same input. Alignment first, scoring second.

## Install

```bash
pip install extract-eval        # once published; for now: pip install git+https://github.com/ashiksharonm/extract-eval
```

## Quickstart

```python
from extract_eval import Config, evaluate, assert_min_scores, load_jsonl, compare_reports

cfg = Config.from_yaml("examples/receipts.yaml")
report = evaluate(load_jsonl("examples/gold.jsonl"), load_jsonl("examples/pred.jsonl"), cfg)
print(report["micro"], report["fields"]["total"]["f1"])
assert_min_scores(report, {"micro_f1": 0.8, "total": 1.0})   # raises AssertionError listing failures
```

Records are JSONL, one document per line: `{"id": "r1", "data": {...}}`. A gold document without a prediction is scored as all-missing.

## CLI

```bash
extract-eval score --gold gold.jsonl --pred pred.jsonl --config cfg.yaml \
    --out out/report.json [--markdown out/report.md] [--fail-under 0.9] [--n-boot 1000] [--seed 0]
extract-eval compare --a out/run_a.json --b out/run_b.json --out out/cmp.json
```

`score` writes `report.json` plus a markdown report and exits 1 if micro F1 is below `--fail-under`.

## Config

```yaml
default: text                  # matcher for fields without one
doc_pass_f1: 1.0               # a document "passes" when its F1 >= this
scalars:                       # dotted paths into the document
  total: {type: numeric, abs_tol: 0.005}
  date: {type: date, dayfirst: true}
  vendor: {type: fuzzy, threshold: 0.85}
line_items:
  items:
    match_on: {name: 1.0, price: 0.5}   # fields (with weights) used to align; default: all fields
    min_similarity: 0.3                 # weaker pairs stay unmatched (FN + FP)
    fields:
      name: {type: fuzzy, threshold: 0.85}
      qty: {type: numeric}
      price: {type: numeric, locale: auto}
```

Matcher options: `numeric` takes `abs_tol`, `rel_tol`, `locale` (`us`, `eu`, `auto`); `date` takes `dayfirst`; `fuzzy` takes `threshold` and `scorer` (any rapidfuzz `fuzz` scorer). Missing means `null`, `""` or whitespace; both sides missing is ignored. A wrong value counts as one FP and one FN.

## Benchmark: Donut on CORD-v2

`naver-clova-ix/donut-base-finetuned-cord-v2` on the full CORD-v2 **test split (100 docs)**, greedy decoding, Apple M5 16 GB (MPS), 216 s total (2.16 s/doc). Menu lines are aligned with Hungarian matching; totals are scalars (`benchmarks/cord.yaml`). The weak variant is the same greedy decode cut to the first 96 generated tokens (equivalent to `max_length=96`, since greedy decoding is prefix-consistent).

| run | micro F1 (95% CI) | macro F1 (95% CI) | docs with F1 = 1.0 |
|---|---|---|---|
| Donut, full decode | 0.876 [0.842, 0.908] | 0.859 [0.798, 0.900] | 47% |
| Donut, truncated to 96 tokens | 0.726 [0.644, 0.802] | 0.710 [0.624, 0.785] | 44% |
| delta (paired bootstrap) | +0.151 [0.078, 0.234] | +0.149 [0.080, 0.229] | +3 docs, 0 regressions |

Per-field F1 for the full run: `menu.nm` 0.832, `menu.cnt` 0.943, `menu.price` 0.863, `total.total_price` 0.906, `sub_total.subtotal_price` 0.892. Of 193 errors, 47 missing, 66 extra, 48 mismatch, 32 format-only. Everything is committed under [`benchmarks/cord_v2`](benchmarks/cord_v2) (gold and predictions JSONL, `report_*.json/.md`, `comparison.*`, `run_meta.json`); reproduce with `python benchmarks/run_cord.py` then `benchmarks/score_cord.sh` (needs `torch transformers datasets sentencepiece pillow`).

These numbers are not comparable to the field-level or tree-edit-distance scores in the Donut paper: the schema subset, matchers, and metric here are this repo's own (see `benchmarks/cord.yaml`).

## Limitations

- Line-item alignment uses only the fields in `match_on`; items identical on those fields are interchangeable, so ties are broken arbitrarily.
- Only scalar fields and one flat level of line items are scored; nested groups (e.g. CORD `sub` items) are ignored.
- Dates without an explicit format are parsed from a fixed list of common formats, with `dayfirst` resolving ambiguity.
- Bootstrap CIs resample documents, so they are wide for small sets and say nothing about distribution shift.
- Numeric parsing is heuristic: choose `locale` deliberately when `.` or `,` could be either separator.
- The format-only bucket is a heuristic (equal after text normalization, number parsing in either locale, or date parsing).

## Development

```bash
uv venv --python 3.11 && uv pip install -e ".[dev]"
ruff check . && pytest -q
```

MIT licensed.
