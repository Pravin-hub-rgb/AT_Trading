# PLAN — Nifty Overview + Aggressive Entry Backtester (Paper Bot)

## 1. Goal

Ayush Thakur ki theory (entry part 1 & 2) ko **code me lock** karke **stale data pe validate** karna. Valid ho toh Upstox live paper bot (signals + paper fills). **No real orders, no UI — data only.**

Flow:
1. Data download (daily + 5-min)
2. Overview nikalna (zone theory)
3. Overview ke according intraday aggressive entry logic test (backtest)
4. Agar expectancy positive + human check sahi → live paper bot (Upstox)

---

## 2. Source Material

| File | Content |
|------|---------|
| `entry english 1.md` | 3 entry types, halt analysis, aggressive entry rules |
| `entry english 2.md` | Failure cases, panic selling, flip/reversal logic |
| `talk.md` | Zone theory (1-5) + open doubts |
| `Start.md` | Fib box theory (33%/66%) + swing S/R (darshakssc ref) |
| `script for swing high and low.md` | Script recommendations — **darshakssc pivot logic ko hum khud Python me port karenge** (TradingView ki zaroorat nahi) |
| `getting ohlcv data of 5min candle.md` | Upstox V3 API limits — data plan ka basis |

---

## 3. Data Plan

- **Instrument**: Nifty 50 → `NSE_INDEX|Nifty 50`
- **Daily candles**: ~1.5-2 saal (zones ke liye)
- **5-min candles**: ~1.5 saal target (entry backtest ke liye)
- **Source**: Upstox V3 Historical Candle API
  - Endpoint: `GET https://api.upstox.com/v3/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}`
  - Interval: `minutes/5`
  - ⚠️ **Limit: 5-min ke liye max 1 month per request** → month-by-month loop (~18 calls for 1.5 saal)
  - Data availability: **January 2022 se** — toh 1.5 saal easily mil jayega
  - Response: `[timestamp, open, high, low, close, volume, oi]`
  - Rate limits ka dhyan — aggressive requests nahi
- **Warm-up period**: pehle ~6 mahine sirf zone-history building (no trades)
- **Tradeable window**: uske baad ~1 saal — jab zones "proper" ho jate hain (expanding window se)
- Storage: `data/nifty_daily.csv`, `data/nifty_5min.csv`
- **Step 1: API limit verify** — kitni history actually milti hai, windows uspe fix

---

## 4. Swing Detection (darshakssc port)

- **Pivot fractals**: candle jiska high/low > N bars (left & right) se extreme — N configurable (default 3-5)
- Swing high/low series → structure labels (HH/HL/LH/LL)
- S/R candidates: swing lows = support, swing highs = resistance
- **Zone clustering**: nearby pivots merge (touch strength = kitni baar test hua)
- Output: `zones.csv` + optional HTML chart per day (manual verification)

---

## 5. Overview Engine — ⚠️ OPEN DECISION

| Method | Source | Status |
|--------|--------|--------|
| **A. Zone method** (1-5 zones) | talk.md | **Recommended** — Ayush-aligned (major R break + successful close = buying), defined, codable |
| **B. Fib box method** (33%/66%) | Start.md | Apni own theory, untested — Phase 2 me A/B add |

**Recommended path:** A pehle, B modular add-on (baad me A/B compare). Combo option: A + "recent major break + successful daily close" booster (Ayush ka overview confirmation).

**Zone rules (talk.md, exact):**
| Zone | Definition | Bias |
|------|-----------|------|
| 1 | Above major R (breakout) | **BUYING** |
| 2 | Near R (top 20% of range, below R) | **SELLING** (pull-down force) |
| 3 | Mid 60% of range | **NO TRADE** (log only) |
| 4 | Near S (bottom 20% of range, above S) | **BUYING** (push-up force) |
| 5 | Below major S (breakdown) | **SELLING** |

⚠️ **No lookahead**: har day ka zone sirf **us day tak ke data se** (expanding window) — warm-up period isi liye chahiye.

---

## 6. Intraday Entry State Machine (5-min)

Per day with bias (selling = mirror):

```
IDLE → FIRST_SWING → HALT (2+ candles; single candle INVALID)
     → RETRACEMENT → CONFIRMATION (>70% reversal) → IN_TRADE
     → EXIT (SL | panic flip | day end)
```

**Rule 1 — First swing = BUYING (N-pattern):**
Buying swing → halt → first selling retracement → support form → candle reverses selling candle/swing **>70%** → BUY on candle close. SL = nearest swing low. Expectation = intraday high breakout. *(entry english 1.md:167-170)*

**Rule 2 — First swing = SELLING (NOT direct buy):**
Selling swing → reversal aaye + **halt confirmation** (2 candles stand; single candle reversal invalid) → buying side confirmed. Agar price high level pe / nearest swing low door → **ek retracement ka wait** → support + >70% reversal → BUY on close. *(entry english 2.md:79-85)*

**Rule 3 — SL hit → exit, day done** (no second-guessing, risk management first). *(entry english 2.md:91)*

**Rule 4 — Panic flip:**
Buying swing ka **first swing low break** → naya support form → wo support break (bade candles = panic) → **exit + flip short**. Momentum-base logic: fall me choti candles (buyers absorbing) = support forming; us support ka breakdown = panic confirmation. *(entry english 2.md:103-137)*

**Config toggles (backtest me compare):**
- "70% of selling candle" vs "70% of selling swing"
- Halt: 2 vs 3 candles
- Zone 1/5 vs Zone 2/4 stats split

---

## 7. Backtest Engine

- Har bias day pe: daily overview (prev close se) + 5-min state machine run
- Entries on candle close; SL/panic on candle extreme touch
- Logs:
  - `signals.jsonl` — har state change + reason
  - `trades.csv` — date, zone, side, entry, SL, exit, reason, P&L
- Zone 3 days: no trade, sirf overview log
- No fills complexity, no slippage/fees (pehle phase me pure signal validation)

---

## 8. Stats & Validation

- Win rate, avg RR, expectancy
- **Zone-wise split** (1/5 vs 2/4) — agar 2/4 kharaab nikle, wahi hata denge
- Monthly breakdown
- 5-10 random days ke charts (entry/SL/flip marked) — **manual human check** (plotly HTML, TradingView jaisa)
- **Decision gate**: expectancy > 0 + charts sahi → live paper phase

---

## 9. Future (Post-Validation)

- Upstox websocket (real-time feed) → live paper bot — **same engine**, config switch (backtest/live)
- Real-time state machine pe har signal push + paper fills + daily report
- Zone 2/3/4 ko dheere dheere refine (jab zone 1/5 validated ho)

---

## 10. Planned File Structure (future, coding phase me)

```
AT_Trading/
  bot/
    config.py          # intervals, thresholds, warm-up days
    fetch_data.py      # Upstox V3 API → data/ (month-by-month loop)
    swing.py           # pivot/zone detection (darshakssc port)
    overview.py        # zone classification per day (no lookahead)
    state_machine.py   # intraday entry rules
    backtest.py        # per-day engine
    stats.py           # metrics + reports
    charts.py          # plotly HTML (optional check)
    .env               # Upstox creds (gitignored)
  data/                # nifty_daily.csv, nifty_5min.csv
  output/              # overview.csv, trades.csv, signals.jsonl, charts/
  PLAN.md              # yeh doc
```

---

## 11. Open Questions

1. **Overview method**: A (zone) / B (fib) / combo — *recommendation: A pehle*
2. Upstox 5-min history kitni din actually milti hai → Step 1 me verify, windows uspe fix
3. Halt "significant" ka threshold: candle-size / retracement-depth minimums (backtest me tune)

---

## 12. Milestones

- **M1**: Data download + limits verified (Upstox V3, month-by-month loop)
- **M2**: Swing/zone detection + `overview.csv` (warm-up aware, no lookahead)
- **M3**: State machine backtest + `trades.csv` + `signals.jsonl`
- **M4**: Stats + charts + decision gate (expectancy, human check)
- **M5** (conditional): Upstox live paper bot — same engine, websocket real-time
