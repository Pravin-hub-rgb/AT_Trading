# Crazy Research Ideas — BTC Swing Engine (9 months, 24/7)

> **Data:** `data/btc/BTCUSDT_5m.csv` 78,493 rows + `BTCUSDT_15m.csv` 26,165 (BTCUSDT, continuous 24/7, IST wall-clock).  
> **Period:** 2025-01-01 05:30 → 2025-10-01 05:25 IST (~9 months, 274 calendar days).  
> **Engine:** `backend/src/btc/btc_swing.py` `compute_btc_swings` (SwingEngine `minBars 14 sustain 7 timeCap 00:00`, ONE continuous chain — no daily reseed, `swing_index` never resets).  
> **Sim:** mirrors `backend/src/btc/btc_engine.py::simulate_btc_trades` — entry on break-bar close, SL at triggering swing's start extreme, BE after +1R, one position at a time, conservative fills (SL checked before target, gap fills at open).  
> **Generated:** 2026-09-05 via `fix/btc_sweep.py` (S1–S5) + `fix/btc_sweep2.py` (combos). Raw output: `fix/btc_sweep_out.txt`, `fix/btc_sweep2_out.txt`.

---

## 0. TL;DR — Most Profitable Setups Found

### ✅ CURRENT (2026-09-06) — LIVE-FAITHFUL numbers, costs included
**What the UI / Master dropdown shows today** — stream entries (incl. pre-start churn
marks) + 1m-precise fills + 0.05%/side + 2pt slippage, FULL Jan-25→Sep-26 window
(bull 2025 + bear 2025-26):

| # | Preset | TF | Tr | Win% | Base R | **NET R** |
|---|--------|-----|-----|------|--------|-----------|
| 1 | **Flip Fixed 3R** | 1h | 94 | **44.7%** | +64.8 | **+55.0** |
| 2 | Decisive Trail 30 | 1h | 287 | 15.3% | +69.7 | +44.5 |
| 3 | Decisive Trail 50 | 15m | 847 | 11.2% | +157.4 | +19.0 |
| 4 | Sniper 3R | 15m | 330 | 22.7% | +75.0 | +7.0 |
| 5–12 | baaki presets | — | — | — | — | −3.5 … −321.9 |

**In one line:** after the engine became fully live-faithful (every B2/FLIP a live
trader would see is a trade, resolved on 1-minute candles, minus real costs), the
**#1 pick is `Flip Fixed 3R (1h)`** — highest win rate (44.7%), lowest fee drag, and
the only setup that shrugs off the churn/fakeout cost. The 15m flagships (Decisive
Trail 50) still hold (+19R NET) but are far thinner than their zero-cost cousins below.

> Full audit trail + old numbers: §8.4 (cost reality), §8.11 → §8.12 (SL + churn fixes).

### ⚠️ HISTORICAL — original sweep era (2025-09, signal-TF fills, ZERO costs, retrospective "final" selection)
These were the numbers that built the page. **Do NOT read them as live expectations** —
fees and 1m precise fills flipped several of them negative (see §8.10/§8.12).

| Rank | Config | Trades | Win% | TotalR | Avg R | PF |
|------|--------|--------|------|--------|-------|-----|
| 🥇 most R | **minBars20 + decisive break + SL swing + SWING-TRAIL + BE1** | 1720 | 13.4 | **+392.9** | +0.228 | 2.24 |
| 🥈 best PF (high vol) | **minBars14 + FLIP break + SL swing + SWING-TRAIL + BE1** | 1049 | 14.8 | +340.8 | **+0.325** | **2.51** |
| 🥉 best per-trade | **minBars20 + FLIP + fixed 3R + BE1 + 15m bias + streak regime** | 161 | 26.7 | +77.0 | **+0.478** | 2.48 |
| baseline (ship default) | decisive + SL swing + fixed 3R + BE1 | 557 | 19.8 | +67.9 | +0.122 | 1.26 |

**The single biggest edge was SWING TRAILING** (SL ratchets to confirmed swing pivots
instead of a fixed 3R target) in the zero-cost world — **+378R vs +68R baseline, a 5.6x
improvement**. Fixed-RR targets cap BTC's trend legs; trailing lets them run. At real
costs that edge mostly gets eaten by fees on 15m; the 1h fixed-3R design keeps the
capture without the fee bleed.

---

## 1. Stats — Swing Structure (whole series, continuous chain)

* **Total swings: 3,620** (5m chain) — up 1,821 (50.3%) / down 1,799. Perfectly balanced.
* **15m swings: 1,224** (bias timeline source).
* **Break kinds: B2 2,046 (56.5%) / FLIP 1,574 (43.5%) / B1 0** — on BTC with `timeCap 00:00` the extreme-break B1 mark NEVER fires; every swing confirms via the pivot-break chain (B2) or a FLIP.
* **Confirm source: FS 100%** — `sustainBars` is a NO-OP on BTC (see §3). Every swing confirms by break, never by N-bar sustain.
* **Leg size (start→end):** mean 884 pts, median 683, p25 441, p75 1,070, p90 1,652.
* **Leg/ATR(14):** mean 5.75, median **5.27**, p25 4.10, p90 8.89 — BTC 5m legs are HUGE relative to ATR (Nifty first-swing median ~105 pts). There are **no weak swings on BTC 5m** — the `minBars 14` gate forces every leg to be a real move.
* **Consecutive structure:** next swing SAME dir as prev: **40.7%** (Nifty: 42.0% — nearly identical!). 3-in-a-row same: **15.8%** (Nifty: 16.0%). The swing rhythm of BTC matches Nifty almost exactly — same engine behavior, just on bigger legs.
* **Daily candles:** 274 days — green 142 (51.8%) / red 132. Color streaks: mean 1.77, max 8, ≥3-long streaks: 28.

> **Crazy take:** BTC swing stats mirror Nifty's (40.7% vs 42% same-dir, 15.8% vs 16% 3-in-row) — the swing chain is a universal market structure readout. But BTC legs are 5+ ATR, so fixed R targets leave 70%+ of the move on the table → trailing is where the money is.

---

## 2. Core Grid Sweep — `entry_break × sl_mode × rr × trailing × breakeven` (108 combos)

Top 10 of 108, sorted by TotalR:

```
decisive slSwing rr2 swing be1    Trades 1906  Win% 13.9  TotalR +378.32  PF 2.05  [trail 1593 be 298 sl 15]
decisive slSwing rr3 swing be1    Trades 1906  Win% 13.9  TotalR +378.32  PF 2.05
decisive slSwing rr4 swing be1    Trades 1906  Win% 13.9  TotalR +378.32  PF 2.05
flip     slSwing rr2 swing be1    Trades 1049  Win% 14.8  TotalR +340.80  PF 2.51  avg +0.325
flip     slSwing rr3 swing be1    Trades 1049  Win% 14.8  TotalR +340.80  PF 2.51
flip     slSwing rr4 swing be1    Trades 1049  Win% 14.8  TotalR +340.80  PF 2.51
flip     slSwing rr2 swing be0    Trades  999  Win% 17.2  TotalR +320.49  PF 2.17
decisive slSwing rr2 swing be0    Trades 1773  Win% 15.9  TotalR +298.37  PF 1.72
flip     slSwing rr3 off  be0     Trades  488  Win% 36.1  TotalR +217.00  PF 1.70
flip     slSwing rr2 r1   be0     Trades 1016  Win% 44.0  TotalR +210.36  PF 1.67
...
BASELINE decisive slSwing rr3 off be1   Trades 557  Win% 19.8  TotalR +67.89  PF 1.26  [sl 262 be 184 target 110]
```

**Findings:**
1. **`trailing=swing` dominates everything.** With swing trailing, `rr` is irrelevant (target never reached — trail always exits first): identical numbers for rr2/3/4.
2. **`sl_mode=pct` (fixed 0.5%) is garbage on BTC** — no pct config makes the top 10. Swing-origin SL is correct: the leg origin is the real invalidation point.
3. **BE1 (breakeven at +1R) strictly helps** with swing trail: be1 +378 vs be0 +298 (decisive). The 298 BE exits convert would-be SLs into zeros.
4. **FLIP entries = fewer, better trades.** decisive 1,906 trades → +378R (avg 0.198); FLIP-only 1,049 trades → +341R (avg 0.325, PF 2.51). FLIP is the "trend actually flipped" confirmation.
5. Fixed 3R (`off`) caps winners hard — only 157 targets vs 293 SLs at baseline. BTC legs routinely run >>3R.

---

## 3. Engine Params — `minBars × sustainBars`

| Config | Swings | Trades | Win% | TotalR | PF |
|--------|--------|--------|------|--------|-----|
| minBars7 sustain3/7/10 | 3,820 | 575 | 18.6 | +51.00 | 1.19 |
| **minBars14 (default)** sustain3/7/10 | 3,620 | 557 | 19.8 | +67.89 | 1.26 |
| **minBars20** sustain3/7/10 | 3,252 | 556 | 21.1 | **+97.00** | **1.38** |

* **`sustainBars` is a total no-op on BTC** — identical results for 3/7/10, because with `timeCap 00:00` every swing confirms via break (FS 100%) and sustain never gets a chance. (On Nifty, sustain confirmations happen constantly before the 09:29 timeCap.)
* **`minBars20` > `minBars14` > `minBars7`**: fewer, cleaner swings = +43% more R at the same trade count. Bigger minimum legs filter chop. Combined with swing trailing this is the 🥇 config (+392.9R, §6-B2).

---

## 4. Crazy Filters — one at a time (core: decisive/slSwing/rr3/off/be1, baseline +67.89R)

| Filter | Trades | Win% | TotalR | PF | Verdict |
|--------|--------|------|--------|-----|---------|
| **BASELINE (no filter)** | 557 | 19.8 | +67.89 | 1.26 | — |
| skip_first=False (trade 1st swing) | 560 | 19.9 | +71.89 | 1.28 | ≈neutral, +4R — the 1st swing break is as good as any other |
| leg ≥ 1.0 ATR | 557 | 19.8 | +67.89 | 1.26 | no-op — **every** BTC leg is > 4 ATR |
| leg ≥ 1.5 ATR | 556 | 19.8 | +68.89 | 1.26 | no-op |
| leg ≤ 0.5 ATR (weak fade) | **0** | — | 0 | — | **ZERO trades.** Nifty's "trade weak swings" idea does not exist on BTC 5m |
| EMA20 gate (long>/short<) | 548 | 18.2 | +28.89 | 1.11 | ❌ **HURTS** (−39R) — kills counter-trend reversal entries, which is exactly what swing-break trades ARE |
| EMA50 gate | 560 | 19.5 | +57.89 | 1.22 | ❌ hurts (−10R) |
| **15m bias gate** | 594 | 20.4 | **+102.00** | **1.39** | ✅ **+34R, best single filter.** Higher-TF alignment filters the worst counter-15m breaks |
| **daily streak regime 3-1-1** | 447 | 22.2 | **+105.00** | **1.55** | ✅ **+37R, PF 1.26→1.55.** Regime gating works on BTC daily colors |
| hours 09:15–15:30 IST only | 395 | 21.3 | +75.89 | 1.43 | ✅ mild: fewer trades, better avg (+0.192 vs +0.122) — "NSE hours" are decent BTC hours |
| hours 19:00–01:30 IST (US cash) | 349 | 16.6 | +11.00 | 1.07 | ❌ kills edge (−57R) — US session = chop for this system |
| hours 13:30–01:30 IST (EU+US) | 490 | 15.7 | +6.95 | 1.03 | ❌ kills edge |
| break close ≥ 0.25 ATR past pivot | 556 | 19.6 | +64.89 | 1.25 | ≈neutral — break-bar closes are already decisively past the pivot |
| break close ≥ 0.50 ATR past pivot | 554 | 19.3 | +58.89 | 1.22 | mild ❌ |
| trail r1 (1R trailing distance) | 1137 | 40.7 | +139.07 | 1.38 | ✅ +71R — but 2x the trades, less per trade |
| trail r2 | 493 | 25.6 | +31.22 | 1.13 | ❌ too wide |
| **swing trailing** | 1906 | 13.9 | **+378.32** | **2.05** | ✅✅ **THE edge** (see §2) |

> **Crazy stat:** EMA gates were the best same-day filter on Nifty (+150R, T5) but are WORSE than nothing on BTC. Makes sense: Nifty 1-min trades both with-trend and against; BTC swing-break entries are *reversal* entries by construction — an EMA gate forbids exactly the early-reversal entries that pay 3R+.

---

## 5. Which Break Kind Pays — per-kind stats (decisive core, no filters)

| Entry kind | Trades | Win% | TotalR | Avg R | PF |
|-----------|--------|------|--------|-------|-----|
| B2 | 340 | 18.6 | +21.00 | +0.062 | 1.12 |
| **FLIP** | 217 | 21.7 | **+46.89** | **+0.216** | **1.50** |

> FLIP (the swing that *flipped* the chain direction) is ~3.5x more profitable per trade than B2. FLIP-only entry (`entry_break=flip`) is the quality pick; decisive (B2+FLIP) is the quantity pick. FLIP-only + swing-trail = PF 2.51 (§6-A1).

---

## 6. Combos — winners stacked (from `fix/btc_sweep2.py`)

```
A1 flip + swingTrail be1 (14/7)               Trades 1049  Win% 14.8  TotalR +340.80  Avg +0.325  PF 2.51
A3 decisive + swingTrail be1 (14/7)           Trades 1906  Win% 13.9  TotalR +378.32  Avg +0.198  PF 2.05
B2 minBars20 decisive + swingTrail be1        Trades 1720  Win% 13.4  TotalR +392.94  Avg +0.228  PF 2.24   <- MOST R
B1 minBars20 flip + swingTrail be1            Trades  951  Win% 12.9  TotalR +233.58  Avg +0.246  PF 2.13
C3 minBars20 flip + swingTrail + 15m bias     Trades  498  Win% 12.0  TotalR +140.82  Avg +0.283  PF 2.30
C6 minBars20 decisive + swingTrail + 15m bias Trades 1026  Win% 13.0  TotalR +277.87  Avg +0.271  PF 2.37
D1 flip rr3 off be1 + 15m bias                Trades  467  Win% 21.6  TotalR +108.00  Avg +0.231  PF 1.55
D4 minBars20 flip rr3 off be1 + bias + streak Trades  161  Win% 26.7  TotalR  +77.00  Avg +0.478  PF 2.48   <- BEST PER-TRADE
D5 minBars20 decisive rr3 off be1+bias+streak Trades  287  Win% 25.5  TotalR +108.00  Avg +0.378  PF 1.97
E3 minBars20 flip r1 trail + bias + streak    Trades  178  Win% 46.1  TotalR  +60.59  Avg +0.340  PF 2.22
```

**Combo findings:**
1. **Filters that help fixed-RR configs HURT swing-trail configs.** 15m bias gate: fixed-3R +68→+102R ✅, but swing-trail +378→+118R ❌ (it cuts 3/4 of the trades, and with trailing *every* extra trade compounds R). Streak regime on swing-trail: +341→+55R ❌.
2. Rule of thumb: **swing-trail wants maximum trade count** (let the ratchet compound), **fixed-RR wants maximum selectivity** (only high-quality flips).
3. The two philosophies:
   - **Compounding trailing:** B2 config (+393R over 9 months, 1,720 trades) — needs low fees/permissive sizing.
   - **Sniper fixed-R:** D4 config (+0.478R/trade, PF 2.48, only 161 trades ≈ 18/month) — much easier to execute live.

---

## 7. Next Steps

* [ ] Surface `trailing=swing` as the frontend default on the BTC page (currently `trailing: "off"` — the ship default leaves 5.6x R on the table).
* [x] Make `minBars` a query param on `GET /api/btc/backtest` — **DONE 2026-09-05** (`min_bars` on /backtest + /chart, frontend master presets set it).
* [x] Out-of-sample check: — **DONE 2026-09-05** (Binance 15m Oct-25→Sep-26 downloaded to `data/btc/BTCUSDT_15m_oos.csv`; winners verified with costs — see §8.5).
* [ ] Test the `1m` TF with 15m bias gate (engine is TF-agnostic; 1m CSV already in `data/btc/`).
* [ ] Partial exits: trail half the position, fixed-3R the other half — best of both philosophies.

> **Files:** `fix/btc_sweep.py` (S1–S5 harness), `fix/btc_sweep2.py` (combos), `fix/btc_sweep_out.txt`, `fix/btc_sweep2_out.txt`.

## 8. HOW IT ACTUALLY WORKS — terminology, trailing mechanics, costs, OOS (2026-09-05)

### 8.1 Terminology — "swing = FS" kya hai, B2/FLIP kya hai

* **Swing (kind=FS)** — ek leg: start extreme → end extreme (pivot-to-pivot). BTC pe (24/7 continuous chain) **har swing `kind: FS` hoti hai** — census: 3252/3252 FS, 0 SUS, 0 B1-kind. Reason: `sustainBars` BTC engine pe NO-OP hai, to "sustain-confirmed" swing kabhi banti hi nahi. (Note: Nifty intraday mein "FS" = *First Swing of the day* — naam collision hai, concept alag. BTC pe FS sirf matlab "break-confirmed swing".)
* **B1 / B2 / FLIP = usi FS swing ke BREAK marks** — alag strategy nahi. `entry_break=decisive` = B2+FLIP dono se entry; `flip` = sirf FLIP. Census (5m, 9mo): FLIP 57% / B2 43% / B1 0.
* **Pivot** = swing ka start extreme (local high/low). Trailing isi pivot pe SL ratcheta hai — "naya swing" aur "naya pivot" trailing ke context mein same cheez hain.

### 8.2 Trailing Max R kaise kaam karta hai (pivot ratchet + MFE)

```
1. Swing confirm (minBars) → decisive break close pe ENTRY (up-break=LONG, down-break=SHORT)
2. Initial SL = swing ka START extreme (bahut door — 1R risk = entry↔swing-start)
3. BREAKEVEN (BE1): price +1R jaaye → SL = entry.  (BE0 = off)
4. PIVOT RATCHET: har naye confirmed swing ke start-pivot pe SL shift (ek hi taraf:
   long ka SL sirf UPAR, short ka sirf NEECHE — kabhi loose nahi hota)
   - SHORT: down-swing ka pivot-HIGH SL ko neeche kheenchta hai
5. Exit = SL hit (ya RR target agar trailing off)
```


### 8.3 Three real trade replays (21 Aug 2025, 5m, Trailing Max R)

| Trade | Story |
|---|---|
| #1431 SHORT 00:00 → **-0.37R** | entry 114197.6, initSL 114610 (risk 412pt). 00:05 pivot-high 114350 → SL ratchet (ab max -0.37R). 00:15 low 114011 = MFE +0.45R, par BE1 sirf +1R pe arm hota hai → koi lock nahi. 00:35 bounce → SL hit. **+0.45R MFE ka whipsaw, capped loss.** |
| #1432 SHORT 02:15 → **-0.06R** | entry 114039.6, initSL 114821.8. 02:20 pivot 114086 → SL 94% tight. 03:00 bounce → exit -0.06R. **Yehi "should-be -1R" trade hai — ratchet ne bacha liya.** |
| #1433 SHORT 03:45 → **+0.61R** | entry 114120.3, SL 114431.9. 04:35 MFE +1.01R → BE armed (SL=entry). 06:45/10:20 ratchets 114011/113931. 14:15 retrace → exit +0.61R (MFE +3.75R). **Winner bhi retrace pe trail-exit hota hai.** |

* **MFE** = Maximum Favorable Excursion = trade ke andar price ki max favourable move (R mein). "Trade +0.45R tak gayi thi" = MFE 0.45.
* **Kyun "-0.3R pe marti hai"**: entry swing ke END zone pe hoti hai; turant baad naya same-dir swing confirm hota hai jiska pivot entry se 0.2–0.4R door → SL turant tight → weak trades 5-40 min mein -0.06 se -0.4R pe nikal jaati hain. **Jo +1R tak pahunchi (MFE≥1R) unme se sirf 3/1720 zero-se-niche nikli** — verified; "good trades bhi -0.3R pe mar rahi hain" wali feeling galat thi.
* **Kyun "-1R wali -0.4R pe nikli"**: pivot ratchet ne SL -1R se utha ke -0.37R pe rakh diya — loss 63-94% bacha. Yehi strategy ka feature hai: losses tight, winners ko bhaagne do.
* Win rate 13.4% isliye ki tight stop normal pullbacks me bhi nikal deta hai. Distribution (1720 tr): 781 trail -0.1..-0.5 · 134 trail -0.5..-1 · 287 BE · 99+69+61 trail-positive · sirf 16 full -1R SL.

### 8.4 THE COST REALITY — zero-cost heroes die at taker fees (0.05%/side + 2pt slip)

| Setup (5m full, 272d) | Tr | Win% | Base R | Costs R | **NET R** |
|---|---|---|---|---|---|
| Sniper 3R (flip+bias+streak+mb20) | 161 | 26.7% | +77.0 | -57.8 | **+19.2** |
| Baseline (decisive/fixed3R/mb14) | 556 | 19.8% | +67.9 | -130.3 | **-62.4** |
| FLIP + 15m Bias | 467 | 21.6% | +108.0 | -177.4 | **-69.4** |
| FLIP Quality (trail/BE1/mb14) | 1049 | 14.8% | +340.8 | -414.5 | **-73.7** |
| **Trailing Max R (trail/BE1/mb20)** | 1720 | 13.4% | +392.9 | -537.2 | **-144.3** |
* Per-trade edge ~+0.23R vs per-trade cost ~0.31R → **fees 1.6× the edge**. Breakeven fee for 5m trail: **0.037%/side** (taker ke niche, sirf maker bachaav).
* 15m decisive trail (489 tr): base +126.9 → **NET +44.6** — kam trades = kam fee drag.
* **Top-25 winners = 96.5% of 5m profit** (remove them → rest lose). Tail-lottery profile: params isi 9-month window pe sweep hue the (in-sample).
* **BE + brokerage idea (BE = entry + cost) — TESTED, REJECTED**: 5m trail base +392.9→+305.2 lekin NET -144.3 → **-291.5**; 15m +44.6 → +18.1. BE ko cost tak upar karna bade runners ko jaldi kaat deta hai — net WORSE.

### 8.5 OUT-OF-SAMPLE — Binance 15m Oct-2025 → Sep-2026 (bear: 114k→80k, -30%)

Wahi in-sample logic, **unseen data**, costs included:

| OOS 15m config | Tr | Win% | Base R | **NET R** |
|---|---|---|---|---|
| **flip mb50 swing-trail BE0** | 180 | 22.2% | +170.3 | **+142.3** ✅ |
| decisive mb50 swing-trail BE0 | 272 | 20.6% | +167.5 | **+131.8** ✅ |
| flip mb30 swing-trail BE0 | 292 | 18.5% | +135.0 | **+83.0** ✅ |
| flip mb50 BE0 @ 2× cost (0.1%+5pt) | 180 | — | +170.3 | **+114.0** ✅ |

* flip mb50: maxDD 8.6R, **11/12 months positive**, longs +69R / shorts +101R (dono side).
* Caveats: top-25 = 131% of profit (tail-heavy), single OOS window, Binance spot data.

**Final verdict: BTC ka asli edge = 15m+ TF, swing-trailing, bade legs (mb30-50), BE off.** 5m sweep winners sirf maker/zero-fee pe zinda. Sniper = only positive 5m config at taker fees, lekin thin (+19R).

### 8.6 Master dropdown — ranked BEST to WORST (2026-09-06 final)

* Dropdown ab **rank order me hai (best top pe)**, har label me timeframe — **12 presets**,
  fully synced with `frontend/src/lib/btcMaster.ts` + backend `_MASTER_PRESETS`:
  `#1 Flip Fixed 3R (1h)` → `#2 Decisive Trail 30 (1h)` → `#3 Decisive Trail 50 (15m)`
  → `#4 Sniper 3R (15m)` → `#5 Flip Trail 20 (1h)` → `#6 Flip Trail 50 (15m)`
  → `#7 Flip Trail 30 (1h)` → `#8 Baseline (ship) (15m)` → `#9 FLIP + 15m Bias (15m)`
  → `#10 Flip Trail 30 (15m)` → `#11 FLIP Quality (15m)` → `#12 Trailing Max R (15m)`.
* **Ranking basis (final, live-faithful):** NET R after **stream entries (incl. pre-start
  churn marks)** + **1m-precise fills** + **0.05%/side + 2pt costs**, on each preset's
  OWN reference TF, full Jan-25 → Sep-26 window (bull 2025 + bear 2025-26).
  #11/#12 negative hain — sirf lesson ke liye list me, trade mat karo.
* **Default = `decisive50` (#3)** — the flagship 15m config; #1 (1h fixed-3R) is the
  highest-win-rate + best-net pick on its own TF.
* Pick karte hi: chart preset ke TF pe auto-switch **+ window FULL-ALL set hota hai**
  (taaki chart trade count summary/`ref` numbers se match kare), trades draw,
  neeche stats/table. "How it works" card page ke **sabse niche** hai.
* **Fees % + Slip pts** inputs har backtest pe — stats me **Net R** (base − costs).
* **Strategy Summary card** (trades table ke neeche): `/api/btc/summary` ab har
  preset ko uske **OWN reference TF (bestTf)** pe **FULL data window** pe chalta hai.
  Har row me **TF column** hai, aur **row par click = wahi preset load** (chart uske
  TF/full-window pe jump) — summary me jo Trades/Net R dikhega, wahi chart pe milega.
* Backend labels + frontend dropdown **exact-match** (`(15m)`/`(1h)` style) — ek preset
  ke do alag naam kabhi nahi.
* **"56% win wala kahan gaya?"** — `#1 Flip Fixed 3R (1h)` ab **94 tr / 44.7% win /
  +55.0R NET** (full window, live-faithful). Purana 55.6%/56.2% retrospective-final +
  signal-TF era ka tha. Honest churn-inclusive version me bhi yahi **sabse-high-win +
  sabse-best-net** preset hai.
* **Data range header me dikhta hai**: `Data: 2025-01-01 05:30 → 2026-09-05 23:35 ·`
  176,343 × 5m etc — /api/btc/status se, TF switch karne pe us TF ki coverage.
> Scripts: `backend/debug/_btc_cost_stress.py`, `_btc_cost_sweep.py`, `_btc_fee_breakeven.py`,
> `_btc_fetch_update.py` (data refresh), `_btc_api_smoke2.py` (full API + repro smoke),
> `_btc_htf_sweep.py` (1h/4h grid), `_engine_vs_nifty.py` (engine audit), `_sum1h.py`.

### 8.7 Data — ONE dataset, one CSV per timeframe (2026-09-05)

- Binance OOS candles (5m: 97,848 rows, 15m: 32,615 rows, 1m too) are **appended to the
  main CSVs** (`data/btc/BTCUSDT_{1m,5m,15m}.csv`), so the UI spans Jan-2025 -> Sep-2026
  continuously — trades across BOTH regimes (2025 bull + 2025-26 bear) on one chart,
  seam is bar-perfect (last in-sample bar + 1 tf == first OOS bar).
- **No `_oos.csv` files, no dataset toggle** — that complexity was removed. One dataset,
  simple data. `GET /api/btc/chart|backtest|summary` take no `dataset` param.
- **Pristine in-sample CSVs are backed up** in `data/btc/backup_insample/` — point scripts
  at that folder to reproduce the original 272-day in-sample numbers exactly
  (557/+67.9, 1720/+392.9, 1049/+340.8, 489/+126.9). `_btc_api_smoke2.py` does this
  automatically as its final check.
- Refresh data anytime: `python debug/_btc_fetch_update.py --tf 15m` (or `--tf 5m` / `--tf 1m`)
  — fetches only candles after the CSV's last timestamp and appends (never overwrites history).
- NOTE: a "full window" (All) backtest now covers ~20 months and mixes regimes — the
  in-sample sweep numbers describe the Jan→Oct-2025 window only.

### 8.8 Full-window merged results (15m, Jan-25 → Sep-26, 0.05%+2pt costs)
⚠️ *Audit-step snapshot (1m fills era, pre-churn-fix). The FINAL live-faithful
numbers are §8.12 — this table shows how the window-merge step looked before the
pre-start-churn marks were added.*

| Rank | Preset | Tr | Win% | Base R | NET R |
|---|---|---|---|---|---|
| 1 | Decisive Trail 50 | 544 | 20.2% | +299.9 | **+229.3** |
| 2 | Flip Trail 50 | 368 | 17.9% | +225.5 | **+168.8** |
| 3 | Flip Trail 30 | 519 | 18.3% | +235.1 | **+142.1** |
| 4 | Sniper 3R | 237 | 26.2% | +100.9 | **+54.2** |
| 5 | Baseline | 417 | 21.8% | +100.6 | +48.1 |
| 6 | Trailing Max R (5m-style on 15m) | 1166 | 16.3% | +211.2 | +22.8 |
| 7 | FLIP + 15m Bias | 508 | 20.3% | +103.4 | +7.6 |
| 8 | FLIP Quality | 815 | 13.4% | +104.3 | −81.6 |

Both regimes in one window and still strongly positive after costs — the mb50 trail
configs are the only ones that survive every test thrown at them so far.
⚠️ (This is the pre-churn-fix snapshot; final numbers in §8.12.)

### 8.9 Higher timeframes — 1h / 4h data + sweep (2026-09-06)

* Data: `data/btc/BTCUSDT_1h.csv` (14,715 rows) and `BTCUSDT_4h.csv` (3,678 rows),
  seeded 2025-01-01 -> now from Binance (same IST format, one dataset — no extra toggle).
  The timeframe buttons in the UI now include 1h and 4h. Refresh:
  `python debug/_btc_fetch_update.py --tf 1h --skip-sweep` (or `--tf 4h`).
* Full sweep grid (decisive/flip x minBars x trail off/swing x BE 0/1, net R after
  0.05%/side + 2pt) over the FULL 20-month merged window — bull AND bear:
  ⚠️ *audit-step snapshot (pre-churn-fix, mixed fill-tf). Final live-faithful 1h
  presets are in §8.12.*

| TF | Config | Tr | Win% | Base R | **NET R** |
|---|---|---|---|---|---|
| 1h | flip mb20 fixed-3R BE0 | 72 | **55.6%** | +88.0 | **+82.2** |
| 1h | flip mb30 swing-trail BE0 | 128 | 25.0% | +84.4 | **+74.2** |
| 1h | decisive mb30 swing-trail BE0 | 173 | 24.3% | +91.3 | +80.1 |
| 4h | flip mb30 swing-trail BE0 | 27 | 37.0% | +71.5 | +70.3 |
| 1h | flip mb20 fixed-3R BE1 | 102 | 31.4% | +66.0 | +57.2 |

* 15m + 1h-bias gate (higher-TF bias tested via `bias_timeline`): decisive mb50
  swing BE0 -> 347 tr / +153.2 NET vs **+229.3 NET WITHOUT the bias** on the same
  window. Verdict: the 1h bias gate CUTS profit on the full window (it filters out
  bear-rally shorts) — rejected as default; keep it optional.
* 4h is too slow (27 trades) to trust alone, but its numbers are positive — use it
  only as a regime eyeball, not a strategy TF.
* Takeaways: 1h fixed-3R is the highest win-rate config found so far
  (~5 trades/month — small sample). 1h swing-trail is the low-frequency complement
  to the 15m presets. Both are in the Master dropdown.
* ⚠️ **Final (live-faithful) 1h numbers are in §8.6 / §8.12** — after the pre-start
  churn fix + 1m fills, `#1 Flip Fixed 3R (1h)` = **94 tr / 44.7% win / +55.0R NET**
  and `#2 Decisive Trail 30 (1h)` = **287 tr / 15.3% / +44.5R NET**, on the FULL
  20-month merged window with 0.05%+2pt costs. The older 55.6%/+85.0 numbers below
  were the retrospective-final + signal-fill era.
* RE-VERIFIED (audit step, `_sum1h.py`): flip mb20 fixed-3R -> 73 tr / 56.2% /
  +85.0R NET on signal-fills — this is the PRE-churn-fix snapshot. The current
  live-faithful engine gives 94 tr / 44.7% / +55.0R.
> Script: `backend/debug/_btc_htf_sweep.py` (results in `backend/sweep_htf_*.json`).

### 8.10 1M-PRECISE FILLS — entries/exits resolve on 1-minute candles (2026-09-06)

* Signals (swings/breaks) still form on the chart TF, but **exits (SL / target /
  trail / breakeven) are now checked minute-by-minute** on the 1m CSV — no more
  hidden intrabar stops inside a 15m/1h bar. Entries were already precise
  (fill = signal bar close = the exact 1m price of that minute).
* Engine: `simulate_btc_trades(..., fine=1m_candles)` (`_exit_on_fine` helper).
  Conservative rules unchanged: exit checks use the SL as of the previous bar,
  SL checked before target inside a bar, gap fills at the bar open.
* API: `GET /api/btc/backtest` and `/summary` default to `fill_tf=1m`
  (pass `fill_tf=signal` for the old signal-TF fills). The UI shows
  "1m-precise fills" in the filters line. Scripts without `fine=` are unchanged.
* Honest numbers (15m full merged window, 0.05%+2pt costs) — signal-fills vs 1m:
  ⚠️ *pre-churn-fix snapshot — final live-faithful numbers are the §8.12 table.*

| Preset | signal-fills NET | **1m-precise NET** | trades |
|---|---|---|---|
| Decisive Trail 50 | +229.3 | **+195.7** | 614 |
| Flip Trail 50 | +168.8 | **+97.5** | 397 |
| Flip Trail 30 | +142.1 | **+71.1** | 583 |
| Sniper 3R | +54.2 | **+51.3** | 237 |
| Flip Fixed 3R (1h cfg) | +82.2* | **+50.7** | 295 |
| Trailing Max R | +22.8 | **-93.0** | 1427 |
| FLIP Quality | -81.6 | **-132.0** | 903 |

  (*1h cfg numbers measured on the 1h window; the row here is the same config
  on 15m candles.) The pattern is consistent: **1m fills shave the fantasy
  edge** — stops that a 15m bar hid now trigger. Trailing Max R flips negative;
  the mb50 trail presets and Sniper stay solidly positive. These 1m numbers are
  the ones to trust for live expectations.
* Regression guard: the in-sample headline repro (1720 / +392.95) still passes
  because scripts that omit `fine=` keep the original signal-TF behaviour.
* UI boxes now draw entry -> ACTUAL exit price (green win / red loss), not the
  static 3R target — trail exits like trade #1 (+6.62R @ 97,514) show their real
  height. Trade table me exact 1m exit time, chart box pe snapped candle.
* LIVE-TRADEABILITY (code-verified): B1/B2/FLIP marks are real-time events —
  `_establish_direction` / `_confirm_direction` / `_flip_direction` all fire at the
  CURRENT bar (`g_idx`). The minBars gate applies to the swing's DECLARATION
  (finalizing its end extreme), NOT to entries — B2 at 17:00 fired when the swing
  was only 8 bars old. Honest caveat: the B2 mark's idx uses the sealed pivot
  (up to 2 bars back, `b2_gap_bars` rule), so live entry lands on the confirmation
  bar's close (~30 min later on 15m) — slightly worse fills than the backtest's
  marked-bar close, but the signal itself is knowable in real time.

### 8.11 LIVE-FAITHFUL SL FIX — opposite-direction breaks got the RIGHT stop (2026-09-06)

* **Bug:** the stream-entry path assigned the WRONG SL to opposite-direction B2/FLIP
  marks. For a SHORT B2 that broke the previous UP-swing, the stop was set to that
  up-swing's **START** pivot — the LOW — which sits BELOW the entry. That is a
  degenerate risk (SL on the wrong side), so the signal was silently SKIPPED.
* **Example (Decisive Trail 50, 15m):** 10-Jan-2025 swing #21 is an UP-FS with churn:
  `15:45 B1 down → 16:00 FLIP up → 17:00 B2 down → 23:15 FLIP up`. A live trader
  sees the **B2 DOWN at 17:00** and shorts (that is the knowable signal at that
  bar) — but the old code used the up-swing START (92,206) as the SL for the SHORT,
  risk went negative, and the trade vanished. Exactly the "live vs backtest" gap
  the user caught.
* **Fix (`_collect_signals`):** opposite-dir marks now get the **PREVIOUS leg's END
  extreme** as their stop (the high of the up leg for a SHORT / the low of the down
  leg for a LONG) — i.e. the pivot the mark actually BROKE. Guards: mark must occur
  at/after that end index; otherwise it is pre-churn and skipped.
* **Also added a degenerate-risk floor:** CSVs round to 2dp, so a swing start_px
  and an entry close can collide to a 0.0x-point "stop" (e.g. risk 0.03 pts →
  $3,250R cost_r artifact). Trades with risk < 0.05% of price are skipped as
  data-rounding ghosts.
* **Verified:** 10-Jan 17:00 now produces a real trade:
  `#4 SHORT 17:00 px=94,911.79 sl=95,000.55 (prev up-swing END) exit=SL -1.0R`.
  Live-faithful. The subsequent 23:15 FLIP-up LONG still trades too.
* **New honest 12-preset ranking (stream + 1m fills + 0.05%/side + 2pt, full Jan-25→Sep-26):**
  ⚠️ *pre-churn-fix snapshot — FINAL numbers (pre-start churn marks included) are the
  §8.12 table below; this one is kept only as the audit step.*

| # | Preset | TF | trades | win% | base R | NET R |
|---|---|---|---|---|---|---|
| 1 | Decisive Trail 50 | 15m | 769 | 12.4 | +198.2 | **+80.0** |
| 2 | Flip Trail 50 | 15m | 525 | 12.8 | +159.3 | +67.8 |
| 3 | Flip Fixed 3R | 1h | 92 | 45.7 | +68.5 | +59.3 |
| 4 | Decisive Trail 30 | 1h | 268 | 16.4 | +79.2 | +57.2 |
| 5 | Sniper 3R | 15m | 303 | 24.8 | +100.0 | +39.9 |
| 6 | Flip Trail 20 | 1h | 227 | 15.9 | +32.4 | +9.1 |
| 7 | Flip Trail 30 | 1h | 203 | 13.8 | +18.2 | -3.5 |
| 8 | Flip Trail 30 | 15m | 736 | 11.5 | +140.9 | -4.2 |
| 9 | Baseline (ship) | 15m | 448 | 18.8 | +42.9 | -17.9 |
| 10 | FLIP + 15m Bias | 15m | 559 | 19.5 | +89.9 | -25.5 |
| 11 | FLIP Quality | 15m | 1085 | 8.2 | +42.9 | -220.4 |
| 12 | Trailing Max R | 15m | 1650 | 8.4 | +60.8 | -250.8 |

* Frontend `btcMaster.ts` + backend `_MASTER_PRESETS` are **exact-match synced**
  (same labels, same rank order, same ref numbers). In-sample 5m stream repro now
  guards at **2034 tr / +82.24R** (the old +392.95 / +128.4 / +80.0 numbers were
  pre-churn-fix; see §8.12 for the final live-faithful stats).

### 8.12 PRE-START CHURN MARKS — same-dir flips before the swing's declared start (2026-09-06)

* The 10-Jan deep audit (debug/_engine_vs_nifty.py) replayed swing #21
  bar-by-bar with the EXACT engine instance the chain used (stitch = prev
  end + 1 = bar 904, 15:30). Replay marks == chain marks byte-for-byte:
  `15:45 B1 down -> 16:00 FLIP up -> 17:00 B2 down -> 23:15 FLIP up`.
  The SwingEngine core is faithful — same code Nifty runs.
* **But the 16:00 FLIP-up fired BEFORE swing #21's declared start (20:30)** —
  it's a pre-start churn mark in the final chain. Live, a trader at 16:00 sees
  that up-break as a real signal. The old `_collect_signals` skipped all
  pre-start same-dir marks ("ambiguous origin") -> the 16:00 LONG never traded.
* **Fix:** when `candles` is supplied (stream mode), pre-start same-dir
  B2/FLIP marks now emit with a LIVE-RECONSTRUCTABLE stop: for a LONG the
  lowest low since the prev swing's end; for a SHORT the highest high. This
  mirrors what a live engine at that bar could actually observe.
* **Verified:** the 10-Jan sequence now yields BOTH live signals —
  `16:00 FLIP-up LONG sl=94,757.57 (-1.0R SL)` AND `17:00 B2-down SHORT
  sl=95,000.55 (busy_until blocks it after the 16:00 exit)` AND `23:15
  FLIP-up LONG (-0.39R)`.
* **Deep engine-vs-nifty finding:** `compute_swing_results` (per-day reseed)
  vs `compute_btc_swings` (continuous chain) cut DIFFERENT segments on 30/30
  days — but that is the WRAPPER (midnight reseed), not the engine. On
  10-Jan, Nifty's per-day chain never declares swing #21 at all (minBars 50
  vs remaining day bars) -> it has zero trades in the whole churn window.
  Continuous 24/7 chaining is the right model for BTC.
* **Honest consequence:** including pre-start churn marks changes the
  economics — 15m trail presets now bleed on fakeout flips, so the ranking
  flips: **#1 Flip Fixed 3R (1h) +55.0R NET** (94 tr, 44.7% win) is now the
  best config. The 1h low-frequency design absorbs churn cost far better.
* **Final 12-preset ranking (stream incl. pre-start churn + 1m fills + 0.05%+2pt):**

| # | Preset | TF | trades | win% | base R | NET R |
|---|---|---|---|---|---|---|
| 1 | Flip Fixed 3R | 1h | 94 | 44.7 | +64.8 | **+55.0** |
| 2 | Decisive Trail 30 | 1h | 287 | 15.3 | +69.7 | +44.5 |
| 3 | Decisive Trail 50 | 15m | 847 | 11.2 | +157.4 | +19.0 |
| 4 | Sniper 3R | 15m | 330 | 22.7 | +75.0 | +7.0 |
| 5 | Flip Trail 20 | 1h | 240 | 15.0 | +22.5 | -3.5 |
| 6 | Flip Trail 50 | 15m | 599 | 11.2 | +114.7 | -5.6 |
| 7 | Flip Trail 30 | 1h | 219 | 12.8 | +7.2 | -18.9 |
| 8 | Baseline (ship) | 15m | 457 | 19.0 | +43.9 | -19.3 |
| 9 | FLIP + 15m Bias | 15m | 592 | 18.4 | +60.9 | -65.7 |
| 10 | Flip Trail 30 | 15m | 817 | 10.4 | +101.8 | -74.8 |
| 11 | FLIP Quality | 15m | 1154 | 7.7 | +9.1 | -283.2 |
| 12 | Trailing Max R | 15m | 1735 | 8.0 | +23.8 | -321.9 |

* Frontend `btcMaster.ts` + backend `_MASTER_PRESETS` re-synced (same labels,
  same rank, same ref #). In-sample 5m stream repro guards at
  **2034 tr / +82.24R**. The engine is now fully live-faithful for entries:
  every B2/FLIP the live engine would have fired is a trade.

