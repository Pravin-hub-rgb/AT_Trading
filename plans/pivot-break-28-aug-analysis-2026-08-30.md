# Why pivot_break didn't fire on 2026-08-28

**Settings:** `execution = precise_1min`, `entry = pivot_break`, `swing_mode = opposite_swing_needed`, `sl = avg x 1`

---

## What pivot_break requires

The `pivot_break` entry method (see [`detect_pivot_break` in `backend/src/intraday.py:469-494`](backend/src/intraday.py:469)) is more conservative than `pace_break`:

- It requires a **sealed LOW pivot** (from WalkerEngine) to exist first
- It requires the **5-min bar's CLOSE** to break below that sealed LOW

```python
if normal_lows and cur["close"] < normal_lows[-1].px:
    return {"type": "pivot_break", "level": normal_lows[-1].px, "bar": i}
```

This is fundamentally different from `pace_break` (which uses the bar's LOW, not CLOSE) and doesn't have 1-min precision — it waits for a full 5-min bar close.

---

## What happened on 28 Aug

### Timeline after gate opened (bar 14, 10:25):

| Bar | Time  | Event                                | What happened                                            |
| --- | ----- | ------------------------------------ | -------------------------------------------------------- |
| 15  | 10:30 | `pivot_break` armed at level 24161.5 | WalkerEngine sealed a LOW pivot; 5-min close broke below |
| 17  | 10:40 | `domination` at 24156.15             | The low kept going down but the 5-min close didn't seal  |
| 19  | 10:50 | (no pivot_break event)               | The 5-min bar closed higher than the armed level         |
| 28  | 11:35 | `setup_disarmed` (timeout)           | Setup aged out — `SWING_TIMEOUT_CANDLES` exceeded        |
| 39  | 12:30 | `setup_disarmed` (swing_voided)      | The swing structure was cancelled                        |

### Why no entry fired

1. **Bar 15 (10:30) armed a pivot_break** at level 24161.5 — this was a valid SHORT setup
2. The system needed a 5-min bar to **close** below 24161.5
3. Bars 16-19 had LOWs that went down to 24149.75 (at 10:55 1-min), but their **5-min CLOSES** stayed above 24161.5
4. The setup timed out at bar 28 (11:35)
5. The swing was then voided at bar 39 (12:30) — the trend structure broke down

**Key insight:** `pivot_break` uses 5-min bar CLOSES, not 1-min lows. The 1-min precision path (which gave us the 10:55 short on `pace_break`) doesn't apply to `pivot_break` because the engine waits for the full 5-min bar to confirm.

---

## Comparison: pace_break vs pivot_break on 28 Aug

| Method      | Entry fired? | Time              | Reason                                                        |
| ----------- | ------------ | ----------------- | ------------------------------------------------------------- |
| pace_break  | YES          | 10:55 (1-min bar) | Domination at 24155.45 confirmed by 1-min close at 24150.65   |
| pivot_break | NO           | —                 | 5-min bar never CLOSED below the armed level; setup timed out |

This is consistent with the design: `pivot_break` is the conservative version that requires 5-min bar confirmation. On a day with shallow pullbacks (28 Aug), `pivot_break` skips the trade because the 5-min structure never broke down, while `pace_break` catches the 1-min precision entry.

---

## Should we make pivot_break use 1-min precision too?

This is a design question. Currently:

- `pace_break` + 1min = uses 1-min precision entry hunt
- `pivot_break` + 1min = still uses 5-min bar CLOSE for the break detection

If you want `pivot_break` to also use 1-min precision, the change would be in `detect_pivot_break` at line 469 — instead of `cur["close"] < normal_lows[-1].px`, it would arm a pending_direct and wait for the next 1-min bar to close below the level.

This is a separate feature from the swing gate fix. Let me know if you want me to implement it.
