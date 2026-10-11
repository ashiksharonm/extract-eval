"""Aggregation: micro/macro P/R/F1, per-doc scores, bootstrap CIs, gating."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .config import Config
from .scoring import BUCKETS, DocResult, score_document


def prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    """Precision, recall, F1; NaN when undefined (no gold and no predictions)."""
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else float("nan")
    return p, r, f


def _f1_vec(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray) -> np.ndarray:
    den = 2 * tp + fp + fn
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, 2 * tp / den, np.nan)


def _micro_macro(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """tp/fp/fn have shape (..., fields). Returns (micro_f1, macro_f1) over the leading dims."""
    micro = _f1_vec(tp.sum(-1), fp.sum(-1), fn.sum(-1))
    per_field = _f1_vec(tp, fp, fn)
    with np.errstate(all="ignore"):
        macro = np.nanmean(per_field, axis=-1)
    return micro, macro


def _ci(samples: np.ndarray, alpha: float = 0.05) -> list[float | None]:
    if np.all(np.isnan(samples)):
        return [None, None]
    lo, hi = np.nanpercentile(samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return [round(float(lo), 4), round(float(hi), 4)]


def _num(x: float) -> float | None:
    return None if x != x else round(float(x), 4)


def _stack(doc_counts: list[dict[str, list[int]]], fields: list[str]) -> np.ndarray:
    arr = np.zeros((len(doc_counts), len(fields), 3))
    for d, counts in enumerate(doc_counts):
        for k, f in enumerate(fields):
            arr[d, k] = counts.get(f, (0, 0, 0))
    return arr


def bootstrap(arr: np.ndarray, n_boot: int, seed: int, chunk: int = 200) -> dict[str, np.ndarray]:
    """Resample documents with replacement. arr has shape (docs, fields, 3)."""
    rng = np.random.default_rng(seed)
    n = arr.shape[0]
    micro, macro, per_field = [], [], []
    for start in range(0, n_boot, chunk):
        b = min(chunk, n_boot - start)
        idx = rng.integers(0, n, size=(b, n))
        s = arr[idx].sum(axis=1)  # (b, fields, 3)
        mi, ma = _micro_macro(s[..., 0], s[..., 1], s[..., 2])
        micro.append(mi)
        macro.append(ma)
        per_field.append(_f1_vec(s[..., 0], s[..., 1], s[..., 2]))
    return {"micro": np.concatenate(micro), "macro": np.concatenate(macro),
            "fields": np.concatenate(per_field)}


def build_report(
    results: list[DocResult], cfg: Config, n_boot: int = 1000, seed: int = 0
) -> dict[str, Any]:
    fields = sorted({f for r in results for f in r.counts})
    arr = _stack([r.counts for r in results], fields)
    tot = arr.sum(axis=0)  # (fields, 3)
    mp, mr, mf = prf(*tot.sum(axis=0))
    pf = _f1_vec(tot[:, 0], tot[:, 1], tot[:, 2])
    macro_f1 = float(np.nanmean(pf)) if np.any(~np.isnan(pf)) else float("nan")
    boot = bootstrap(arr, n_boot, seed) if n_boot and len(results) else None

    docs: dict[str, Any] = {}
    for r, a in zip(results, arr, strict=True):
        t = a.sum(axis=0)
        f1 = prf(*t)[2]
        f1 = 1.0 if f1 != f1 else f1
        docs[r.doc_id] = {
            "tp": int(t[0]), "fp": int(t[1]), "fn": int(t[2]), "f1": round(f1, 4),
            "passed": bool(f1 >= cfg.doc_pass_f1 - 1e-12), "fields": r.counts,
        }
    errors = [e for r in results for e in r.errors]
    by_bucket = Counter(e["bucket"] for e in errors)
    fld: dict[str, Any] = {}
    for k, f in enumerate(fields):
        p, rc, f1 = prf(*tot[k])
        fb = Counter(e["bucket"] for e in errors if e["field"] == f)
        fld[f] = {
            "tp": int(tot[k, 0]), "fp": int(tot[k, 1]), "fn": int(tot[k, 2]),
            "precision": _num(p), "recall": _num(rc), "f1": _num(f1),
            "f1_ci95": _ci(boot["fields"][:, k]) if boot else None,
            "errors": {b: fb.get(b, 0) for b in BUCKETS},
        }
    return {
        "extract_eval_version": __version__,
        "n_docs": len(results),
        "n_bootstrap": n_boot, "seed": seed,
        "micro": {"precision": _num(mp), "recall": _num(mr), "f1": _num(mf),
                  "f1_ci95": _ci(boot["micro"]) if boot else None},
        "macro": {"f1": _num(macro_f1), "f1_ci95": _ci(boot["macro"]) if boot else None},
        "pass_rate": round(sum(d["passed"] for d in docs.values()) / max(len(docs), 1), 4),
        "doc_pass_f1": cfg.doc_pass_f1,
        "error_buckets": {b: by_bucket.get(b, 0) for b in BUCKETS},
        "fields": fld,
        "docs": docs,
        "errors": errors,
    }


def load_jsonl(path: str | Path) -> dict[str, dict[str, Any]]:
    """Read records shaped ``{"id": ..., "data": {...}}`` (or the doc fields next to ``id``)."""
    out: dict[str, dict[str, Any]] = {}
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        doc_id = str(rec.get("id", n))
        out[doc_id] = rec["data"] if isinstance(rec.get("data"), dict) else {
            k: v for k, v in rec.items() if k != "id"
        }
    return out


def evaluate(
    gold: Mapping[str, dict[str, Any]],
    pred: Mapping[str, dict[str, Any]],
    config: Config | dict[str, Any],
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    """Score predictions against gold. Gold docs with no prediction are scored as all-missing."""
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    results = [score_document(i, g, pred.get(i, {}), cfg) for i, g in gold.items()]
    report = build_report(results, cfg, n_boot, seed)
    report["n_missing_predictions"] = sum(1 for i in gold if i not in pred)
    report["n_extra_predictions"] = sum(1 for i in pred if i not in gold)
    return report


_ALIASES = {"micro_f1": ("micro", "f1"), "micro_precision": ("micro", "precision"),
            "micro_recall": ("micro", "recall"), "macro_f1": ("macro", "f1")}


def metric_value(report: Mapping[str, Any], name: str) -> float | None:
    if name in _ALIASES:
        a, b = _ALIASES[name]
        return report[a][b]
    if name == "pass_rate":
        return report["pass_rate"]
    if name in report["fields"]:
        return report["fields"][name]["f1"]
    raise KeyError(f"unknown metric {name!r}")


def assert_min_scores(report: Mapping[str, Any], thresholds: Mapping[str, float]) -> None:
    """Raise AssertionError listing every metric below its threshold (for CI gating).

    Keys: micro_f1, micro_precision, micro_recall, macro_f1, pass_rate, or a field name
    (e.g. "total.total_price" or "menu.price") which gates that field's F1.
    """
    failures = []
    for name, minimum in thresholds.items():
        v = metric_value(report, name)
        if v is None or v < minimum:
            failures.append(f"{name}: {v} < {minimum}")
    if failures:
        raise AssertionError("scores below threshold: " + "; ".join(failures))


def iter_metric_names(report: Mapping[str, Any]) -> Iterable[str]:
    yield from _ALIASES
    yield "pass_rate"
    yield from report["fields"]
