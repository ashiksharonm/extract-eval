"""Extraction regression gate: compare a candidate run against a baseline run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .compare import compare_reports
from .config import Config
from .metrics import evaluate
from .report import _ci, _f


@dataclass
class Regression:
    """A metric whose candidate score dropped versus the baseline."""

    metric: str
    baseline: float | None
    candidate: float | None
    delta: float
    ci95: list[float | None] | None
    significant: bool


@dataclass
class GateResult:
    comparison: dict[str, Any]
    regressions: list[Regression] = field(default_factory=list)
    min_drop: float = 0.0
    significance: str = "ci"

    @property
    def regressed(self) -> bool:
        return bool(self.regressions)


def find_regressions(
    cmp: Mapping[str, Any],
    min_drop: float = 0.0,
    significance: str = "ci",
    scope: str = "any",
) -> list[Regression]:
    """List metrics that regressed.

    A metric regresses when ``delta <= -min_drop`` (and ``delta < 0``) and, with
    ``significance="ci"``, the paired-bootstrap 95% CI of the delta lies entirely below zero.
    ``significance="none"`` flags every drop of at least ``min_drop``, which suits small sets.
    ``scope`` is ``micro`` (micro F1 only), ``fields`` (per-field F1) or ``any`` (both).
    """
    if significance not in ("ci", "none"):
        raise ValueError("significance must be 'ci' or 'none'")
    if scope not in ("micro", "fields", "any"):
        raise ValueError("scope must be 'micro', 'fields' or 'any'")
    candidates: list[tuple[str, Mapping[str, Any]]] = []
    if scope in ("micro", "any"):
        candidates.append(("micro_f1", cmp["micro_f1"]))
    if scope in ("fields", "any"):
        candidates += sorted(cmp["fields"].items())
    out: list[Regression] = []
    for name, d in candidates:
        delta = d["delta"]
        if delta is None or delta >= 0 or delta > -min_drop:
            continue
        ci = d.get("delta_ci95")
        sig = bool(ci and ci[1] is not None and ci[1] < 0)
        if significance == "ci" and not sig:
            continue
        out.append(Regression(name, d["a"], d["b"], delta, ci, sig))
    return out


def run_gate(
    gold: Mapping[str, dict[str, Any]],
    baseline: Mapping[str, dict[str, Any]],
    candidate: Mapping[str, dict[str, Any]],
    config: Config | dict[str, Any],
    n_boot: int = 1000,
    seed: int = 0,
    min_drop: float = 0.0,
    significance: str = "ci",
    scope: str = "any",
) -> GateResult:
    """Score both runs against the same gold set, compare, and flag regressions."""
    ra = evaluate(gold, baseline, config, n_boot, seed)
    rb = evaluate(gold, candidate, config, n_boot, seed)
    return gate_from_reports(ra, rb, n_boot, seed, min_drop, significance, scope)


def gate_from_reports(
    ra: Mapping[str, Any],
    rb: Mapping[str, Any],
    n_boot: int = 1000,
    seed: int = 0,
    min_drop: float = 0.0,
    significance: str = "ci",
    scope: str = "any",
) -> GateResult:
    cmp = compare_reports(ra, rb, n_boot, seed)
    return GateResult(cmp, find_regressions(cmp, min_drop, significance, scope),
                      min_drop, significance)


def render_gate_markdown(
    result: GateResult, name_a: str = "baseline", name_b: str = "candidate"
) -> str:
    """Markdown for ``$GITHUB_STEP_SUMMARY`` or a PR comment."""
    cmp = result.comparison
    verdict = ("FAILED: significant regression" if result.regressed
               else "PASSED: no significant regression")
    rule = ("CI of the paired-bootstrap delta entirely below 0"
            if result.significance == "ci" else "any drop")
    out = [
        f"## Extraction regression gate: {verdict}", "",
        f"{cmp['n_docs_compared']} paired documents. Delta = {name_b} - {name_a} (F1). "
        f"Regression rule: {rule}, drop >= {result.min_drop:g}.", "",
        f"| metric | {name_a} | {name_b} | delta | 95% CI | status |", "|---|---|---|---|---|---|",
    ]
    flagged = {r.metric for r in result.regressions}

    def row(label: str, key: str, d: Mapping[str, Any]) -> str:
        delta = "n/a" if d["delta"] is None else f"{d['delta']:+.3f}"
        ci = _ci(d.get("delta_ci95")) or "n/a"
        status = "REGRESSION" if key in flagged else (
            "improved" if (d["delta"] or 0) > 0 else "ok")
        return f"| {label} | {_f(d['a'])} | {_f(d['b'])} | {delta} | {ci} | {status} |"

    out.append(row("**micro F1**", "micro_f1", cmp["micro_f1"]))
    out += [row(f"`{f}`", f, d) for f, d in sorted(cmp["fields"].items())]
    fl = cmp["flips"]
    out += ["", f"Documents that flipped pass to fail: {len(fl['pass_to_fail'])}; "
            f"fail to pass: {len(fl['fail_to_pass'])}."]
    if fl["pass_to_fail"]:
        out.append(f"- pass to fail: {', '.join(fl['pass_to_fail'][:20])}")
    out += ["", "_Per-field checks are not corrected for multiple comparisons; "
            "raise `--min-drop` to ignore tiny drops._"]
    return "\n".join(out) + "\n"
