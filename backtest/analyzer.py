"""Performance stats and equity curve plotting."""
from __future__ import annotations

import matplotlib.pyplot as plt


def summarize(strat) -> dict:
    sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio")
    dd = strat.analyzers.dd.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    total = trades.get("total", {}).get("total", 0)
    won = trades.get("won", {}).get("total", 0)
    lost = trades.get("lost", {}).get("total", 0)
    win_rate = (won / total) if total else 0.0
    pnl_net = trades.get("pnl", {}).get("net", {}).get("total", 0.0)
    return {
        "sharpe": sharpe,
        "max_drawdown_pct": dd.get("max", {}).get("drawdown"),
        "trades": total,
        "wins": won,
        "losses": lost,
        "win_rate": win_rate,
        "net_pnl": pnl_net,
    }


def plot_equity(cerebro, path: str | None = None):
    figs = cerebro.plot(style="candlestick", iplot=False, show=False)
    if path:
        figs[0][0].savefig(path, dpi=120)
    return figs
