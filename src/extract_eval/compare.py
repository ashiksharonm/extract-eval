"""Compare two scored runs (paired by document id)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .metrics import _ci, _micro_macro, _stack


def compare_reports(
    a: Mapping[str, Any], b: Mapping[str, Any], n_boot: int = 1000, seed: int = 0
) -> dict[str, Any]:
    """Per-field deltas (b - a), paired-bootstrap CI on micro F1 delta, and pass/fail flips."""
    ids = [i for i in a["docs"] if i in b["docs"]]
    fields = sorted(set(a["fields"]) | set(b["fields"]))
    flips = {"pass_to_fail": [], "fail_to_pass": []}
    for i in ids:
        pa, pb = a["docs"][i]["passed"], b["docs"][i]["passed"]
        if pa and not pb:
            flips["pass_to_fail"].append(i)
        elif pb and not pa:
            flips["fail_to_pass"].append(i)

    def delta(x: float | None, y: float | None) -> float | None:
        return None if x is None or y is None else round(y - x, 4)

    per_field = {
        f: {"a": a["fields"].get(f, {}).get("f1"), "b": b["fields"].get(f, {}).get("f1"),
            "delta": delta(a["fields"].get(f, {}).get("f1"), b["fields"].get(f, {}).get("f1"))}
        for f in fields
    }
    arr_a = _stack([a["docs"][i]["fields"] for i in ids], fields)
    arr_b = _stack([b["docs"][i]["fields"] for i in ids], fields)
    micro_ci = macro_ci = None
    if n_boot and ids:
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(ids), size=(n_boot, len(ids)))
        sa, sb = arr_a[idx].sum(axis=1), arr_b[idx].sum(axis=1)
        mia, maa = _micro_macro(sa[..., 0], sa[..., 1], sa[..., 2])
        mib, mab = _micro_macro(sb[..., 0], sb[..., 1], sb[..., 2])
        micro_ci, macro_ci = _ci(mib - mia), _ci(mab - maa)
    return {
        "n_docs_compared": len(ids),
        "micro_f1": {"a": a["micro"]["f1"], "b": b["micro"]["f1"],
                     "delta": delta(a["micro"]["f1"], b["micro"]["f1"]),
                     "delta_ci95": micro_ci},
        "macro_f1": {"a": a["macro"]["f1"], "b": b["macro"]["f1"],
                     "delta": delta(a["macro"]["f1"], b["macro"]["f1"]),
                     "delta_ci95": macro_ci},
        "pass_rate": {"a": a["pass_rate"], "b": b["pass_rate"],
                      "delta": delta(a["pass_rate"], b["pass_rate"])},
        "fields": per_field,
        "flips": flips,
    }

