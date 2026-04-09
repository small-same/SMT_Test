# SMT / ICT 教學 — 從概念到 CLI 實操

本文件解釋 ICT (Inner Circle Trader) 框架下的 **SMT Divergence**
如何運作,以及本專案 CLI 的每個參數對應到什麼交易概念。
閱讀後你應能看懂 `python cli.py` 的輸出,並知道怎麼調整參數。

> ⚠️ 所有內容僅為教育用途,不構成投資建議。

---

## 1. 名詞速查

| 名詞 | 中文 | 一句話解釋 |
|---|---|---|
| **Swing High / Low** | 擺動高/低點 | 局部極值:一根 K 棒的高(低)點比左右各 N 根都高(低) |
| **HH / HL / LH / LL** | 高高 / 高低 / 低高 / 低低 | 相鄰兩個同類 pivot 的比較(Higher High、Lower Low 等) |
| **SMT Divergence** | 智慧錢背離 | 兩個「應該同向」的標的,其中一個創新高/低而另一個沒跟上 |
| **BOS** | Break of Structure | 收盤價突破「最近的同向 swing」,視為趨勢延續 |
| **CHOCH** | Change of Character | 第一次反向 BOS,視為趨勢轉折訊號 |
| **Pivot** | 樞紐 | 觸發訊號的那個 swing 點(停損參考位) |
| **R:R** | 風險報酬比 | `(target - entry) / (entry - stop)`,固定 2.0 代表賺 2 賠 1 |
| **TTL** | 訊號壽命 | SMT 發生後幾根 K 棒內還算有效,過期就作廢 |

---

## 2. ICT 的核心直覺

ICT 假設市場由「聰明錢 (smart money)」主導。當他們**準備反向**時,
常常先在某個標的停止製造新高/低,而相關標的(散戶追的那個)仍
在慣性延伸。兩者出現**背離**,就是聰明錢先收手的腳印。

### 2.1 經典例子 — SPY vs QQQ

SPY(標普 500)和 QQQ(那指 100)同屬美股大盤,正相關極高。

```
情境:熊市 SMT (bearish)
          SPY                 QQQ
高點2 ●  ← 新高 (HH)          ●
       \                    /  ← 沒創新高 (LH)
高點1   ●                  ●
```

SPY 創新高但 QQQ 沒跟上 → **bearish SMT**,暗示即將回落。
要進空單前,通常再等一個 **BOS_down 或 CHOCH_down** 作為
確認才動手。

### 2.2 多頭例子

```
情境:多頭 SMT (bullish)
          SPY                 QQQ
低點1   ●                  ●
       /                    \   ← 沒再破底 (HL)
低點2 ●  ← 新低 (LL)          ●
```

SPY 破底但 QQQ 守住 → **bullish SMT**,醞釀反彈。

### 2.3 為什麼還要 BOS / CHOCH?

光是 SMT 只能告訴你「動能消退」,不代表「馬上反轉」。
加上結構確認可大幅降低假訊號:

- **BOS_up** = 收盤突破最近 swing high → 買方接手
- **CHOCH_up** = 由下行轉為第一次 BOS_up → 轉折訊號更強

本專案的 `actionable` 狀態 = SMT + 同向 BOS/CHOCH 發生於 TTL 內。

---

## 3. 進出場價位怎麼算

程式用與 `strategies/smt_strategy.py` 相同的規則:

```
entry  = SMT 事件當天的收盤價 (primary)
         ├── bullish: stop   = pivot_low  × 0.995    (pivot 下方 0.5%)
         │             risk  = entry - stop
         │             target= entry + risk × rr_ratio
         └── bearish: stop   = pivot_high × 1.005    (pivot 上方 0.5%)
                      risk  = stop - entry
                      target= entry - risk × rr_ratio
```

- **pivot** 就是觸發訊號的那個 swing 點,把停損藏在它外側 0.5%
  給市場一點雜訊空間。
- **R:R = 2.0** 代表:若虧損 1 元的空間,目標設在獲利 2 元的價位。
- 真實進場可再自行移動停損或分批止盈,本工具只給建議起點。

---

## 4. CLI 參數對照表

```bash
python cli.py [options]
```

| 參數 | 預設 | 交易意義 |
|---|---|---|
| `--pair` | `SPY_QQQ` | 要掃描的「主交易 / 參考」配對,定義於 `config/pairs.yaml` |
| `--start` / `--end` | 近一年 | 資料區間;越長訊號越多,但過舊訊號只能研究不能交易 |
| `--timeframe` | `1d` | K 棒週期。`1d` 最穩定;`1h`/`4h` 僅 yfinance(美股)支援 |
| `--swing-window` | `5` | fractal 窗口。值越大 pivot 越粗、訊號越少越穩;小值較敏感 |
| `--rr-ratio` | `2.0` | 目標價與停損的倍數。保守 1.5、積極 3.0 |
| `--signal-ttl` | `10` | SMT 幾根 K 棒內未被確認就作廢(避免追太舊的訊號) |
| `--no-confirmation` | off | 關掉 BOS/CHOCH 過濾,看所有 SMT(噪音多,研究用) |
| `--mode` | `latest` | `latest`=只看最近一筆 actionable;`scan`=列出全部歷史 |
| `--list-pairs` | — | 列出可用 pair 後結束 |

### 調參直覺

- **訊號太多/雜**:調大 `--swing-window` (7~10)、確保用預設 confirmation。
- **訊號太少/漏**:調小 `--swing-window` (3)、拉長 `--start` 區間。
- **你想抓更大行情**:`--rr-ratio 3`,但命中率會下降。
- **你交易時間短**:`--signal-ttl 5`,只要最快確認的訊號。

---

## 5. 讀懂 CLI 輸出

### 5.1 `latest` 模式

```text
Fetching SPY_QQQ: SPY / QQQ (US) 2024-04-10 → 2025-04-09 [1d]

Scanned 250 bars → 6 SMT event(s)

>>> LATEST ACTIONABLE SIGNAL
    2025-03-18  BULLISH  entry=562.10  stop=557.30  target=571.70  R:R=2.0
    ✓ 已被 BOS_up 確認 @ 2025-03-21
    ! 訊息僅供參考,非投資建議
```

解讀:
- 程式在 2025-03-18 發現 SPY/QQQ 的多頭 SMT。
- 3 天後(03-21)SPY 收盤突破最近 swing high,確認訊號。
- 建議進場 562.10、停損 557.30、目標 571.70,風險 4.80、目標 9.60。
- 你可自行選擇當下市價進、或等回測試停損附近進。

### 5.2 `scan` 模式

```text
  Date         Dir      Status                  Entry       Stop     Target  R:R   Age  Note
  ------------------------------------------------------------------------------------
✓ 2024-07-12   BEARISH  actionable            549.20     552.80     542.00   2.0    180  已被 BOS_down 確認 @ 2024-07-18
… 2024-11-02   BULLISH  pending_confirmation  580.10     576.30     587.70   2.0     90  等待 BOS/CHOCH 確認
x 2023-12-15   BULLISH  expired               470.40     467.50     476.20   2.0    240  已逾期,僅供歷史參考
```

- ✓ = actionable(SMT + 確認)
- … = pending_confirmation(SMT 出現但尚未確認,仍在 TTL 內)
- x = expired(超過 TTL,只能回顧學習)

---

## 6. 典型工作流

```bash
# 1. 先看有哪些 pair
python cli.py --list-pairs

# 2. 用預設最快檢查美股
python cli.py

# 3. 想看歷史訓練眼力
python cli.py --pair SPY_QQQ --mode scan --start 2023-01-01

# 4. 換台股
python cli.py --pair TSMC_0050 --mode scan

# 5. 想降低噪音,把 window 放大
python cli.py --swing-window 7

# 6. 研究時暫時放寬確認條件
python cli.py --no-confirmation --mode scan
```

---

## 7. 常見疑問

**Q. actionable 就該進場嗎?**
A. 否。actionable 只代表 SMT + 結構確認都到位,你仍須自行評估
   總體環境、事件風險、個人倉位。工具不替你按鈕。

**Q. 為什麼最新一天沒訊號?**
A. SMT 通常在 pivot 形成後才能偵測(swing 需要右側 N 根)。
   `swing_window=5` 代表至少要等 5 根 K 棒才能確定 pivot。

**Q. 停損為何是 pivot ±0.5% 而不是固定點數?**
A. 這是和 `smt_strategy.py` 回測一致的規則,確保「CLI 看到的」
   和「回測統計出的」是同一套邏輯。

**Q. TTL 過期的訊號有用嗎?**
A. 用來複盤:觀察當時確認是否出現、若出現 R:R 能否達成。
   是訓練盤感最好的材料。

---

## 8. 延伸閱讀

- ICT Mentorship (YouTube 免費) — Michael J. Huddleston 原始教學
- *Trading in the Zone* — Mark Douglas (交易心態)
- 本專案原始碼:
  - `core/swing.py` — swing 偵測
  - `core/smt_detector.py` — SMT 規則
  - `core/confirmations.py` — BOS / CHOCH
  - `signals/advisor.py` — 組合成帶價位的訊號
  - `strategies/smt_strategy.py` — 對應的回測策略

祝研究順利。再次提醒:**本工具僅供教育與訊號提示,交易自負盈虧。**
