# SMT / ICT Tutorial — From Concept to CLI

This document explains how **SMT Divergence** works under the ICT (Inner Circle Trader) framework, and how each CLI parameter in this project maps to a trading concept. After reading you should be able to interpret `python cli.py` output and know how to tune the parameters.

> ⚠️ Educational use only. Nothing here is investment advice.

---

## 1. Glossary

| Term | Meaning |
|---|---|
| **Swing High / Low** | Local extreme: a candle whose high (low) exceeds the N candles on each side. |
| **HH / HL / LH / LL** | Higher High / Higher Low / Lower High / Lower Low — comparisons between two consecutive same-type pivots. |
| **SMT Divergence** | Two correlated instruments where one prints a new high/low and the other does not. |
| **BOS** | Break of Structure — close beyond the most recent same-direction swing; trend continuation. |
| **CHOCH** | Change of Character — first opposite-direction BOS; trend reversal signal. |
| **Pivot** | The swing point that triggered the signal (used as the stop reference). |
| **R:R** | Risk:reward ratio = `(target - entry) / (entry - stop)`. 2.0 means risking 1 to make 2. |
| **TTL** | Signal lifetime — how many bars after the SMT event the signal remains valid. |

---

## 2. The ICT Intuition

ICT assumes markets are driven by "smart money". When they prepare to reverse, they often stop printing new highs/lows on one instrument while the correlated one (the retail favorite) keeps extending by inertia. That **divergence** is the smart-money footprint.

### 2.1 Classic example — SPY vs QQQ

SPY (S&P 500) and QQQ (Nasdaq 100) are both US large-cap and highly correlated.

```
Bearish SMT
          SPY                 QQQ
high2  ●  ← new HH            ●
       \                     /  ← failed to print HH (LH)
high1   ●                   ●
```

SPY makes a new high but QQQ does not → **bearish SMT**, hinting at a pullback. Before going short you typically wait for a **BOS_down or CHOCH_down** as confirmation.

### 2.2 Bullish example

```
Bullish SMT
          SPY                 QQQ
low1    ●                    ●
       /                      \   ← held above prior low (HL)
low2  ●  ← new LL              ●
```

SPY breaks down but QQQ holds → **bullish SMT**, building a bounce.

### 2.3 Why also use BOS / CHOCH?

SMT alone only tells you "momentum is fading", not "the reversal is now". Adding structure confirmation cuts false signals significantly:

- **BOS_up** = close above the most recent swing high → buyers stepping in.
- **CHOCH_up** = the first BOS_up after a downtrend → stronger reversal cue.

This project's `actionable` status = SMT **plus** a same-direction BOS/CHOCH within the TTL window.

---

## 3. How Entry / Stop / Target Are Computed

The CLI uses the same rule as `strategies/smt_strategy.py`:

```
entry  = primary close on the SMT event day
         ├── bullish: stop   = pivot_low  × 0.995    (0.5% below pivot)
         │             risk  = entry - stop
         │             target= entry + risk × rr_ratio
         └── bearish: stop   = pivot_high × 1.005    (0.5% above pivot)
                      risk  = stop - entry
                      target= entry - risk × rr_ratio
```

- **pivot** is the swing point that triggered the signal; the stop sits 0.5% beyond it to give the market some noise room.
- **R:R = 2.0** means: for every 1 unit of loss space, the target sits at 2 units of profit.
- In live use you can trail the stop or scale out; this tool only gives a starting point.

---

## 4. CLI Parameters

```bash
python cli.py [options]
```

| Parameter | Default | Trading meaning |
|---|---|---|
| `--pair` | `SPY_QQQ` | The "primary / reference" pair to scan, defined in `config/pairs.yaml`. |
| `--start` / `--end` | last year | Date range. Longer ranges produce more signals but old ones are research-only. |
| `--timeframe` | `1d` | Bar interval. `1d` is most stable; `1h`/`4h` only supported for US via yfinance. |
| `--swing-window` | `5` | Fractal window. Larger → coarser pivots, fewer/cleaner signals. Smaller → more sensitive. |
| `--rr-ratio` | `2.0` | Target multiple. Conservative 1.5, aggressive 3.0. |
| `--signal-ttl` | `10` | Bars before an unconfirmed SMT event expires (avoids chasing stale signals). |
| `--no-confirmation` | off | Disable BOS/CHOCH filter to see every SMT event (noisy, research only). |
| `--mode` | `latest` | `latest` = only the most recent actionable; `scan` = full history. |
| `--list-pairs` | — | List available pairs and exit. |

### Tuning intuition

- **Too many / noisy signals**: raise `--swing-window` (7~10), keep confirmation on.
- **Too few / missing signals**: lower `--swing-window` (3), extend `--start`.
- **Want bigger moves**: `--rr-ratio 3` — but expect a lower hit rate.
- **Short-term trading**: `--signal-ttl 5` — only the fastest confirmations count.

---

## 5. Reading CLI Output

### 5.1 `latest` mode

```text
Fetching SPY_QQQ: SPY / QQQ (US) 2024-04-10 → 2025-04-09 [1d]

Scanned 250 bars → 6 SMT event(s)

>>> LATEST ACTIONABLE SIGNAL
    2025-03-18  BULLISH  entry=562.10  stop=557.30  target=571.70  R:R=2.0
    ✓ confirmed by BOS_up @ 2025-03-21
    ! informational only — not investment advice
```

How to read:
- On 2025-03-18 the program found a bullish SMT on SPY/QQQ.
- 3 days later (03-21) SPY closed above the most recent swing high → confirmation.
- Suggested entry 562.10, stop 557.30, target 571.70 — risk 4.80, reward 9.60.
- You can choose to enter at market or wait for a pullback near the stop.

### 5.2 `scan` mode

```text
  Date         Dir      Status                  Entry       Stop     Target  R:R   Age  Note
  ------------------------------------------------------------------------------------
✓ 2024-07-12   BEARISH  actionable            549.20     552.80     542.00   2.0    180  confirmed by BOS_down @ 2024-07-18
… 2024-11-02   BULLISH  pending_confirmation  580.10     576.30     587.70   2.0     90  awaiting BOS/CHOCH
x 2023-12-15   BULLISH  expired               470.40     467.50     476.20   2.0    240  past TTL — historical only
```

- ✓ = actionable (SMT + confirmation)
- … = pending_confirmation (SMT printed but not yet confirmed, still in TTL)
- x = expired (past TTL — review only)

---

## 6. Typical Workflow

```bash
# 1. see available pairs
python cli.py --list-pairs

# 2. quick check on US default
python cli.py

# 3. study history to train your eye
python cli.py --pair SPY_QQQ --mode scan --start 2023-01-01

# 4. switch to Taiwan
python cli.py --pair TSMC_0050 --mode scan

# 5. reduce noise by widening the window
python cli.py --swing-window 7

# 6. relax confirmation while researching
python cli.py --no-confirmation --mode scan
```

---

## 7. FAQ

**Q. Should I enter as soon as a signal is `actionable`?**
A. No. `actionable` only means SMT + structure confirmation are both in place. You still need to assess macro context, event risk, and position sizing. The tool does not push the button for you.

**Q. Why is there no signal on the most recent day?**
A. SMT can only be detected after a pivot has formed (a swing needs N bars to its right). With `swing_window=5`, you must wait at least 5 bars before a pivot is confirmed.

**Q. Why is the stop pivot ±0.5% rather than a fixed amount?**
A. This matches the rule in `smt_strategy.py` so the CLI signals and the backtest stats use exactly the same logic.

**Q. Are expired signals useful?**
A. Yes — for review. Check whether confirmation eventually appeared, and whether the R:R target would have been met. It's the best way to train pattern recognition.

---

## 8. Further Reading

- ICT Mentorship (free on YouTube) — Michael J. Huddleston's original lessons.
- *Trading in the Zone* — Mark Douglas (trading psychology).
- Project source code:
  - `core/swing.py` — swing detection
  - `core/smt_detector.py` — SMT rules
  - `core/confirmations.py` — BOS / CHOCH
  - `signals/advisor.py` — composes price-level signals
  - `strategies/smt_strategy.py` — corresponding backtest strategy

Happy researching. Reminder: **this tool is for education and signal hints only. You trade at your own risk.**
