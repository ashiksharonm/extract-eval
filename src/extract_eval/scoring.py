"""Per-document scoring: scalar fields plus Hungarian-aligned line items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from .config import Config, LineItemSpec
from .matchers import Matcher, is_missing

BUCKETS = ("missing", "extra", "mismatch", "format_only")


@dataclass
class DocResult:
    doc_id: str
    counts: dict[str, list[int]] = field(default_factory=dict)  # field -> [tp, fp, fn]
    errors: list[dict[str, Any]] = field(default_factory=list)

    def _add(self, name: str, tp: int = 0, fp: int = 0, fn: int = 0) -> None:
        c = self.counts.setdefault(name, [0, 0, 0])
        c[0] += tp
        c[1] += fp
        c[2] += fn

    def _error(self, name: str, bucket: str, gold: Any, pred: Any, item: Any = None) -> None:
        e = {"doc": self.doc_id, "field": name, "bucket": bucket, "gold": gold, "pred": pred}
        if item is not None:
            e["item"] = item
        self.errors.append(e)


def get_path(data: Any, path: str) -> Any:
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_items(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        value = [value]
    return [v for v in value if isinstance(v, dict)]


def _score_pair(res: DocResult, name: str, m: Matcher, g: Any, p: Any, item: Any = None) -> None:
    gm, pm = is_missing(g), is_missing(p)
    if gm and pm:
        return
    if pm:
        res._add(name, fn=1)
        res._error(name, "missing", g, p, item)
    elif gm:
        res._add(name, fp=1)
        res._error(name, "extra", g, p, item)
    elif m.match(g, p):
        res._add(name, tp=1)
    else:
        res._add(name, fp=1, fn=1)
        res._error(name, "format_only" if m.loosely_equal(g, p) else "mismatch", g, p, item)


def align_items(
    gold: list[dict[str, Any]],
    pred: list[dict[str, Any]],
    matchers: dict[str, Matcher],
    weights: dict[str, float],
    min_similarity: float = 0.3,
) -> list[tuple[int, int]]:
    """Optimal one-to-one pairing of gold and predicted items (Hungarian algorithm).

    Similarity of a pair is the weighted mean of per-field match scores over the fields
    where at least one side has a value. Pairs under ``min_similarity`` are left unmatched.
    """
    if not gold or not pred:
        return []
    sim = np.zeros((len(gold), len(pred)))
    for i, g in enumerate(gold):
        for j, p in enumerate(pred):
            num = den = 0.0
            for f, w in weights.items():
                gv, pv = g.get(f), p.get(f)
                if is_missing(gv) and is_missing(pv):
                    continue
                den += w
                if not (is_missing(gv) or is_missing(pv)):
                    num += w * matchers[f].score(gv, pv)
            sim[i, j] = num / den if den else 0.0
    rows, cols = linear_sum_assignment(-sim)
    return [(int(r), int(c)) for r, c in zip(rows, cols, strict=True)
            if sim[r, c] >= min_similarity]


def _score_items(res: DocResult, spec: LineItemSpec, cfg: Config, gold: Any, pred: Any) -> None:
    g_items, p_items = _as_items(gold), _as_items(pred)
    names = list(spec.fields) or sorted({k for it in g_items for k in it})
    matchers = {n: spec.fields.get(n, cfg.default_matcher) for n in names}
    weights = dict(spec.match_on) or {n: 1.0 for n in names}
    for n in weights:
        matchers.setdefault(n, cfg.default_matcher)
    pairs = align_items(g_items, p_items, matchers, weights, spec.min_similarity)
    used_g = {i for i, _ in pairs}
    used_p = {j for _, j in pairs}
    for n in matchers:
        res.counts.setdefault(f"{spec.path}.{n}", [0, 0, 0])
    for i, j in pairs:
        for n, m in matchers.items():
            _score_pair(res, f"{spec.path}.{n}", m, g_items[i].get(n), p_items[j].get(n), i)
    for i, g in enumerate(g_items):
        if i not in used_g:
            for n in matchers:
                if not is_missing(g.get(n)):
                    res._add(f"{spec.path}.{n}", fn=1)
                    res._error(f"{spec.path}.{n}", "missing", g.get(n), None, i)
    for j, p in enumerate(p_items):
        if j not in used_p:
            for n in matchers:
                if not is_missing(p.get(n)):
                    res._add(f"{spec.path}.{n}", fp=1)
                    res._error(f"{spec.path}.{n}", "extra", None, p.get(n), j)


def score_document(
    doc_id: str, gold: dict[str, Any], pred: dict[str, Any], cfg: Config
) -> DocResult:
    res = DocResult(doc_id)
    for path, m in cfg.scalars.items():
        res.counts.setdefault(path, [0, 0, 0])
        _score_pair(res, path, m, get_path(gold, path), get_path(pred, path))
    for path, spec in cfg.line_items.items():
        _score_items(res, spec, cfg, get_path(gold, path), get_path(pred, path))
    return res
