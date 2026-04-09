"""Backtrader strategy using SMT divergence + BOS/CHOCH confirmation.

Feeds:
    data0 = primary (A, traded)
    data1 = reference (B, SMT correlated asset)
"""
from __future__ import annotations

import backtrader as bt
import pandas as pd

from core.swing import detect_swings, last_two
from core.smt_detector import _bearish_from_highs, _bullish_from_lows
from core.confirmations import detect_structure


class SMTStrategy(bt.Strategy):
    params = dict(
        swing_window=5,
        lookback_bars=120,
        rr_ratio=2.0,
        risk_per_trade=0.01,       # 1% equity per trade
        signal_ttl=10,             # bars a pending signal remains valid
        require_confirmation=True,
        correlation="positive",
    )

    def __init__(self):
        self.order = None
        self.stop_price = None
        self.target_price = None
        self.pending = None  # dict(direction, pivot, stop_ref, age)

    # ------------------------------------------------------------------
    def _window_df(self, data) -> pd.DataFrame:
        n = min(self.p.lookback_bars, len(data))
        idx = [bt.num2date(data.datetime[-i]) for i in range(n - 1, -1, -1)]
        return pd.DataFrame(
            {
                "high": [data.high[-i] for i in range(n - 1, -1, -1)],
                "low": [data.low[-i] for i in range(n - 1, -1, -1)],
                "close": [data.close[-i] for i in range(n - 1, -1, -1)],
            },
            index=pd.DatetimeIndex(idx),
        )

    # ------------------------------------------------------------------
    def next(self):
        # Exit first (intrabar stop / target approximation on close).
        if self.position and self.stop_price is not None:
            price = self.datas[0].close[0]
            if self.position.size > 0:
                if price <= self.stop_price or price >= self.target_price:
                    self.close()
                    self.stop_price = None
                    return
            else:
                if price >= self.stop_price or price <= self.target_price:
                    self.close()
                    self.stop_price = None
                    return

        if len(self.datas[0]) < self.p.lookback_bars:
            return
        if self.order:
            return

        df_a = self._window_df(self.datas[0])
        df_b = self._window_df(self.datas[1])
        sa = detect_swings(df_a, self.p.swing_window)
        sb = detect_swings(df_b, self.p.swing_window)
        if len(sa) < 2 or len(sb) < 2:
            return

        ah, bh = last_two(sa, "high"), last_two(sb, "high")
        al, bl = last_two(sa, "low"), last_two(sb, "low")

        # Fresh SMT signal on this bar?
        if ah and bh and _bearish_from_highs(ah, bh):
            recent_low = max((s for s in sa if s.type == "low"), key=lambda s: s.timestamp, default=None)
            self.pending = dict(
                direction="bearish", pivot=ah[1].price,
                stop_ref=ah[1].price, age=0,
            )
        if al and bl and _bullish_from_lows(al, bl):
            self.pending = dict(
                direction="bullish", pivot=al[1].price,
                stop_ref=al[1].price, age=0,
            )

        if not self.pending:
            return

        # TTL
        self.pending["age"] += 1
        if self.pending["age"] > self.p.signal_ttl:
            self.pending = None
            return

        direction = self.pending["direction"]
        price = self.datas[0].close[0]

        # Confirmation via BOS/CHOCH on primary.
        confirmed = True
        if self.p.require_confirmation:
            struct = detect_structure(df_a, sa)
            if not struct:
                confirmed = False
            else:
                last = struct[-1]
                if direction == "bullish" and not last.kind.endswith("_up"):
                    confirmed = False
                if direction == "bearish" and not last.kind.endswith("_down"):
                    confirmed = False

        if not confirmed or self.position:
            return

        equity = self.broker.getvalue()
        stop_ref = self.pending["stop_ref"]
        if direction == "bullish":
            stop = stop_ref * 0.995  # just below pivot low
            risk = price - stop
            if risk <= 0:
                self.pending = None
                return
            size = max(1, int((equity * self.p.risk_per_trade) / risk))
            self.order = self.buy(size=size)
            self.stop_price = stop
            self.target_price = price + risk * self.p.rr_ratio
        else:
            stop = stop_ref * 1.005
            risk = stop - price
            if risk <= 0:
                self.pending = None
                return
            size = max(1, int((equity * self.p.risk_per_trade) / risk))
            self.order = self.sell(size=size)
            self.stop_price = stop
            self.target_price = price - risk * self.p.rr_ratio

        self.pending = None

    def notify_order(self, order):
        if order.status in (order.Completed, order.Canceled, order.Rejected, order.Margin):
            self.order = None
