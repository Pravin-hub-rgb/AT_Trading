# Plan: Prev-Pivot SL Mode

## Goal

Add a new `sl_mode` option `prev_pivot` that places SL at the most recent opposing pivot level (from the WalkerEngine) with a configurable point buffer.

## Context

We just ported the WalkerEngine to Python. It tracks high/low pivots as they form during the session. These pivots can be used to place SL closer to the action instead of using the avg-candle-size method.

## Data Flow

```
5min candles → WalkerEngine tracks pivots
                    ↓
              normal_highs (list of recent high pivots)
              normal_lows  (list of recent low pivots)
                    ↓
              At entry: pick most recent opposing pivot
                    ↓
              SL = pivot + buffer (below for long, above for short)
```

## Changes

### 1. `backend/src/intraday.py`

**Config update** — add `prev_pivot` to SL_MODE_MULT dict and SL_MODE_FIXED:

```python
SL_MODE_MULT = {"avg": 1.0, "avg075": 0.75, "avg05": 0.5}
SL_MODE_FIXED = {"fixed8": 8.0}
# New: no mult needed — uses fixed buffer
```

**New constant:**

```python
SL_PIVOT_BUFFER = 1.0   # points below/above the pivot for SL
```

**New config option (optional):**

```python
DEFAULT_CFG = {
    ...
    "sl_pivot_buffer": 1.0,   # buffer in absolute points
}
```

**Run WalkerEngine during simulate_day** — feed 5min candles to walker, collect pivots as they form:

```python
walker = WalkerEngine()
pivots: list[AlgoPivot] = []

while i < len(candles):
    cur = candles[i]
    walker_pivots = walker.process_bar(FlowCandle(...), i)
    for p in walker_pivots:
        if p.kind == "H":
            # track in normal_highs pool
        else:
            # track in normal_lows pool

    # On entry trigger, compute SL:
    # For BUY (long): latest normal_highs pivot + buffer
    # For SELL (short): latest normal_lows pivot - buffer
    if cfg["sl_mode"] == "prev_pivot":
        if dirn == 1:  # long
            ref = normal_highs[-1].px + cfg.get("sl_pivot_buffer", SL_PIVOT_BUFFER)
        else:
            ref = normal_lows[-1].px - cfg.get("sl_pivot_buffer", SL_PIVOT_BUFFER)
        sl = ref - 0  # use ref directly as the SL reference
```

**Update `_open_trade` to handle new mode:**

- When `cfg["sl_mode"] == "prev_pivot"`: compute SL from walker pivot + buffer
- Risk = entry - SL (for longs), SL - entry (for shorts)
- Target still = entry + RR_TARGET \* risk

**Track pivot pools per direction:**

- Need to know the most recent pivot for the OPPOSITE direction at entry time
- E.g., for a BUY entry: need the most recent HIGH pivot (normal_highs)
- For a SELL entry: need the most recent LOW pivot (normal_lows)
- Pivots accumulate in the pools as the session progresses

### 2. `backend/server.py` (if needed)

- Update API/docs if `sl_mode` accepts new values

## Open Questions

1. Should buffer be configurable per-entry or global config?
2. Should we use micro pivots as well (not just walker-sealed pivots)?
3. If no pivot exists yet (early entry before first pivot forms), fallback to avg mode?

## Decision

- Buffer = configurable via `sl_pivot_buffer` config (default 1.0)
- Only walker-sealed pivots (normal_highs/lows), not micro
- Fallback to `avg` if no pivot exists yet
- `sl_mode = "prev_pivot"` as new named option
