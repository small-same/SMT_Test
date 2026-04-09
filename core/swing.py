"""Fractal-based swing high / swing low detection.

A bar at index i is a swing high if its high is the strict maximum over
the window [i-w, i+w] (exclusive at center). Symmetric for swing low.
Pure functions, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd


SwingType = Literal["high", "low"]


@dataclass(frozen=True)
class Swing:
    timestamp: pd.Timestamp
    price: float
    type: SwingType


def detect_swings(df: pd.DataFrame, window: int = 5) -> list[Swing]:
    """Detect swing highs and lows using a fractal window.

    Parameters
    ----------
    df : DataFrame with 'high' and 'low' columns, indexed by timestamp.
    window : half-window size. A pivot needs `window` bars on each side.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    idx = df.index
    out: list[Swing] = []
    n = len(df)
    for i in range(window, n - window):
        lh = highs[i - window : i]
        rh = highs[i + 1 : i + 1 + window]
        if highs[i] > lh.max() and highs[i] > rh.max():
            out.append(Swing(idx[i], float(highs[i]), "high"))
            continue
        ll = lows[i - window : i]
        rl = lows[i + 1 : i + 1 + window]
        if lows[i] < ll.min() and lows[i] < rl.min():
            out.append(Swing(idx[i], float(lows[i]), "low"))
    return out


def last_two(swings: list[Swing], kind: SwingType) -> tuple[Swing, Swing] | None:
    """Return the (older, newer) two most recent swings of given kind."""
    filtered = [s for s in swings if s.type == kind]
    if len(filtered) < 2:
        return None
    return filtered[-2], filtered[-1]
