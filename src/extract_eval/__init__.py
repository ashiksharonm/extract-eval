"""extract-eval: evaluate structured extraction against ground truth."""

__version__ = "0.1.0"

from .compare import compare_reports
from .config import Config, LineItemSpec
from .matchers import Matcher, make_matcher, parse_date, parse_number
from .metrics import assert_min_scores, evaluate, load_jsonl
from .scoring import align_items, score_document

__all__ = [
    "Config", "LineItemSpec", "Matcher", "align_items", "assert_min_scores", "compare_reports",
    "evaluate", "load_jsonl", "make_matcher", "parse_date", "parse_number", "score_document",
]
