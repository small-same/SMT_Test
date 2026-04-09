"""SMT (Smart Money Technique) divergence detector.

ICT swing-based definition: given two correlated assets A and B,
compare the most recent two swing highs / lows. If one makes a new
HH/LL while the other fails to, that is SMT divergence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd

from .swing import Swing, detect_swings, last_two


Direction = Literal["bullish", "bearish"]


@dataclass(frozen=True)
class SMTEvent:
    timestamp: pd.Timestamp
    direction: Direction
    pivot_a: Swing
    pivot_b: Swing


def _bearish_from_highs(a: tuple[Swing, Swing], b: tuple[Swing, Swing]) -> bool:
    # A makes HH, B fails to confirm (lower high)  → bearish SMT
    return a[1].price > a[0].price and b[1].price < b[0].price


def _bullish_from_lows(a: tuple[Swing, Swing], b: tuple[Swing, Swing]) -> bool:
    # A makes LL, B fails to confirm (higher low)  → bullish SMT
    return a[1].price < a[0].price and b[1].price > b[0].price


def detect_smt(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    window: int = 5,
    correlation: str = "positive",
) -> list[SMTEvent]:
    """Walk the aligned series bar by bar and emit SMT events.

    For each bar index i, recompute swings on df_[:i+1] and check the
    last two highs / lows. Emits at most one event per bar (when a new
    divergence appears). Negative correlation flips B's comparison.
    """
    if not df_a.index.equals(df_b.index):
        raise ValueError("df_a and df_b must share the same index (call data.align).")

    events: list[SMTEvent] = []
    seen: set[tuple[pd.Timestamp, str]] = set()
    n = len(df_a)

    for i in range(window * 2 + 2, n):
        sa = detect_swings(df_a.iloc[: i + 1], window=window)
        sb = detect_swings(df_b.iloc[: i + 1], window=window)

        ah = last_two(sa, "high")
        bh = last_two(sb, "high")
        al = last_two(sa, "low")
        bl = last_two(sb, "low")

        ts = df_a.index[i]

        if ah and bh:
            a_pair, b_pair = ah, bh
            if correlation == "negative":
                b_pair = (Swing(b_pair[0].timestamp, -b_pair[0].price, "high"),
                          Swing(b_pair[1].timestamp, -b_pair[1].price, "high"))
            if _bearish_from_highs(a_pair, b_pair):
                key = (ah[1].timestamp, "bearish")
                if key not in seen:
                    seen.add(key)
                    events.append(SMTEvent(ts, "bearish", ah[1], bh[1]))

        if al and bl:
            a_pair, b_pair = al, bl
            if correlation == "negative":
                b_pair = (Swing(b_pair[0].timestamp, -b_pair[0].price, "low"),
                          Swing(b_pair[1].timestamp, -b_pair[1].price, "low"))
            if _bullish_from_lows(a_pair, b_pair):
                key = (al[1].timestamp, "bullish")
                if key not in seen:
                    seen.add(key)
                    events.append(SMTEvent(ts, "bullish", al[1], bl[1]))

    return events
