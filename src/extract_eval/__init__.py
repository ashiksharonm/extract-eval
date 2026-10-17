"""extract-eval: evaluate structured extraction against ground truth."""

__version__ = "0.2.0"

from .compare import compare_reports
from .config import Config, LineItemSpec
from .gate import GateResult, Regression, find_regressions, run_gate
from .matchers import Matcher, make_matcher, parse_date, parse_number
from .metrics import assert_min_scores, evaluate, load_jsonl
from .scoring import align_items, score_document

__all__ = [
    "Config", "GateResult", "LineItemSpec", "Matcher", "Regression", "align_items",
    "assert_min_scores", "compare_reports", "evaluate", "find_regressions", "load_jsonl",
    "make_matcher", "parse_date", "parse_number", "run_gate", "score_document",
]
