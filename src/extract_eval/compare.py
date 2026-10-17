"""Compare two scored runs (paired by document id)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .metrics import _ci, _f1_vec, _micro_macro, _stack


def compare_reports(
    a: Mapping[str, Any], b: Mapping[str, Any], n_boot: int = 1000, seed: int = 0
) -> dict[str, Any]:
    """Per-field deltas (b - a), paired-bootstrap CI on micro F1 delta, and pass/fail flips."""
    ids = [i for i in a["docs"] if i in b["docs"]]
    fields = sorted(set(a["fields"]) | set(b["fields"]))
    flips: dict[str, list[str]] = {"pass_to_fail": [], "fail_to_pass": []}
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
    field_ci: dict[str, list[float | None]] = {}
    if n_boot and ids:
        rng = np.random.default_rng(seed)
        mi_d, ma_d, f_d = [], [], []
        for start in range(0, n_boot, 100):  # chunked to bound memory on large sets
            idx = rng.integers(0, len(ids), size=(min(100, n_boot - start), len(ids)))
            sa, sb = arr_a[idx].sum(axis=1), arr_b[idx].sum(axis=1)
            mia, maa = _micro_macro(sa[..., 0], sa[..., 1], sa[..., 2])
            mib, mab = _micro_macro(sb[..., 0], sb[..., 1], sb[..., 2])
            mi_d.append(mib - mia)
            ma_d.append(mab - maa)
            f_d.append(_f1_vec(sb[..., 0], sb[..., 1], sb[..., 2])
                       - _f1_vec(sa[..., 0], sa[..., 1], sa[..., 2]))
        micro_ci, macro_ci = _ci(np.concatenate(mi_d)), _ci(np.concatenate(ma_d))
        fd = np.concatenate(f_d)
        field_ci = {f: _ci(fd[:, k]) for k, f in enumerate(fields)}
    for f, d in per_field.items():
        d["delta_ci95"] = field_ci.get(f)
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

