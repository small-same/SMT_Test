"""US equities loader using yfinance."""
from __future__ import annotations

import pandas as pd

from .loaders import BaseLoader


class YFinanceLoader(BaseLoader):
    def fetch(self, symbol, start, end, interval="1d") -> pd.DataFrame:
        import yfinance as yf

        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise ValueError(f"No data for {symbol} [{start}..{end}]")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return self._normalize(df)
