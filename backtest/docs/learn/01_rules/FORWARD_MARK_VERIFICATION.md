# Forward Mark Verification Log

Daily verification of swing marks against TradingView's BTCUSDT.P chart.

**Timezone**: India Standard Time (IST, UTC+05:30).
**Engine**: `src/firstswing.py::SwingEngine` via `backend/src/btc/btc_swing.py::compute_btc_swings`,
minBars=50, timeCap="00:00" (24/7). Engine is parity-tested between backtest and live paths.

## 2026-10-20

### Method

1. `exp_oct20_marks.py` loads IS+forward 15m CSVs concatenated (same as `exp_forward_eval.py`).
2. Computes the continuous swing chain (minBars=50, 24/7).
3. Filters swings where `confirmed_at_time` starts with `2026-10-20`.

### Engine Output (3 marks)

| swing# | confirmed (IST) | dir | kind | break_kind | pivot start | pivot end |
|---|---|---|---|---|---|---|
| 2912 | 2026-10-20 02:30:00 | down | FS | FLIP | 83069.4 @ 10-19 15:00 | 81668.0 @ 10-19 21:30 |
| 2913 | 2026-10-20 15:30:00 | down | FS | B2 | 82248.6 @ 10-20 03:45 | 81150.0 @ 10-20 06:30 |
| 2914 | 2026-10-20 20:30:00 | up | FS | B2 | 81174.1 @ 10-20 06:45 | 83429.2 @ 10-20 20:15 |

### TradingView Cross-Check

Open [BTCUSDT.P](https://www.tradingview.com/symbols/BTCUSDT/) on a 15-minute chart,
timezone IST. Verify:

1. **Swing #2912 (FLIP, down, confirmed 02:30)**:
   - A previous up-swing high was established at 83069.4 around 10-19 15:00.
   - Price broke below that high (FLIP) and the down-swing completed at 81668.0 on 10-19 21:30.
   - On the chart: look for the pivot-low that formed after the break — the FLIP cross should
     be visible as a failed retest of the prior high.

2. **Swing #2913 (B2, down, confirmed 15:30)**:
   - The down-swing from #2912 left a B1 break at the swing start (82248.6 @ 10-20 03:45).
   - A B2 break extended lower to 81150.0 @ 10-20 06:30.
   - On the chart: two consecutive lower-extreme breaks within the same down-swing.

3. **Swing #2914 (B2, up, confirmed 20:30)**:
   - Down-swing #2913 ended at 81150.0 (10-20 06:30).
   - An up-swing began, B1 at 81174.1, then B2 extended to 83429.2 @ 10-20 20:15.
   - Confirmed 30 minutes later at 20:30.

### Raw Data Files

- `backtest/forward_oct20_marks.csv` — swing-level marks (3 rows)
- `backtest/forward_oct20_bars.csv` — per-bar table with OHLC + mark indicators (96 candles)
- `backtest/forward_oct20_marks.json` — combined JSON (swings + per_bar)
- `backtest/tests/exp_oct20_marks.py` — extraction script

### Per-Bar Mark Table (Oct 20, 15m candles, IST)

Candles marked with FLIP or B2+ (up) / B2- (down) carry a swing mark:

| Bar | Time (IST)         | Open    | High    | Low     | Close   | Mark     |
|----:|--------------------|--------:|--------:|--------:|--------:|----------|
| 11  | 2026-10-20 02:30   | 82000.0 | 82156.2 | 81985.0 | 82152.2 | FLIP     |
| 63  | 2026-10-20 15:30   | 81459.3 | 81588.0 | 81438.3 | 81566.0 | B2- (↓)  |
| 83  | 2026-10-20 20:30   | 83232.0 | 83275.0 | 82162.0 | 82382.3 | B2+ (↑)  |

**To verify on TradingView**: Open BTCUSDT.P on a 15-minute chart (timezone IST), scroll to Oct 20, and confirm:
1. The FLIP mark at 02:30 aligns with a failed retest of the prior swing high
2. The B2- mark at 15:30 is the second consecutive lower-extreme break in the down-swing
3. The B2+ mark at 20:30 is the second consecutive higher-extreme break starting the up-swing from 81150

### Checklist

- [ ] FLIP mark at 02:30 visible on chart (swing #2912)
- [ ] B2 mark at 15:30 visible on chart (swing #2913)
- [ ] B2 mark at 20:30 visible on chart (swing #2914)
- [ ] All pivot levels match TradingView OHLC
