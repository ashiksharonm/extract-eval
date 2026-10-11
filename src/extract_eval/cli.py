"""Command line interface: ``extract-eval score|compare``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compare import compare_reports
from .config import Config
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
    ra, rb = (json.loads(Path(p).read_text()) for p in (a.a, a.b))
    cmp = compare_reports(ra, rb, a.n_boot, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cmp, indent=2))
    md = Path(a.markdown) if a.markdown else out.with_suffix(".md")
    md.write_text(render_comparison(cmp, Path(a.a).stem, Path(a.b).stem))
    print(f"micro_f1 delta={cmp['micro_f1']['delta']} flips: "
          f"-{len(cmp['flips']['pass_to_fail'])} +{len(cmp['flips']['fail_to_pass'])} -> {out}")
    return 0


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
    c = sub.add_parser("compare", help="compare two report.json files")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--markdown")
    c.add_argument("--n-boot", type=int, default=1000)
    c.add_argument("--seed", type=int, default=0)
    c.set_defaults(fn=_compare)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
