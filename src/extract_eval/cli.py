"""Command line interface: ``extract-eval score|compare``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .config import Config
from .gate import gate_from_reports, render_gate_markdown, run_gate
from .metrics import evaluate, load_jsonl
from .report import render_comparison, render_markdown


def _score(a: argparse.Namespace) -> int:
    cfg = Config.from_yaml(a.config)
    report = evaluate(load_jsonl(a.gold), load_jsonl(a.pred), cfg, a.n_boot, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    md = Path(a.markdown) if a.markdown else out.with_suffix(".md")
    md.write_text(render_markdown(report))
    m = report["micro"]
    print(f"docs={report['n_docs']} micro_f1={m['f1']} macro_f1={report['macro']['f1']} "
          f"pass_rate={report['pass_rate']} -> {out}, {md}")
    if a.fail_under is not None and (m["f1"] is None or m["f1"] < a.fail_under):
        print(f"FAIL: micro F1 {m['f1']} < --fail-under {a.fail_under}", file=sys.stderr)
        return 1
    return 0


def _compare(a: argparse.Namespace) -> int:
    base, cand = a.baseline or a.a, a.candidate or a.b
    if not base or not cand:
        print("error: give BASELINE and CANDIDATE (or --a/--b)", file=sys.stderr)
        return 2
    jsonl = base.endswith(".jsonl") or cand.endswith(".jsonl")
    if jsonl:
        if not (a.gold and a.config):
            print("error: comparing JSONL predictions needs --gold and --config", file=sys.stderr)
            return 2
        gold = load_jsonl(a.gold)
        cfg = Config.from_yaml(a.config)
        res = run_gate(gold, load_jsonl(base), load_jsonl(cand), cfg, a.n_boot, a.seed,
                       a.min_drop, a.significance, a.scope)
    else:
        ra, rb = (json.loads(Path(p).read_text()) for p in (base, cand))
        res = gate_from_reports(ra, rb, a.n_boot, a.seed, a.min_drop, a.significance, a.scope)
    cmp = res.comparison
    names = (Path(base).stem, Path(cand).stem)
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({**cmp, "regressions": [asdict(r) for r in res.regressions]},
                                  indent=2))
        md_path = Path(a.markdown) if a.markdown else out.with_suffix(".md")
        md_path.write_text(render_comparison(cmp, *names))
    md = render_gate_markdown(res, *names)
    if a.summary:
        with open(a.summary, "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    if a.gate_markdown:
        Path(a.gate_markdown).write_text(md)
    print(f"micro_f1 delta={cmp['micro_f1']['delta']} "
          f"flips: -{len(cmp['flips']['pass_to_fail'])} +{len(cmp['flips']['fail_to_pass'])} "
          f"regressions={len(res.regressions)}")
    for r in res.regressions:
        print(f"REGRESSION {r.metric}: {r.baseline} -> {r.candidate} "
              f"(delta {r.delta:+.4f}, 95% CI {r.ci95})", file=sys.stderr)
    return 1 if res.regressed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="extract-eval", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="score predictions against gold")
    s.add_argument("--gold", required=True, help="gold JSONL ({id, data})")
    s.add_argument("--pred", required=True, help="predictions JSONL ({id, data})")
    s.add_argument("--config", required=True, help="YAML config")
    s.add_argument("--out", required=True, help="report.json path (report.md written next to it)")
    s.add_argument("--markdown", help="markdown path (default: --out with .md)")
    s.add_argument("--fail-under", type=float, help="exit 1 if micro F1 is below this")
    s.add_argument("--n-boot", type=int, default=1000)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=_score)
    c = sub.add_parser(
        "compare",
        help="regression gate: compare BASELINE and CANDIDATE (predictions JSONL or report.json)",
        description="Exit 1 when a metric significantly regressed, 2 on usage errors.")
    c.add_argument("baseline", nargs="?", help="baseline predictions .jsonl or report .json")
    c.add_argument("candidate", nargs="?", help="candidate predictions .jsonl or report .json")
    c.add_argument("--a", help="baseline report.json (legacy spelling)")
    c.add_argument("--b", help="candidate report.json (legacy spelling)")
    c.add_argument("--gold", help="gold JSONL (required for prediction JSONL inputs)")
    c.add_argument("--config", help="YAML config (required for prediction JSONL inputs)")
    c.add_argument("--out", help="write comparison JSON here (markdown next to it)")
    c.add_argument("--markdown", help="markdown path for the long comparison table")
    c.add_argument("--summary", help="append gate markdown here, e.g. $GITHUB_STEP_SUMMARY")
    c.add_argument("--gate-markdown", help="write gate markdown to this file (PR comment body)")
    c.add_argument("--min-drop", type=float, default=0.0,
                   help="ignore F1 drops smaller than this (default 0)")
    c.add_argument("--significance", choices=["ci", "none"], default="ci",
                   help="ci: require the 95%% CI of the delta below 0; none: any drop counts")
    c.add_argument("--scope", choices=["any", "micro", "fields"], default="any")
    c.add_argument("--n-boot", type=int, default=1000)
    c.add_argument("--seed", type=int, default=0)
    c.set_defaults(fn=_compare)
    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
