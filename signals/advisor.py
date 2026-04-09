"""Combine SMT detection with BOS/CHOCH confirmation to produce
actionable trade signals with entry/stop/target prices.

This module does NOT place orders. It transforms raw detector output
into a list of `TradeSignal` objects that a CLI (or any caller) can
present to the user for discretionary decision making.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd

from core.swing import detect_swings
from core.smt_detector import detect_smt, SMTEvent
from core.confirmations import detect_structure, StructureEvent


Direction = Literal["bullish", "bearish"]
Status = Literal["actionable", "pending_confirmation", "expired"]


@dataclass(frozen=True)
class TradeSignal:
    timestamp: pd.Timestamp     # SMT event bar
    direction: Direction
    pivot_price: float          # triggering swing pivot on primary
    entry: float                # suggested entry (close of event bar)
    stop: float                 # just beyond pivot (±0.5%)
    target: float               # entry ± risk * rr_ratio
    risk_per_unit: float
    rr_ratio: float
    confirmed: bool             # BOS/CHOCH in the SMT direction after event
    status: Status
    age_bars: int               # bars between event and latest bar
    note: str                   # human-readable description


def _matching_confirmation(
    struct: list[StructureEvent],
    event_ts: pd.Timestamp,
    direction: Direction,
    ttl_cutoff: pd.Timestamp,
) -> StructureEvent | None:
    suffix = "_up" if direction == "bullish" else "_down"
    for s in struct:
        if s.timestamp < event_ts:
            continue
        if s.timestamp > ttl_cutoff:
            break
        if s.kind.endswith(suffix):
            return s
    return None


def scan_signals(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    swing_window: int = 5,
    rr_ratio: float = 2.0,
    signal_ttl: int = 10,
    correlation: str = "positive",
) -> list[TradeSignal]:
    """Run SMT detection on aligned A/B frames and attach trade levels.

    For each SMT event:
      - entry = close of event bar (on A)
      - stop  = pivot * 0.995 (bullish) or * 1.005 (bearish)
      - target = entry ± (entry - stop).abs() * rr_ratio
    TTL is measured in bars on the A index. A signal is `actionable` if
    a BOS/CHOCH in the same direction occurs within the TTL window.
    """
    if not df_a.index.equals(df_b.index):
        raise ValueError("df_a and df_b must be aligned (same index).")

    events: list[SMTEvent] = detect_smt(
        df_a, df_b, window=swing_window, correlation=correlation
    )
    if not events:
        return []

    swings_a = detect_swings(df_a, window=swing_window)
    struct = detect_structure(df_a, swings_a)
    index = df_a.index
    last_ts = index[-1]

    signals: list[TradeSignal] = []
    for ev in events:
        try:
            event_pos = index.get_loc(ev.timestamp)
        except KeyError:
            continue
        entry = float(df_a["close"].iloc[event_pos])
        pivot = float(ev.pivot_a.price)

        if ev.direction == "bullish":
            stop = pivot * 0.995
            risk = entry - stop
            if risk <= 0:
                continue
            target = entry + risk * rr_ratio
        else:
            stop = pivot * 1.005
            risk = stop - entry
            if risk <= 0:
                continue
            target = entry - risk * rr_ratio

        ttl_end_pos = min(event_pos + signal_ttl, len(index) - 1)
        ttl_cutoff = index[ttl_end_pos]
        confirm = _matching_confirmation(struct, ev.timestamp, ev.direction, ttl_cutoff)
        confirmed = confirm is not None

        age = len(index) - 1 - event_pos
        if age > signal_ttl:
            status: Status = "expired"
        elif confirmed:
            status = "actionable"
        else:
            status = "pending_confirmation"

        if confirmed:
            note = f"已被 {confirm.kind} 確認 @ {confirm.timestamp.date()}"
        elif status == "pending_confirmation":
            note = "等待 BOS/CHOCH 確認"
        else:
            note = "已逾期,僅供歷史參考"

        signals.append(
            TradeSignal(
                timestamp=ev.timestamp,
                direction=ev.direction,
                pivot_price=pivot,
                entry=entry,
                stop=stop,
                target=target,
                risk_per_unit=risk,
                rr_ratio=rr_ratio,
                confirmed=confirmed,
                status=status,
                age_bars=age,
                note=note,
            )
        )

    return signals
