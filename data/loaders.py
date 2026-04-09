"""Data loader abstraction. All loaders return OHLCV DataFrame
indexed by tz-aware timestamp with columns: open, high, low, close, volume.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd


class BaseLoader(ABC):
    @abstractmethod
    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame with lowercase columns."""
        raise NotImplementedError

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns=str.lower)
        cols = ["open", "high", "low", "close", "volume"]
        df = df[[c for c in cols if c in df.columns]].dropna()
        df.index = pd.to_datetime(df.index)
        return df


def align(a: pd.DataFrame, b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align two OHLCV frames on common timestamps (inner join)."""
    idx = a.index.intersection(b.index)
    return a.loc[idx].copy(), b.loc[idx].copy()
