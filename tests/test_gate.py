import json
from pathlib import Path

import pytest

from extract_eval import Config
from extract_eval.cli import main
from extract_eval.gate import find_regressions, render_gate_markdown, run_gate

EX = Path(__file__).parent.parent / "examples"
CFG = Config.from_yaml(EX / "receipts.yaml")


def _gold(n=30):
    return {f"d{i}": {"vendor": f"Shop {i}", "total": str(i + 1),
                      "items": [{"name": "tea", "qty": 1, "price": i + 1}]} for i in range(n)}


def _break_total(gold, k):
    pred = {i: json.loads(json.dumps(v)) for i, v in gold.items()}
    for i in list(pred)[:k]:
        pred[i]["total"] = "999"
    return pred


def test_identical_runs_do_not_regress():
    g = _gold()
    res = run_gate(g, g, g, CFG, n_boot=200)
    assert not res.regressed
    assert "PASSED" in render_gate_markdown(res)


def test_significant_regression_is_flagged_per_field():
    g = _gold()
    res = run_gate(g, g, _break_total(g, 20), CFG, n_boot=300)
    names = {r.metric for r in res.regressions}
    assert "total" in names and "micro_f1" in names
    assert "vendor" not in names
    md = render_gate_markdown(res)
    assert "FAILED" in md and "REGRESSION" in md


def test_improvement_is_not_a_regression():
    g = _gold()
    res = run_gate(g, _break_total(g, 20), g, CFG, n_boot=200)
    assert not res.regressed


def test_small_drop_not_significant_but_flagged_without_ci():
    g = _gold()
    cand = _break_total(g, 1)
    ci = run_gate(g, g, cand, CFG, n_boot=300)
    assert "total" not in {r.metric for r in ci.regressions}
    strict = run_gate(g, g, cand, CFG, n_boot=300, significance="none")
    assert "total" in {r.metric for r in strict.regressions}
    floor = run_gate(g, g, cand, CFG, n_boot=300, significance="none", min_drop=0.5)
    assert not floor.regressed


def test_scope_and_validation():
    g = _gold()
    res = run_gate(g, g, _break_total(g, 20), CFG, n_boot=100, scope="micro")
    assert [r.metric for r in res.regressions] == ["micro_f1"]
    with pytest.raises(ValueError):
        find_regressions(res.comparison, significance="x")
    with pytest.raises(ValueError):
        find_regressions(res.comparison, scope="x")


def _write(path, docs):
    path.write_text("\n".join(json.dumps({"id": i, "data": d}) for i, d in docs.items()))


def test_cli_compare_jsonl_exit_codes_and_summary(tmp_path, capsys):
    g = _gold()
    gp, bp, cp, sp = (tmp_path / n for n in ("g.jsonl", "b.jsonl", "c.jsonl", "sum.md"))
    _write(gp, g)
    _write(bp, g)
    _write(cp, _break_total(g, 20))
    base = ["compare", str(bp), str(cp), "--gold", str(gp), "--config", str(EX / "receipts.yaml"),
            "--n-boot", "200", "--summary", str(sp)]
    assert main(base) == 1
    assert "FAILED" in sp.read_text()
    assert "REGRESSION total" in capsys.readouterr().err
    assert main(["compare", str(bp), str(bp), "--gold", str(gp), "--config",
                 str(EX / "receipts.yaml"), "--n-boot", "100"]) == 0


def test_cli_compare_usage_errors(tmp_path):
    assert main(["compare"]) == 2
    assert main(["compare", "a.jsonl", "b.jsonl"]) == 2
