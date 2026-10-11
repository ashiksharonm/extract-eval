"""Markdown rendering of score and comparison reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .scoring import BUCKETS


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _ci(ci: list[float | None] | None) -> str:
    return "" if not ci or ci[0] is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def render_markdown(report: Mapping[str, Any], max_errors: int = 15) -> str:
    m, M = report["micro"], report["macro"]
    out = [
        "# extract-eval report", "",
        f"- Documents: {report['n_docs']}",
        f"- Micro P/R/F1: {_f(m['precision'])} / {_f(m['recall'])} / **{_f(m['f1'])}** "
        f"95% CI {_ci(m['f1_ci95'])}",
        f"- Macro F1: **{_f(M['f1'])}** 95% CI {_ci(M['f1_ci95'])}",
        f"- Docs passing (doc F1 >= {report['doc_pass_f1']}): {report['pass_rate']:.1%}",
        f"- Bootstrap: {report['n_bootstrap']} resamples over documents, seed {report['seed']}",
        "", "## Per-field", "",
        "| field | P | R | F1 | F1 95% CI | TP | FP | FN | " + " | ".join(BUCKETS) + " |",
        "|---|---|---|---|---|---|---|---|" + "---|" * len(BUCKETS),
    ]
    for name, s in report["fields"].items():
        out.append(
            f"| `{name}` | {_f(s['precision'])} | {_f(s['recall'])} | {_f(s['f1'])} | "
            f"{_ci(s['f1_ci95'])} | {s['tp']} | {s['fp']} | {s['fn']} | "
            + " | ".join(str(s["errors"][b]) for b in BUCKETS) + " |"
        )
    eb = report["error_buckets"]
    out += ["", "## Error buckets", "", "| bucket | count |", "|---|---|"]
    out += [f"| {b} | {eb[b]} |" for b in BUCKETS]
    if report["errors"]:
        out += ["", f"## Sample errors (first {max_errors})", "",
                "| doc | field | bucket | gold | pred |", "|---|---|---|---|---|"]
        for e in report["errors"][:max_errors]:
            g, p = (str(e["gold"]).replace("|", "\\|"), str(e["pred"]).replace("|", "\\|"))
            out.append(f"| {e['doc']} | `{e['field']}` | {e['bucket']} | {g} | {p} |")
    return "\n".join(out) + "\n"


def render_comparison(cmp: Mapping[str, Any], name_a: str = "A", name_b: str = "B") -> str:
    def row(label: str, d: Mapping[str, Any]) -> str:
        sign = "" if d["delta"] is None else f"{d['delta']:+.3f}"
        return f"| {label} | {_f(d['a'])} | {_f(d['b'])} | {sign} {_ci(d.get('delta_ci95'))} |"

    out = [
        f"# Run comparison: {name_a} vs {name_b}", "",
        f"{cmp['n_docs_compared']} paired documents. Delta = {name_b} - {name_a}; "
        "CI is a paired bootstrap over documents.", "",
        f"| metric | {name_a} | {name_b} | delta |", "|---|---|---|---|",
        row("micro F1", cmp["micro_f1"]), row("macro F1", cmp["macro_f1"]),
        row("pass rate", cmp["pass_rate"]),
    ]
    for f, d in cmp["fields"].items():
        out.append(row(f"`{f}` F1", d))
    fl = cmp["flips"]
    out += ["", f"Pass to fail: {len(fl['pass_to_fail'])} docs; fail to pass: "
            f"{len(fl['fail_to_pass'])} docs."]
    if fl["pass_to_fail"]:
        out.append(f"- pass to fail: {', '.join(fl['pass_to_fail'][:30])}")
    if fl["fail_to_pass"]:
        out.append(f"- fail to pass: {', '.join(fl['fail_to_pass'][:30])}")
    return "\n".join(out) + "\n"
