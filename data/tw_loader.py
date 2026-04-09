"""Taiwan market loader using yfinance (free, no token required).

Symbol convention:
- Numeric stock/ETF id (e.g. "2330", "0050") → auto-suffixed to "2330.TW".
- "TAIEX" → mapped to "^TWII" (Yahoo's TAIEX index ticker).
- Anything starting with "^" or already containing "." is passed through.
"""
from __future__ import annotations

import pandas as pd

from .loaders import BaseLoader


def _normalize_symbol(symbol: str) -> str:
    s = symbol.strip()
    if s.upper() in ("TAIEX", "^TWII"):
        return "^TWII"
    if s.startswith("^") or "." in s:
        return s
    if s.isdigit():
        return f"{s}.TW"
    return s


class TwYFinanceLoader(BaseLoader):
    def fetch(self, symbol, start, end, interval="1d") -> pd.DataFrame:
        import yfinance as yf

        yf_symbol = _normalize_symbol(symbol)
        df = yf.download(
            yf_symbol,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise ValueError(f"No data for {symbol} ({yf_symbol}) [{start}..{end}]")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return self._normalize(df)


# Backwards-compat alias so existing imports keep working.
FinMindLoader = TwYFinanceLoader
