"""M7 — parameter sensitivity study.

Sweeps strategy parameters over a grid, runs the backtest for each
combination, and collects summary metrics into a pandas DataFrame.

Usage (script):
    python -m backtest.sensitivity --pair SPY_QQQ \
        --start 2018-01-01 --end 2024-12-31 \
        --out results/sensitivity_spy_qqq.csv

Usage (library):
    from backtest.sensitivity import sweep, DEFAULT_GRID
    df = sweep("SPY_QQQ", "2018-01-01", "2024-12-31")
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd

from .runner import run
from .analyzer import summarize


DEFAULT_GRID: dict[str, list] = {
    "swing_window": [3, 5, 7, 10],
    "rr_ratio": [1.5, 2.0, 3.0],
    "signal_ttl": [5, 10, 20],
}


def sweep(
    pair: str,
    start: str,
    end: str,
    grid: dict[str, list] | None = None,
    timeframe: str = "1d",
    cash: float = 100_000.0,
    require_confirmation: bool = True,
    verbose: bool = True,
) -> pd.DataFrame:
    """Run the backtest for every parameter combination in `grid`.

    Returns a DataFrame with one row per combo: params + metrics.
    Failures (e.g. not enough data) are captured with an `error` column.
    """
    grid = grid or DEFAULT_GRID
    keys = list(grid.keys())
    combos = list(itertools.product(*(grid[k] for k in keys)))
    rows: list[dict] = []

    for i, values in enumerate(combos, 1):
        params = dict(zip(keys, values))
        params["require_confirmation"] = require_confirmation
        row: dict = {**params, "error": None}
        if verbose:
            tag = " ".join(f"{k}={v}" for k, v in params.items() if k != "require_confirmation")
            print(f"[{i}/{len(combos)}] {tag}")
        try:
            _, strat = run(pair, start, end, timeframe=timeframe, params=params, cash=cash)
            row.update(summarize(strat))
        except Exception as exc:  # noqa: BLE001
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    df = pd.DataFrame(rows)
    # Sort best-first by sharpe (None last), then net_pnl.
    if "sharpe" in df.columns:
        df = df.sort_values(
            by=["sharpe", "net_pnl"],
            ascending=[False, False],
            na_position="last",
        ).reset_index(drop=True)
    return df


def _print_top(df: pd.DataFrame, n: int = 10) -> None:
    cols = [
        c
        for c in ["swing_window", "rr_ratio", "signal_ttl",
                  "sharpe", "max_drawdown_pct", "trades",
                  "win_rate", "net_pnl", "error"]
        if c in df.columns
    ]
    print(f"\nTop {min(n, len(df))} combos:")
    with pd.option_context("display.width", 160, "display.max_columns", None):
        print(df[cols].head(n).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="SMT parameter sensitivity sweep")
    parser.add_argument("--pair", default="SPY_QQQ")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--cash", type=float, default=100_000.0)
    parser.add_argument("--no-confirmation", action="store_true")
    parser.add_argument("--out", default=None, help="save full results to CSV")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    df = sweep(
        pair=args.pair,
        start=args.start,
        end=args.end,
        timeframe=args.timeframe,
        cash=args.cash,
        require_confirmation=not args.no_confirmation,
    )

    _print_top(df, n=args.top)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"\nSaved full results → {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
