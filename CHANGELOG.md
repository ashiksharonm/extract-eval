# Changelog

## 0.2.0
- `extract-eval compare BASELINE CANDIDATE`: regression gate over prediction JSONL (with `--gold`/`--config`) or `report.json` files; per-field F1 deltas with paired-bootstrap 95% CIs; exit 1 on significant regression.
- GitHub Action (`action.yml`) that runs the gate and writes `$GITHUB_STEP_SUMMARY` / PR comment.
- Gradio demo (`space/`).
- Packaging: single-source version, `py.typed`, mypy, coverage gate.

## 0.1.0
- Initial release: Hungarian line-item matching, field matchers, bootstrap CIs, run comparison.
