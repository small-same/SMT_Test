"""Unit tests using synthetic data."""
import pandas as pd
import pytest

from core.swing import detect_swings, last_two
from core.smt_detector import detect_smt


def _make(highs, lows):
    idx = pd.date_range("2024-01-01", periods=len(highs), freq="D")
    return pd.DataFrame({"high": highs, "low": lows, "close": highs}, index=idx)


def test_detect_swing_high_and_low():
    highs = [1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3]
    lows = [h - 0.5 for h in highs]
    df = _make(highs, lows)
    swings = detect_swings(df, window=2)
    kinds = [s.type for s in swings]
    assert "high" in kinds
    assert "low" in kinds


def test_bearish_smt():
    # A: HH, B: LH  → bearish SMT
    a_highs = [1, 3, 1, 5, 1, 1, 1]   # swing highs at idx 1 (3) and 3 (5) → HH
    a_lows = [0, 0, 0, 0, 0, 0, 0]
    b_highs = [1, 4, 1, 2, 1, 1, 1]   # swing highs 4 then 2 → LH
    b_lows = [0, 0, 0, 0, 0, 0, 0]
    a = _make(a_highs, a_lows)
    b = _make(b_highs, b_lows)
    events = detect_smt(a, b, window=1)
    assert any(e.direction == "bearish" for e in events)


def test_bullish_smt():
    # A: LL, B: HL  → bullish SMT
    a_highs = [10] * 7
    a_lows = [9, 7, 9, 5, 9, 9, 9]    # swing lows 7 then 5 → LL
    b_highs = [10] * 7
    b_lows = [9, 6, 9, 8, 9, 9, 9]    # swing lows 6 then 8 → HL
    a = _make(a_highs, a_lows)
    b = _make(b_highs, b_lows)
    events = detect_smt(a, b, window=1)
    assert any(e.direction == "bullish" for e in events)


def test_no_smt_when_aligned():
    a_highs = [1, 3, 1, 5, 1, 1, 1]
    a_lows = [0] * 7
    b_highs = [1, 3, 1, 5, 1, 1, 1]   # both HH
    b_lows = [0] * 7
    events = detect_smt(_make(a_highs, a_lows), _make(b_highs, b_lows), window=1)
    assert not any(e.direction == "bearish" for e in events)


def test_last_two():
    df = _make([1, 3, 1, 5, 1, 4, 1], [0] * 7)
    sw = detect_swings(df, window=1)
    pair = last_two(sw, "high")
    assert pair is not None
    assert pair[1].price >= 4
