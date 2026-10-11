"""Field matchers: decide whether a predicted value equals the gold value."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from rapidfuzz import fuzz

_CURRENCY_JUNK = re.compile(r"[^\d.,\-()+eE]")


def is_missing(value: Any) -> bool:
    """None, empty string and whitespace-only strings count as 'no value'."""
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_text(value: Any, strip_punct: bool = True) -> str:
    s = unicodedata.normalize("NFKC", str(value)).casefold()
    if strip_punct:
        s = "".join(" " if unicodedata.category(c).startswith(("P", "S")) else c for c in s)
    return " ".join(s.split())


def parse_number(value: Any, locale: str = "us") -> float | None:
    """Parse '1,234.50', '$12', '(3.00)', '12-' and (locale='eu') '1.234,50' to a float.

    locale: 'us' (',' thousands, '.' decimal), 'eu' ('.' thousands, ',' decimal) or
    'auto' (the right-most separator is the decimal mark if both occur; a lone
    separator followed by exactly three digits is treated as a thousands mark).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    s = _CURRENCY_JUNK.sub("", str(value)).strip()
    if not s:
        return None
    neg = (s.startswith("(") and s.endswith(")")) or s.startswith("-") or s.endswith("-")
    s = s.strip("()-+")
    if not s or not re.search(r"\d", s):
        return None
    dec, thou = ".", ","
    if locale == "eu":
        dec, thou = ",", "."
    elif locale == "auto":
        if "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            thou = "." if dec == "," else ","
        else:
            sep = "," if "," in s else "." if "." in s else None
            if sep:
                tail = s.rsplit(sep, 1)[1]
                if s.count(sep) > 1 or len(tail) == 3:
                    thou, dec = sep, "." if sep == "," else ","
                else:
                    dec, thou = sep, "." if sep == "," else ","
    s = s.replace(thou, "")
    if s.count(dec) > 1:
        return None
    s = s.replace(dec, ".")
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if neg else n


_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
    "%B %d %Y", "%b %d %Y", "%Y%m%d",
)
_DAYFIRST = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y")
_MONTHFIRST = ("%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y")


def parse_date(value: Any, dayfirst: bool = True) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    s = " ".join(str(value).split())
    s = re.split(r"[T ](?=\d{1,2}:\d{2})", s)[0]
    order = (*_DATE_FORMATS, *(_DAYFIRST + _MONTHFIRST if dayfirst else _MONTHFIRST + _DAYFIRST))
    for fmt in order:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class Matcher:
    """Scores a (gold, pred) pair in [0, 1]; ``match`` is the boolean decision."""

    type: str = "text"
    abs_tol: float = 0.0
    rel_tol: float = 0.0
    locale: str = "us"
    dayfirst: bool = True
    threshold: float = 0.85
    scorer: str = "token_sort_ratio"
    strip_punct: bool = True

    def score(self, gold: Any, pred: Any) -> float:
        t = self.type
        if t == "exact":
            return float(gold == pred)
        if t == "text":
            return float(
                normalize_text(gold, self.strip_punct) == normalize_text(pred, self.strip_punct)
            )
        if t == "numeric":
            g, p = parse_number(gold, self.locale), parse_number(pred, self.locale)
            if g is None or p is None:
                return float(normalize_text(gold) == normalize_text(pred))
            return float(abs(g - p) <= max(self.abs_tol, self.rel_tol * abs(g)) + 1e-12)
        if t == "date":
            g, p = parse_date(gold, self.dayfirst), parse_date(pred, self.dayfirst)
            if g is None or p is None:
                return float(normalize_text(gold) == normalize_text(pred))
            return float(g == p)
        if t == "fuzzy":
            fn = getattr(fuzz, self.scorer)
            return fn(normalize_text(gold), normalize_text(pred)) / 100.0
        raise ValueError(f"unknown matcher type: {t!r}")

    def match(self, gold: Any, pred: Any) -> bool:
        s = self.score(gold, pred)
        return s >= self.threshold if self.type == "fuzzy" else s >= 1.0

    def loosely_equal(self, gold: Any, pred: Any) -> bool:
        """True when values differ only in formatting (case, punctuation, separators, dates)."""
        if normalize_text(gold) == normalize_text(pred):
            return True
        for loc in ("us", "eu"):
            g, p = parse_number(gold, loc), parse_number(pred, loc)
            if g is not None and p is not None and g == p:
                return True
        g, p = parse_date(gold), parse_date(pred)
        return g is not None and g == p


MATCHER_TYPES = ("exact", "text", "numeric", "date", "fuzzy")


def make_matcher(spec: str | dict[str, Any] | Matcher | None) -> Matcher:
    if isinstance(spec, Matcher):
        return spec
    if spec is None:
        return Matcher()
    if isinstance(spec, str):
        spec = {"type": spec}
    spec = dict(spec)
    if spec.get("type", "text") not in MATCHER_TYPES:
        raise ValueError(f"unknown matcher type {spec['type']!r}; choose from {MATCHER_TYPES}")
    return Matcher(**spec)
