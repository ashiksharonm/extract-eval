import pytest
from hypothesis import given
from hypothesis import strategies as st

from extract_eval import make_matcher, parse_date, parse_number


@pytest.mark.parametrize(
    "raw,expected",
    [("1,234.50", 1234.5), ("$12", 12.0), ("(3.00)", -3.0), ("12-", -12.0), (7, 7.0),
     ("Rp 1,346,000", 1346000.0), ("abc", None), ("", None), (None, None)],
)
def test_parse_number_us(raw, expected):
    assert parse_number(raw) == expected


def test_parse_number_locales():
    assert parse_number("1.234,50", "eu") == 1234.5
    assert parse_number("45.000", "eu") == 45000.0
    assert parse_number("1.234,50", "auto") == 1234.5
    assert parse_number("1,234.50", "auto") == 1234.5
    assert parse_number("12,5", "auto") == 12.5
    assert parse_number("1,234", "auto") == 1234.0


def test_parse_date():
    from datetime import date

    assert parse_date("2026-03-04") == date(2026, 3, 4)
    assert parse_date("04/03/2026") == date(2026, 3, 4)
    assert parse_date("04/03/2026", dayfirst=False) == date(2026, 4, 3)
    assert parse_date("4 Mar 2026") == date(2026, 3, 4)
    assert parse_date("not a date") is None


def test_matchers():
    assert make_matcher("exact").match("a", "a") and not make_matcher("exact").match("a", "A")
    assert make_matcher("text").match("  Hello,  WORLD ", "hello world")
    num = make_matcher({"type": "numeric", "abs_tol": 0.01})
    assert num.match("$12.00", 12.005) and not num.match("12", "12.5")
    assert make_matcher({"type": "numeric", "rel_tol": 0.1}).match(100, 109)
    assert make_matcher("date").match("2026-03-04", "04/03/2026")
    fz = make_matcher({"type": "fuzzy", "threshold": 0.85})
    assert fz.match("Iced Latte", "Iced Lattes") and not fz.match("Iced Latte", "Tea")


def test_loose_equality_flags_format_only():
    exact = make_matcher("exact")
    assert not exact.match("1,234.50", "1234.50") and exact.loosely_equal("1,234.50", "1234.50")
    assert not exact.loosely_equal("12", "13")


def test_unknown_type():
    with pytest.raises(ValueError):
        make_matcher("bogus")


@given(st.floats(min_value=-1e9, max_value=1e9, allow_nan=False))
def test_numeric_matcher_reflexive(x):
    assert make_matcher("numeric").match(x, x)
    assert make_matcher("numeric").match(f"{x:,.2f}", round(x, 2))
