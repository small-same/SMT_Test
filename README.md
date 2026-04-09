# SMT — Smart Money Technique Backtest Framework

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Disclaimer**:本專案僅供**學術研究與策略回測**使用,不構成任何投資建議。
> 使用者依本專案資訊進行任何交易行為所造成之盈虧,作者概不負責。

一個基於 Python + [Backtrader](https://www.backtrader.com/) 的回測框架,
用來研究 ICT(Inner Circle Trader)交易概念中的 **SMT 背離(Smart Money Divergence)** 策略,
支援**美股**(yfinance)與**台股**(yfinance / Yahoo Finance)。

---

## 什麼是 SMT 背離?

兩個高度相關的標的(例如 SPY 與 QQQ、台積電 2330 與 0050)在**正常情況下會同漲同跌**。
當其中一個創**新低**而另一個**沒有跟著創新低**時,代表「聰明錢」可能已經停止賣出 →
這就是**看多 SMT 背離**(反之亦然為看空)。

本框架做的事:

1. 用**分形(fractal)**自動偵測兩個標的的 swing high / low。
2. 比對兩邊的 swing,找出 SMT 背離事件。
3. 用 **BOS / CHOCH** 市場結構作為進場確認(可選)。
4. 用 Backtrader 進行歷史回測,輸出 Sharpe、勝率、最大回撤等指標。
5. 提供 CLI 即時掃描最近的訊號(含建議 entry / stop / target)。

完整概念與參數解說見 [`docs/SMT_TUTORIAL.md`](docs/SMT_TUTORIAL.md)。

---

## 安裝

需求:**Python 3.10+**(在 Windows / macOS / Linux 上皆可運行,測試於 3.10–3.11)。

```bash
# 1. clone
git clone https://github.com/<your-account>/SMT.git
cd SMT

# 2. 建立虛擬環境(建議)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 跑測試確認環境 OK
pytest tests/
```

> **資料來源說明**:本專案所有資料皆透過 [yfinance](https://github.com/ranaroussi/yfinance)(免費、免註冊、免 token)從 Yahoo Finance 抓取。
> Yahoo 偶爾會觸發 rate limit,如果某次抓取失敗請稍等幾秒後重試。

---

## Quick Start

### 程式化回測

```python
from backtest import run, summarize

cerebro, strat = run("SPY_QQQ", "2018-01-01", "2024-12-31")
print(summarize(strat))
```

預期輸出(範例):

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

### CLI 訊號掃描

```bash
# 預設:SPY/QQQ 最近一年,顯示最新一筆 actionable 訊號
python cli.py

# 指定配對與時間區間
python cli.py --pair TSMC_0050 --start 2024-01-01 --end 2025-01-01

# 列出區間內所有 SMT 事件
python cli.py --pair SPY_QQQ --mode scan

# 不要求 BOS/CHOCH 市場結構確認
python cli.py --no-confirmation

# 列出所有可用的 pair
python cli.py --list-pairs
```

---

## 內建 Pair

| Name        | Market | Primary       | Reference     | 說明                       |
|-------------|--------|---------------|---------------|----------------------------|
| `SPY_QQQ`   | US     | SPY           | QQQ           | 美股 ETF 經典組合          |
| `SPX_NDX`   | US     | ^GSPC (S&P)   | ^IXIC (NDX)   | 美股指數                   |
| `TWII_0050` | TW     | 0050          | TAIEX (^TWII) | 台灣 50 ETF vs 加權指數    |
| `TSMC_0050` | TW     | 2330 (台積電) | 0050          | 個股 vs ETF                |

### 新增自己的 Pair

編輯 [`config/pairs.yaml`](config/pairs.yaml),格式如下:

```yaml
pairs:
  MY_PAIR:
    market: US             # US 或 TW
    primary: AAPL          # 主要交易標的
    reference: MSFT        # 參照標的(用來偵測背離)
    correlation: positive  # positive 或 negative
```

**台股代號慣例**:直接寫數字代號(`"2330"`、`"0050"`),loader 會自動補上 `.TW` 後綴;
指數請寫 `TAIEX` 或 `^TWII`。

---

## 主要參數

所有參數都會在 CLI、回測、敏感度分析三條路徑共用同一套語義:

| 參數                  | 預設 | 說明                                                       |
|-----------------------|------|------------------------------------------------------------|
| `--swing-window`      | 5    | Swing high/low 的分形視窗(越大越保守,訊號越少)。       |
| `--rr-ratio`          | 2.0  | 風險報酬比,決定 take-profit 距離(stop × rr)。           |
| `--signal-ttl`        | 10   | 訊號出現後幾根 K 線內未觸發即過期。                        |
| `--no-confirmation`   | off  | 關閉 BOS/CHOCH 市場結構過濾(訊號變多但雜訊也多)。       |
| `--mode {latest,scan}`| latest | CLI 模式:只顯示最新一筆 / 列出全部事件。                |

---

## 參數敏感度分析

```bash
python -m backtest.sensitivity --pair SPY_QQQ \
    --start 2018-01-01 --end 2024-12-31 \
    --out results/sensitivity_spy_qqq.csv
```

預設網格:`swing_window ∈ {3,5,7,10}` × `rr_ratio ∈ {1.5,2,3}` × `signal_ttl ∈ {5,10,20}`,
共 36 組;結果依 Sharpe 排序輸出至 stdout 與 CSV。

---

## 專案結構

資料流向:**`data → core → strategies → backtest / cli`**

```
SMT/
├── config/pairs.yaml          # 配對定義(新增 pair 改這裡)
├── data/
│   ├── loaders.py             # BaseLoader 抽象介面
│   ├── us_loader.py           # 美股(yfinance)
│   └── tw_loader.py           # 台股(yfinance,自動處理 .TW 後綴)
├── core/
│   ├── swing.py               # 分形 swing 偵測
│   ├── smt_detector.py        # SMT 背離偵測
│   └── confirmations.py       # BOS / CHOCH 市場結構
├── strategies/
│   └── smt_strategy.py        # Backtrader Strategy 包裝
├── backtest/
│   ├── runner.py              # cerebro 組裝 + analyzers
│   └── sensitivity.py         # 參數網格搜尋
├── signals/                   # CLI 用的訊號掃描器
├── notebooks/research.ipynb   # 視覺驗證 swing / SMT
├── docs/SMT_TUTORIAL.md       # 完整教學文件
├── tests/                     # pytest 單元測試
└── cli.py                     # 互動式訊號掃描
```

---

## 已知限制

- yfinance 偶爾觸發 Yahoo rate limit,連續抓取多個 symbol 時需稍等。
- 台股資料目前只支援**價量**,沒有三大法人 / 融資券等籌碼面資料。
  若需要籌碼面,可自行接 [FinMind](https://finmindtrade.com/) 或證交所開放資料。
- Backtrader 在 Python 3.12+ 偶有相容性警告,建議使用 3.10 / 3.11。

---

## 貢獻

歡迎開 issue 與 PR。回報問題時請附上:
- Python 版本與作業系統
- 完整錯誤訊息
- 重現用的指令或程式碼片段

---

## Acknowledgements

- 策略概念來自 [ICT(Inner Circle Trader)](https://www.youtube.com/@InnerCircleTrader) 教學體系。
- 回測引擎:[Backtrader](https://www.backtrader.com/)
- 資料來源:[Yahoo Finance](https://finance.yahoo.com/) via [yfinance](https://github.com/ranaroussi/yfinance)

---

## License

[MIT](LICENSE) © 2026 SMT Project Contributors

**This project is research-only. No live trading. Use at your own risk.**
