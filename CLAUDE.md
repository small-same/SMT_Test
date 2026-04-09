# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SMT — Python + Backtrader framework for backtesting ICT **SMT Divergence** strategies on US (yfinance) and Taiwan (FinMind) markets. Research-only; no live trading.

## Commands

```bash
pip install -r requirements.txt
pytest tests/                          # all tests
pytest tests/test_smt_detector.py -k name   # single test

python cli.py                          # interactive signal scan (defaults SPY/QQQ)
python cli.py --pair TSMC_0050 --mode scan --start 2024-01-01 --end 2025-01-01
python cli.py --list-pairs

python -m backtest.sensitivity --pair SPY_QQQ \
    --start 2018-01-01 --end 2024-12-31 \
    --out results/sensitivity_spy_qqq.csv
```

Programmatic backtest:
```python
from backtest import run, summarize
cerebro, strat = run("SPY_QQQ", "2018-01-01", "2024-12-31")
```

## Architecture

Pipeline flows in one direction: **data → core → strategies → backtest/cli**.

- `config/pairs.yaml` — declares correlated pairs (primary + reference symbol, market). All pair lookups go through this file; new pairs are added here, not in code.
- `data/` — market loaders (yfinance for US, FinMind for TW) normalized to a **unified OHLCV interface** so downstream code is market-agnostic.
- `core/swing.py` — fractal-based swing high/low detection (parameter: `swing_window`).
- `core/smt_detector.py` — ICT swing-based **SMT divergence** between primary and reference series. Consumes swings from `core/swing.py`.
- `core/confirmations.py` — BOS / CHOCH market-structure filter. Optional; toggled via `--no-confirmation` in CLI and strategy params.
- `strategies/smt_strategy.py` — Backtrader `Strategy` wrapping the detector + confirmation; emits entries with stop/target sized by `rr_ratio`, expiring after `signal_ttl` bars.
- `backtest/runner.py` — wires loaders + strategy into a `cerebro`, attaches analyzers, exposes `run()` / `summarize()`.
- `backtest/sensitivity.py` — grid sweep over `swing_window × rr_ratio × signal_ttl` (default 36 combos), Sharpe-ranked.
- `cli.py` — interactive scanner (latest signal vs. scan-all modes); shares the same detector/confirmation stack as the backtest path.
- `notebooks/research.ipynb` — visual validation of swings/SMT events.

Key params propagated through the stack: `swing_window`, `rr_ratio`, `signal_ttl`, `--no-confirmation`. When changing any of these semantics, update `core/`, `strategies/smt_strategy.py`, `cli.py`, and `backtest/sensitivity.py` together.

Full concept docs: `docs/SMT_TUTORIAL.md`.
