"""Backtest runner supporting US and TW markets (both via yfinance)."""
from __future__ import annotations

from pathlib import Path
import yaml
import backtrader as bt

from data import YFinanceLoader, TwYFinanceLoader, align
from strategies import SMTStrategy


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "pairs.yaml"


def _loader(market: str):
    return YFinanceLoader() if market == "US" else TwYFinanceLoader()


def run(
    pair_name: str,
    start: str,
    end: str,
    timeframe: str = "1d",
    params: dict | None = None,
    cash: float = 100_000.0,
):
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["pairs"][pair_name]
    loader = _loader(cfg["market"])

    a = loader.fetch(cfg["primary"], start, end, timeframe)
    b = loader.fetch(cfg["reference"], start, end, timeframe)
    a, b = align(a, b)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(cash)
    cerebro.adddata(bt.feeds.PandasData(dataname=a), name=cfg["primary"])
    cerebro.adddata(bt.feeds.PandasData(dataname=b), name=cfg["reference"])

    strat_params = dict(correlation=cfg.get("correlation", "positive"))
    if params:
        strat_params.update(params)
    cerebro.addstrategy(SMTStrategy, **strat_params)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    results = cerebro.run()
    return cerebro, results[0]


if __name__ == "__main__":
    cerebro, strat = run("SPY_QQQ", "2018-01-01", "2024-12-31")
    print("Final value:", cerebro.broker.getvalue())
    print("Sharpe:", strat.analyzers.sharpe.get_analysis())
    print("DD:", strat.analyzers.dd.get_analysis())
    print("Trades:", strat.analyzers.trades.get_analysis())
