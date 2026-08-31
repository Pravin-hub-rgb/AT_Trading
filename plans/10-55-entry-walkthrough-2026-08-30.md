# Why the 10:55 Entry Fired on 2026-08-28

**Settings:** `execution = precise_1min`, `entry = pace_break`, `swing_mode = opposite_swing_needed`, `sl = avg x 1`

---

## The Two Swings

### Cyan Line — First Swing (ENTRY GATE)

- `first_swing_confirmed_idx = 14`
- Day 5-min bar #14 closes at **2026-08-28 10:25**
- Direction declared: **buying** (up)
- `first_swing_end_time = 10:15`

This is the **entry gate**. No trade can fire before bar 14.

### Yellow Line — Second Swing (DIRECTION FILTER only)

- `swing2_confirmed_idx = 3`
- Day 5-min bar #3 closes at **2026-08-28 09:30**
- Direction declared: **selling** (down) — opposite to cyan line

Since yellow is opposite to cyan, `second_swing_armed` fires. The trade direction will be **buying** (from the cyan/first swing). The yellow line does NOT open the gate — it only confirms the direction alignment.

---

## Gate Timeline

| Time      | 5-min Bar  | Event                                  | Gate Status                    |
| --------- | ---------- | -------------------------------------- | ------------------------------ |
| 09:30     | bar 3      | Second swing (yellow) confirms selling | gate = 14 (FS1 not yet)        |
| 09:50     | bar ~5     | Trade attempted                        | **BLOCKED** (bar 5 < gate 14)  |
| 10:20     | bar ~16    | Trade attempted                        | **BLOCKED** (bar 16 < gate 14) |
| **10:15** | **bar 14** | **First swing (cyan) confirms buying** | **GATE OPENS**                 |
| 10:50     | bar 19     | Pace break domination detected         | gate = 14, bar 19 > 14 = OK    |
| 10:55     | bar 19     | 1-min bar closes, entry fires          | **TRADE OPENS**                |

---

## Step-by-Step: How the 10:55 Entry Happened

### 1-min Candles around 10:50-10:55

```
10:49  O=24158.25  H=24165.65  L=24156.85  C=24163.40  <- domination forming
10:50  O=24163.95  H=24168.90  L=24163.10  C=24167.10
10:51  O=24168.15  H=24170.60  L=24164.95  C=24165.35
10:52  O=24165.70  H=24166.10  L=24162.00  C=24162.90
10:53  O=24163.40  H=24164.70  L=24159.60  C=24159.75
10:54  O=24160.15  H=24162.20  L=24155.45  C=24155.60  <- low = 24155.45 (domination level!)
10:55  O=24157.00  H=24157.00  L=24149.75  C=24150.65  <- closes at 24150.65
```

### Bar 19 (10:50 5-min bar) — Pace Break Detected

At 10:50, the engine sees a **domination pace break**:

```
{'type': 'pace_break', 'bar': 19, 'time': '10:50',
 'break_type': 'domination', 'level': 24155.45,
 'swing_before': 'buying', 'swing_size': 81.75,
 'aligned_with_bias': True}
```

- Level = **24155.45** (the low of the previous 5-min bar, serving as support)
- Break type = **domination** (price dominating below a level)
- `aligned_with_bias = True` — the domination direction is consistent with the day's short-term bias

**BUT the trade does NOT fire yet.** This is the "precise 1-min" mechanic. The engine sees the setup at 10:50, but defers entry until the next 1-min bar closes to confirm.

`pending_direct_1m` is armed:

```
{'type': 'pending_direct_1m', 'bar': 19, 'time': '10:50',
 'ts': 1787894400, 'level': 24155.45, 'break_type': 'domination'}
```

### Bar 19 Again (next 5-min iteration at 10:55) — Entry Fires

The engine processes bar 19 again as it moves forward. Now the pending_direct check runs:

```
m1_bar = resolve_pending_direct(pending_direct, m1_day, cur["ts"])
```

The 1-min bar at 10:55 has:

- Open 24157.00, High 24157.00, Low **24149.75**, Close **24150.65**
- Low (24149.75) broke below armed level (24155.45) — domination confirmed ✓
- Bar timestamp ≤ current 5-min bar timestamp ✓

All checks pass:

- `gate_ok`: bar 19 > gate bar 14 → **OPEN** ✓
- `window_ok`: 10:55 inside 09:15–15:30 → **OPEN** ✓
- `entries_ok`: first entry of the day → **OPEN** ✓

**→ Trade opens:**

```
{'type': 'entry', 'bar': 19, 'time': '10:55:00',
 'dir': 'short', 'price': 24150.65, 'sl': 24184.01, 'target': 24050.57}
```

Direction is **short** (selling). This is because the domination break was a downward break of the level — the pace_break signals a short-term bearish pullback within the up-trend. The SL is 24184.01 (above entry, for a short), target is 24050.57.

### Outcome

The trade exited at 11:00 as **ft_fail** (follow-through failure) at 24160.25 for **-0.29R**. Price bounced back up after the initial breakdown — the follow-through never arrived.

---

## Why Wasn't the 9:50 and 10:20 Entry the First Trade?

Both were blocked by the gate:

- **9:50** (bar ~5): `bar 5 < gate bar 14` → `setup_disarmed_pre_gate` → `pending_direct = None`
- **10:20** (bar ~16): `bar 16 < gate bar 14` → `setup_disarmed_pre_gate` → `pending_direct = None`

The first swing (cyan) hadn't confirmed yet. The system was in waiting mode. Once bar 14 closed at 10:25 confirming the first swing, the gate opened and the next valid pace_break could fire.

---

## Key Files

- Walkthrough script: `backend/debug/_ss_walk_10_55.py`
- Output: `backend/debug/_walk_10_55_out.txt`
- Gate fix: `backend/src/intraday.py` lines 873-891
- Defensive pending_direct fix: `backend/src/intraday.py` lines 989-1024
