# Swing Mode Refactor — 31 Aug 2026

## Context

User wants to **simplify swing_mode** by replacing it with AGGRESSIVE/CONSERVATIVE based on cases. The cases (B1-Bc9) are the source of truth.

## User's Clarified Logic

For BULLISH bias:

### CONSERVATIVE (when first swing is also buying)

```
Bias = Buying, First Swing = Buying → SAME DIRECTION

Step 1: Wait for opposite swing (SELLING) to form
Step 2: Check if second swing is SELLING:
  - If SELLING → ENTER on SECOND pivot break (not first)
  - If BUYING → NO TRADE
```

### AGGRESSIVE (when first swing is selling - against bias)

```
Bias = Buying, First Swing = Selling → OPPOSITE DIRECTION

Step 1: First swing = selling = already the counter-trend
Step 2: ENTER on SECOND pivot break (not first)
  - No need to wait for second swing, first swing IS the counter-trend
```

**Rule: ALWAYS enter on SECOND pivot break, NEVER first.**

The only difference:

- **CONSERVATIVE**: First swing = same as bias, wait for opposite swing, enter on its 2nd pivot break
- **AGGRESSIVE**: First swing = opposite to bias, enter on its 2nd pivot break (no waiting)

## Examples

### 19 Aug: Bias=Selling, First Swing=Selling → CONSERVATIVE

- First swing (09:30) is SELLING (same as bias) → CONSERVATIVE mode
- Wait for opposite (BUYING) swing to form
- 09:55: BUYING swing forms (opposite to bias) ✓
- 09:58: First pivot break (buying low) → IGNORE (first break)
- 10:02: Second pivot break → ENTER SHORT ✓

### 28 Aug: Bias=Selling, First Swing=Buying → AGGRESSIVE

- First swing (09:30) is BUYING (opposite to bias) → AGGRESSIVE mode
- First swing IS already the counter-trend
- 09:34: First pivot break (buying high) → IGNORE
- Next: Second pivot break → ENTER SHORT ✓

## Revised Case → Trade Mode Mapping

### AGGRESSIVE (first swing opposite to bias)

- B2: ▲ gap-up, FS=selling (against bias)
- B3: ▲ gap-down, FS=buying (against bias)
- Bc3: ▼ gap-up, FS=selling (against bias)
- Bc4: ▼ gap-up, FS=buying (against bias)

Wait, let me re-check. Looking at docs:

For BULLISH bias (▲):

- B1: gap-up, FS=buying → WITH FLOW (aggressive)
- B2: gap-up, FS=selling → AGAINST FLOW (wait for buying - opposite swing)
- B3: gap-down, FS=buying → WITH FLOW (aggressive)
- B4: gap-down, FS=selling → AGAINST FLOW (wait for buying - opposite swing)
- B5: flat, FS=buying → WITH FLOW (aggressive)
- B6: flat, FS=selling → AGAINST FLOW (wait for buying - opposite swing)

So:

- **AGGRESSIVE** = FS = SAME as bias (with flow)
- **CONSERVATIVE** = FS = OPPOSITE to bias (need to wait for opposite swing to come back)

Wait, this is different from what I had before. Let me re-read user's words:

```
buying conservative
first swing is also buying we wait for selling swing
if the second swing is also buying then we don't trade
if it is selling so now we enter on the second pivot break not first

now first is selling so now we don't wait for the second swing
we just enter on the second pivot .. thats' it
```

OK so:

**Case A: Bias=Buying, FS=Buying** (CONSERVATIVE)

- Wait for SELLING swing (opposite to bias)
- If 2nd swing is SELLING → enter on 2nd pivot break
- If 2nd swing is BUYING → no trade

**Case B: Bias=Buying, FS=Selling** (AGGRESSIVE)

- First swing IS already the selling retracement
- Don't wait for 2nd swing
- Enter on 2nd pivot break of first swing

So mapping:

### AGGRESSIVE (FS opposite to bias, first swing IS the counter-trend)

| Case | Bias | Gap  | FS      | Why Aggressive              |
| ---- | ---- | ---- | ------- | --------------------------- |
| B2   | ▲    | up   | selling | FS already opposite to bias |
| B4   | ▲    | down | selling | FS already opposite to bias |
| B6   | ▲    | flat | selling | FS already opposite to bias |
| Bc2  | ▼    | down | buying  | FS already opposite to bias |
| Bc4  | ▼    | up   | buying  | FS already opposite to bias |
| Bc6  | ▼    | flat | buying  | FS already opposite to bias |

### CONSERVATIVE (FS same as bias, need to wait for opposite swing)

| Case | Bias | Gap  | FS      | Why Conservative                  |
| ---- | ---- | ---- | ------- | --------------------------------- |
| B1   | ▲    | up   | buying  | FS same as bias, wait for selling |
| B3   | ▲    | down | buying  | FS same as bias, wait for selling |
| B5   | ▲    | flat | buying  | FS same as bias, wait for selling |
| Bc1  | ▼    | down | selling | FS same as bias, wait for buying  |
| Bc3  | ▼    | up   | selling | FS same as bias, wait for buying  |
| Bc5  | ▼    | flat | selling | FS same as bias, wait for buying  |

### UNBIASED (skip for 1-min)

| Case  | Action |
| ----- | ------ |
| U1-U5 | SKIP   |

## Key Insight: SECOND PIVOT BREAK ALWAYS

Regardless of aggressive or conservative, we always enter on the SECOND pivot break, never the first:

- **AGGRESSIVE**: FS opposite to bias → wait for FS's 2nd pivot break
- **CONSERVATIVE**: FS same as bias → wait for opposite swing's 2nd pivot break

The "second pivot break" is the key filter - it skips false breakouts.

## Implementation Plan

### Phase 1: Backend Simplification

```
[ ] Add CASE_TRADE_MODE dictionary (case_id → aggressive/conservative/skip)
[ ] Update classify_case() to return (case_id, trade_mode)
[ ] Remove swing_mode config field
[ ] Add trade_mode logic to simulate_day entry gate
[ ] Add pivot break counter (track #1 vs #2 break)
[ ] Add unbiased skip for 1-min
[ ] Remove detect_second_swing() call (replaced by simpler logic)
```

### Phase 2: Frontend Updates

```
[ ] Remove swing_mode dropdown
[ ] Update DEFAULT_BT_PARAMS (remove swing_mode)
[ ] Show case classification + trade_mode in UI
```

### Phase 3: Testing

```
[ ] Test 28 Aug (B6/aggressive): wait for 2nd pivot break of first swing
[ ] Test 19 Aug (Bc1/conservative): wait for opposite swing + 2nd pivot break
[ ] Test 25 Aug: identify case, verify behavior
[ ] Test unbiased days: SKIP for 1-min
```

## Code Changes

### File: backend/src/intraday.py

**Remove swing_mode default:**

```python
# OLD:
"entry_method": "pace_break",
"swing_mode": "opposite_swing_needed",

# NEW:
"entry_method": "pace_break",
# swing_mode removed - derived from case classification
```

**Add CASE_TRADE_MODE and update classify_case:**

```python
CASE_TRADE_MODE = {
    # AGGRESSIVE: FS opposite to bias, first swing IS counter-trend
    "B2": "aggressive", "B4": "aggressive", "B6": "aggressive",
    "Bc2": "aggressive", "Bc4": "aggressive", "Bc6": "aggressive",
    # CONSERVATIVE: FS same as bias, wait for opposite swing
    "B1": "conservative", "B3": "conservative", "B5": "conservative",
    "Bc1": "conservative", "Bc3": "conservative", "Bc5": "conservative",
    # UNBIASED: skip for 1-min
    "U1": "skip", "U2": "skip", "U3": "skip", "U4": "skip", "U5": "skip",
}

def classify_case(eff_bias, gap, extreme, swing_dir):
    """Returns (case_id, trade_mode)"""
    # ... existing case_id logic ...
    case_id = ... # B1, B2, etc.
    trade_mode = CASE_TRADE_MODE.get(case_id, "aggressive")
    return case_id, trade_mode
```

**Update entry gate logic:**

```python
# After classify_case:
case_id, trade_mode = classify_case(bias, gap, extreme, swing_dir)

# Skip unbiased for 1-min
if use_1m and trade_mode == "skip":
    return  # no entries

# Both modes: wait for SECOND pivot break
# Difference: which swing to monitor
if trade_mode == "aggressive":
    # FS opposite to bias = first swing IS counter-trend
    # Monitor FS's pivots, enter on #2 break
    monitored_swing = "first_swing"
    require_pivot_count = 2
elif trade_mode == "conservative":
    # FS same as bias = wait for opposite swing
    # Monitor OPPOSITE swing's pivots, enter on #2 break
    monitored_swing = "second_swing"  # the one opposite to FS
    require_pivot_count = 2
```

**Add pivot break counter:**

```python
# Track pivot break count for the monitored swing
pivot_break_count = 0  # reset when monitored swing changes

# In pivot break detection:
if pivot_broken:
    pivot_break_count += 1
    if pivot_break_count >= require_pivot_count:
        # ENTER!
```

### File: frontend/src/components/IntradayPanel.tsx

```typescript
// REMOVE SWING_MODES dropdown
// Remove swing_mode from saveFilters
```

### File: frontend/src/app/chart/page.tsx

```typescript
// REMOVE swing_mode from DEFAULT_BT_PARAMS
```

## Examples Walkthrough

### 28 Aug (B6: ▲ FLAT SELLING-FIRST) - AGGRESSIVE

```
1. FsV2 detects first swing = SELLING (09:30)
2. Case = B6, trade_mode = AGGRESSIVE
3. Monitor first swing's pivots
4. 09:34: First pivot (high 24154.9) broken → IGNORE (count=1)
5. Next pivot break → ENTER SHORT (count=2)
```

### 19 Aug (Bc1: ▼ GAP-DOWN SELLING-FIRST) - CONSERVATIVE

```
1. FsV2 detects first swing = SELLING (09:30)
2. Case = Bc1, trade_mode = CONSERVATIVE
3. Monitor OPPOSITE swing (BUYING) - wait for it to form
4. 09:55: BUYING swing confirmed (opposite to bias)
5. 09:58: First buying pivot (low 24175) broken → IGNORE (count=1)
6. 10:02: Second buying pivot broken → ENTER SHORT (count=2)
```

## Files to Modify

1. **backend/src/intraday.py** - main changes
2. **backend/src/intraday_1m.py** - may need updates for 1-min
3. **frontend/src/components/IntradayPanel.tsx** - remove swing_mode UI
4. **frontend/src/app/chart/page.tsx** - remove swing_mode defaults
5. **docs/entry theory.md** - simplify concept docs
6. **docs/cases.md** - add trade_mode field

## Risks

- **Pivot break counting** in 1-min data: need to track which pivot belongs to which swing
- **Color changes** (swing voids) reset counters
- **WalkerEngine** pivots are per-timeframe - need to map to monitored swing
- **Backtest regression**: existing cases may break, need before/after comparison
