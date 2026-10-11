import json
from pathlib import Path

import pytest

from extract_eval import Config, assert_min_scores, compare_reports, evaluate
from extract_eval.cli import main

EX = Path(__file__).parent.parent / "examples"
CFG = Config.from_yaml(EX / "receipts.yaml")


def _gold():
    return {f"d{i}": {"total": str(i), "items": [{"name": "a", "qty": 1, "price": i}]}
            for i in range(1, 21)}


def test_bootstrap_ci_brackets_point_estimate_and_is_seeded():
    gold = _gold()
    pred = {k: dict(v) for k, v in gold.items()}
    for k in list(pred)[:5]:
        pred[k] = {"total": "999", "items": []}
    r1 = evaluate(gold, pred, CFG, n_boot=300, seed=1)
    r2 = evaluate(gold, pred, CFG, n_boot=300, seed=1)
    assert r1["micro"] == r2["micro"]
    lo, hi = r1["micro"]["f1_ci95"]
    assert lo <= r1["micro"]["f1"] <= hi and lo < hi


def test_compare_flips_and_deltas():
    gold = _gold()
    worse = {k: dict(v) for k, v in gold.items()}
    worse["d1"] = {"total": "0", "items": []}
    a, b = evaluate(gold, gold, CFG, 100), evaluate(gold, worse, CFG, 100)
    c = compare_reports(a, b, n_boot=100)
    assert c["flips"]["pass_to_fail"] == ["d1"] and c["flips"]["fail_to_pass"] == []
    assert c["micro_f1"]["delta"] < 0 and c["micro_f1"]["delta_ci95"][1] <= 0.0
    assert c["fields"]["total"]["delta"] < 0
    assert compare_reports(b, a, n_boot=0)["flips"]["fail_to_pass"] == ["d1"]


def test_assert_min_scores():
    rep = evaluate(_gold(), _gold(), CFG, 0)
    assert_min_scores(rep, {"micro_f1": 1.0, "macro_f1": 1.0, "total": 1.0, "pass_rate": 1.0})
    bad = {k: {"total": "0", "items": []} for k in _gold()}
    with pytest.raises(AssertionError, match="micro_f1"):
        assert_min_scores(evaluate(_gold(), bad, CFG, 0), {"micro_f1": 0.9})
    with pytest.raises(KeyError):
        assert_min_scores(rep, {"nope": 1})


def test_cli_score_and_compare(tmp_path, capsys):
    out = tmp_path / "r.json"
    args = ["score", "--gold", str(EX / "gold.jsonl"), "--pred", str(EX / "pred.jsonl"),
            "--config", str(EX / "receipts.yaml"), "--out", str(out), "--n-boot", "50"]
    assert main(args) == 0
    assert (tmp_path / "r.md").read_text().startswith("# extract-eval report")
    assert json.loads(out.read_text())["n_docs"] == 2
    assert main([*args, "--fail-under", "0.99"]) == 1
    cmp_out = tmp_path / "c.json"
    assert main(["compare", "--a", str(out), "--b", str(out), "--out", str(cmp_out),
                 "--n-boot", "20"]) == 0
    assert "Run comparison" in (tmp_path / "c.md").read_text()
