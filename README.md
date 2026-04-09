# SMT — Smart Money Technique Backtest Framework

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Disclaimer**: This project is for **academic research and strategy backtesting only**. It does not constitute investment advice. The authors are not responsible for any profits or losses arising from trades made based on this project.

A Python + [Backtrader](https://www.backtrader.com/) framework for researching the **SMT Divergence (Smart Money Divergence)** concept from the ICT (Inner Circle Trader) methodology, supporting both **US equities** (yfinance) and **Taiwan equities** (yfinance / Yahoo Finance).

---

## What is SMT Divergence?

Two highly correlated instruments (e.g. SPY and QQQ, or TSMC 2330 and 0050) **normally move together**. When one makes a **new low** but the other **fails to**, it suggests "smart money" may have stopped selling — this is a **bullish SMT divergence** (and vice versa for bearish).

What this framework does:

1. Automatically detects swing highs/lows on both instruments using a **fractal** method.
2. Compares swings on both sides to identify SMT divergence events.
3. Optionally uses **BOS / CHOCH** market structure as entry confirmation.
4. Runs historical backtests via Backtrader, reporting Sharpe, win rate, max drawdown, etc.
5. Provides a CLI to scan for the latest signals (with suggested entry / stop / target).

Full concept and parameter walkthrough: [`docs/SMT_TUTORIAL_EN.md`](docs/SMT_TUTORIAL_EN.md).

---

## Installation

Requires **Python 3.10+** (works on Windows / macOS / Linux; tested on 3.10–3.11).

```bash
# 1. clone
git clone https://github.com/<your-account>/SMT.git
cd SMT

# 2. create a virtual environment (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. install dependencies
pip install -r requirements.txt

# 4. run the test suite to verify the environment
pytest tests/
```

> **Data source note**: All data is fetched from Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) (free, no signup, no token). Yahoo occasionally rate-limits — if a fetch fails, wait a few seconds and retry.

---

## Quick Start

### Programmatic backtest

```python
from backtest import run, summarize

cerebro, strat = run("SPY_QQQ", "2018-01-01", "2024-12-31")
print(summarize(strat))
```

Example output:

```
{
  'pair': 'SPY_QQQ',
  'trades': 47,
  'win_rate': 0.553,
  'sharpe': 1.12,
  'max_drawdown_pct': 8.4,
  'final_value': 11820.55
}
```

### CLI signal scanner

```bash
# default: SPY/QQQ over the past year, showing the latest actionable signal
python cli.py

# specify pair and date range
python cli.py --pair TSMC_0050 --start 2024-01-01 --end 2025-01-01

# list all SMT events in the range
python cli.py --pair SPY_QQQ --mode scan

# disable BOS/CHOCH market-structure confirmation
python cli.py --no-confirmation

# list all available pairs
python cli.py --list-pairs
```

---

## Built-in Pairs

| Name        | Market | Primary       | Reference     | Notes                          |
|-------------|--------|---------------|---------------|--------------------------------|
| `SPY_QQQ`   | US     | SPY           | QQQ           | Classic US ETF pair            |
| `SPX_NDX`   | US     | ^GSPC (S&P)   | ^IXIC (NDX)   | US indices                     |
| `TWII_0050` | TW     | 0050          | TAIEX (^TWII) | Taiwan 50 ETF vs broad index   |
| `TSMC_0050` | TW     | 2330 (TSMC)   | 0050          | Single stock vs ETF            |

### Adding your own pair

Edit [`config/pairs.yaml`](config/pairs.yaml):

```yaml
pairs:
  MY_PAIR:
    market: US             # US or TW
    primary: AAPL          # primary trading instrument
    reference: MSFT        # reference instrument (used for divergence)
    correlation: positive  # positive or negative
```

**Taiwan ticker convention**: write the numeric code directly (`"2330"`, `"0050"`) — the loader appends `.TW` automatically. For the index use `TAIEX` or `^TWII`.

---

## Key Parameters

The same parameter semantics flow through the CLI, the backtest, and the sensitivity analysis:

| Parameter             | Default | Meaning                                                    |
|-----------------------|---------|------------------------------------------------------------|
| `--swing-window`      | 5       | Fractal window for swing detection (larger = fewer, more conservative signals). |
| `--rr-ratio`          | 2.0     | Risk:reward ratio determining take-profit distance (`stop × rr`). |
| `--signal-ttl`        | 10      | Bars after a signal appears before it expires unconfirmed. |
| `--no-confirmation`   | off     | Disable BOS/CHOCH structure filter (more signals, more noise). |
| `--mode {latest,scan}`| latest  | CLI mode: latest actionable only, or list all events.      |

---

## Parameter Sensitivity Analysis

```bash
python -m backtest.sensitivity --pair SPY_QQQ \
    --start 2018-01-01 --end 2024-12-31 \
    --out results/sensitivity_spy_qqq.csv
```

Default grid: `swing_window ∈ {3,5,7,10}` × `rr_ratio ∈ {1.5,2,3}` × `signal_ttl ∈ {5,10,20}` → 36 combinations. Results are sorted by Sharpe and printed to stdout as well as written to CSV.

---

## Project Layout

Data flow: **`data → core → strategies → backtest / cli`**

```
SMT/
├── config/pairs.yaml          # pair definitions (add new pairs here)
├── data/
│   ├── loaders.py             # BaseLoader abstract interface
│   ├── us_loader.py           # US (yfinance)
│   └── tw_loader.py           # TW (yfinance, handles .TW suffix)
├── core/
│   ├── swing.py               # fractal swing detection
│   ├── smt_detector.py        # SMT divergence detection
│   └── confirmations.py       # BOS / CHOCH market structure
├── strategies/
│   └── smt_strategy.py        # Backtrader Strategy wrapper
├── backtest/
│   ├── runner.py              # cerebro assembly + analyzers
│   └── sensitivity.py         # parameter grid search
├── signals/                   # CLI signal scanner
├── notebooks/research.ipynb   # visual validation of swings / SMT
├── docs/SMT_TUTORIAL_EN.md    # full tutorial
├── tests/                     # pytest unit tests
└── cli.py                     # interactive signal scanner
```

---

## Known Limitations

- yfinance occasionally hits Yahoo rate limits — pace bulk fetches.
- Taiwan data currently includes **price/volume only**; no institutional flow / margin data. For that, integrate [FinMind](https://finmindtrade.com/) or TWSE open data yourself.
- Backtrader emits compatibility warnings on Python 3.12+. Python 3.10 / 3.11 is recommended.

---

## Contributing

Issues and PRs welcome. When reporting an issue please include:
- Python version and OS
- Full error message
- The exact command or code snippet that reproduces it

---

## Acknowledgements

- Strategy concepts from the [ICT (Inner Circle Trader)](https://www.youtube.com/@InnerCircleTrader) curriculum.
- Backtest engine: [Backtrader](https://www.backtrader.com/)
- Data source: [Yahoo Finance](https://finance.yahoo.com/) via [yfinance](https://github.com/ranaroussi/yfinance)

---

## License

[MIT](LICENSE) © 2026 SMT Project Contributors

**This project is research-only. No live trading. Use at your own risk.**
