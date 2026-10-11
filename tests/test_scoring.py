import pytest
from hypothesis import given
from hypothesis import strategies as st

from extract_eval import Config, align_items, evaluate, make_matcher, score_document

CFG = Config.from_dict({
    "scalars": {"total": {"type": "numeric"}},
    "line_items": {"items": {
        "match_on": {"name": 1.0, "price": 0.5},
        "fields": {"name": "text", "qty": "numeric", "price": "numeric"},
    }},
})


ALL_FIELDS = Config.from_dict({"line_items": {"items": {
    "fields": {"name": "text", "qty": "numeric", "price": "numeric"}}}})


def test_hungarian_beats_positional_order():
    gold = {"items": [{"name": "latte", "qty": 2, "price": 9},
                      {"name": "tea", "qty": 1, "price": 3}]}
    pred = {"items": [{"name": "tea", "qty": 1, "price": 3},
                      {"name": "latte", "qty": 2, "price": 9}]}
    r = score_document("d", gold, pred, CFG)
    assert all(c[1] == 0 and c[2] == 0 for c in r.counts.values())
    assert r.counts["items.name"][0] == 2


def test_unmatched_items_become_fn_and_fp():
    gold = {"items": [{"name": "latte", "qty": 1, "price": 9},
                      {"name": "tea", "qty": 1, "price": 3}]}
    pred = {"items": [{"name": "latte", "qty": 1, "price": 9},
                      {"name": "cake", "qty": 5, "price": 40}]}
    r = score_document("d", gold, pred, CFG)
    assert r.counts["items.name"] == [1, 1, 1]
    buckets = sorted(e["bucket"] for e in r.errors if e["field"] == "items.name")
    assert buckets == ["extra", "missing"]


def test_error_buckets_scalar():
    cfg = Config.from_dict({"scalars": {
        "a": "exact", "b": "exact", "c": "exact", "d": "exact", "e": "exact"}})
    gold = {"a": "1,000", "b": "x", "c": None, "d": "keep", "e": ""}
    pred = {"a": "1000", "b": "y", "c": "extra", "d": "keep"}
    r = score_document("d", gold, pred, cfg)
    got = {e["field"]: e["bucket"] for e in r.errors}
    assert got == {"a": "format_only", "b": "mismatch", "c": "extra"}
    assert r.counts["d"] == [1, 0, 0] and r.counts["e"] == [0, 0, 0]
    missing = score_document("d", {"a": "1"}, {}, Config.from_dict({"scalars": {"a": "exact"}}))
    assert missing.errors[0]["bucket"] == "missing"


def test_single_dict_item_and_inferred_fields():
    cfg = Config.from_dict({"line_items": {"menu": {}}, "default": "text"})
    r = score_document("d", {"menu": {"nm": "A", "p": "1"}}, {"menu": [{"nm": "a", "p": "1"}]}, cfg)
    assert r.counts == {"menu.nm": [1, 0, 0], "menu.p": [1, 0, 0]}


def test_min_similarity_leaves_unrelated_unmatched():
    m = {"name": make_matcher("text")}
    assert align_items([{"name": "a"}], [{"name": "b"}], m, {"name": 1.0}, 0.3) == []
    assert align_items([{"name": "a"}], [{"name": "a"}], m, {"name": 1.0}, 0.3) == [(0, 0)]
    assert align_items([], [{"name": "a"}], m, {"name": 1.0}) == []


def test_evaluate_perfect_and_missing_prediction():
    gold = {"d1": {"total": "5", "items": [{"name": "a", "qty": 1, "price": 5}]},
            "d2": {"total": "7", "items": []}}
    rep = evaluate(gold, {"d1": gold["d1"]}, CFG, n_boot=50)
    assert rep["docs"]["d1"]["passed"] and not rep["docs"]["d2"]["passed"]
    assert rep["n_missing_predictions"] == 1
    assert rep["micro"]["recall"] == pytest.approx(4 / 5)
    assert rep["micro"]["precision"] == 1.0


@given(st.lists(st.tuples(st.text("abc", min_size=1, max_size=3), st.integers(0, 5)),
                min_size=0, max_size=6), st.randoms())
def test_perfect_under_any_permutation(items, rnd):
    gold = [{"name": n, "qty": q, "price": 1} for n, q in items]
    pred = list(gold)
    rnd.shuffle(pred)
    r = score_document("d", {"items": gold}, {"items": pred}, ALL_FIELDS)
    assert all(c[1] == 0 and c[2] == 0 for c in r.counts.values())


@given(st.lists(st.sampled_from("abcdef"), min_size=1, max_size=6, unique=True),
       st.lists(st.sampled_from("abcdef"), min_size=0, max_size=6, unique=True))
def test_counts_are_consistent(g, p):
    gold = {"items": [{"name": n, "qty": 1, "price": 1} for n in g]}
    pred = {"items": [{"name": n, "qty": 1, "price": 1} for n in p]}
    r = score_document("d", gold, pred, CFG)
    tp, fp, fn = r.counts["items.name"]
    assert tp + fn == len(g) and tp + fp == len(p) and tp == len(set(g) & set(p))
