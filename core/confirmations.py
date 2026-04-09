"""Market structure confirmations: BOS and CHOCH.

BOS (Break of Structure): price closes beyond the last swing high (bullish)
or below the last swing low (bearish), confirming trend continuation.

CHOCH (Change of Character): first BOS against the prevailing trend —
signals a potential reversal and is the preferred confirmation after SMT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd

from .swing import Swing


Kind = Literal["BOS_up", "BOS_down", "CHOCH_up", "CHOCH_down"]


@dataclass(frozen=True)
class StructureEvent:
    timestamp: pd.Timestamp
    kind: Kind
    level: float


def detect_structure(df: pd.DataFrame, swings: list[Swing]) -> list[StructureEvent]:
    """Scan bars after each swing; emit BOS/CHOCH when close breaks it."""
    events: list[StructureEvent] = []
    last_trend: str | None = None  # "up" or "down"
    closes = df["close"]

    for idx, s in enumerate(swings):
        future = closes.loc[closes.index > s.timestamp]
        if future.empty:
            continue
        if s.type == "high":
            broken = future[future > s.price]
            if not broken.empty:
                ts = broken.index[0]
                kind: Kind = "CHOCH_up" if last_trend == "down" else "BOS_up"
                events.append(StructureEvent(ts, kind, s.price))
                last_trend = "up"
        else:
            broken = future[future < s.price]
            if not broken.empty:
                ts = broken.index[0]
                kind = "CHOCH_down" if last_trend == "up" else "BOS_down"
                events.append(StructureEvent(ts, kind, s.price))
                last_trend = "down"

    events.sort(key=lambda e: e.timestamp)
    return events
