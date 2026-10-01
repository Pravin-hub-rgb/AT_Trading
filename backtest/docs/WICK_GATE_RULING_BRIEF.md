# WICK-GATE RULING BRIEF - padho, phir ruling do

**Date:** 2026-09-27 | **Status:** kuch bhi ADOPT nahi hua - tumhara ruling pending hai
**Full technical record:** CHECKLIST 24.96, EXPERIMENT_LOG row 101, harness
`backtest/tests/exp_gray_wick1h.py`, results `_gray_wick1h.json`
**OUTCOME (2026-09-27): HOLD - sole blocker forward gate 5/50 (supersedes "ruling pending" above).**
**Corrected in c18ffbb/eb12934: window 5.0-5.4 | 5.6-6.4 (hole 5.5), age10 = insufficient data, all-6 = 6.1 post-hoc; record extended: CHECKLIST 24.97, LOG row 102.**

---

## TL;DR (Hinglish)

1. **Purana "wick gate dead" verdict galat gate par tha.** Stage B ne jo gate
   dhundha tha (1-hour wick), uske baad ke saare harness 15-minute wick nape -
   naam same, formula alag, trades alag (74 vs 112), cohort ka sign ulta.
2. **Asli gate (1h wala) gray mode me 4/4 PASS:** +28.1 / +25.7 / +19.8 / +23.8R
   (IS/OOS x champion/utcsat), bilkul wahi number jo Stage B ka post-process tha -
   iska matlab gray mode exactly sahi kaam karta hai (proof: seq-identical 6/6,
   cascade 0.00).
3. **Age10 lane ek chhota miss hai** (-2.0R, sirf is/age10) - par age10 kabhi
   Stage B ke rule me tha hi nahi.
4. **Abhi kuch ship nahi hua.** Neeche 4 options hain - Adopt / Adopt-all /
   Hold / Reject. Jo bolo, wahi aage badhega (engine change sirf dusra agent
   karega, mere haath me nahi).

---

## 1. Kya gadbad thi (simple me)

**Stage B (24.90) ne yeh gate dhundha tha:**

> "SHORT trades jahan pichhle 12 GHANTE (12 x 1h bars) ki total wick
> ATR se kam hai (< 6.026)" - yeh trades net LOSERS the. Unhe ledger se
> hatane par +28.1 / +25.7 / +19.8 / +23.8R milte the (4/4 PASS).

**Problem:** agle sab harness (`exp_wick_short_pathtrue`,
`exp_cascade_tax_test`, aur unke gray children `exp_sl_fine_cascade` /
`exp_sl_width_gate`) ne wick **15-minute bars** par napi - 12 x 15m bars
(entry bar included), ATR15, raw threshold 6.03. Yeh **alag formula hai**:

| | Stage B (asli) | Follow-ups (jo sabne test kiya) |
|---|---|---|
| Timeframe | 1h bars | 15m bars |
| Window | 12 closed 1h = 12 ghante | 12 x 15m = 3 ghante (entry bar included) |
| ATR | ATR14 of 1h | ATR of 15m |
| Threshold | raw < 6.026 (rounded value) | raw <= 6.03 |
| Flagged (is/champion) | **74 trades** | **112 trades** |
| Cohort sign | **-28.1R (losers)** | **+6.7R gross (winners!)** |

**Result:** jo "-78.6R cascade tax" mila aur "gray wick ko rescue NAHI karta"
verdict aaya - wo dono galat cohort par the. Jaise do alag instruments se
humidity napi aur ek dusre se compare kar diya.

## 2. Is run me kya proof hua (sab pre-registered, controls green)

**Controls (sab pass, tabhi verdicts dikhe):**
- 6 ref ledgers exact (500/+325.8, 454/+359.0, 130/+435.7 IS; 279/+70.1,
  253/+60.2, 76/+43.2 OOS)
- Stage B parity EXACT: offline flags = Stage B ke bilkul (74/62/35/36 counts
  AND sumNet -28.0569/-25.6736/-19.7805/-23.7746 tak 1e-3 me)
- In-engine gray flags = offline flags, 6/6 cells
- Purane 15m cohort ka offline replication = purane artifact ke n_gray
  (112/100/30/64/61/18) exact 6/6

**Numbers (gray = signal aaye, order mat lagao, par engine ka state jaise chalna
chahiye waise chalta rahe):**

| Cell | Gray trades | Harness dNet | **LIVE dNet** (asli paise) | Path-true skip | Kept% |
|---|---|---|---|---|---|
| IS champion | 74 | +10.5 | **+28.1** (= Stage B) | -39.0 | 85.2 |
| IS utcsat | 62 | +13.1 | **+25.7** (= Stage B) | -12.6 | 86.3 |
| OOS champion | 35 | +15.5 | **+19.8** (= Stage B) | +7.5 | 87.5 |
| OOS utcsat | 36 | +19.3 | **+23.8** (= Stage B) | +24.0 | 85.8 |
| IS age10 | 20 | -6.7 | **-2.0** | -9.1 | 84.6 |
| OOS age10 | 7 | +4.3 | **+5.2** | +4.1 | 90.8 |

Notes:
- **Harness vs LIVE ka farq = cost relief:** harness me gray trade ki fees/
  funding book me phir bhi kat-ti hai; asli me order hi nahi laga toh cost hi
  nahi (17.6/12.6/4.3/4.5R bachte hain 4 cells me). Yehi farq 15m verdict ko
  bhi badalta nahi (neeche para 4).
- **seq-identical 6/6 + cascade 0.00:** gray ke baad bhi wahi agle trades aaye
  jo aane chahiye the - slot/cooldown/streak sab preserve. Isi liye live dNet
  == post-process EXACTLY barabar nikla (P2 prediction, 4/4 match).
- **Path-true skip alag hai** (state preserve NAHI): IS me -39.0/-12.6, OOS me
  +7.5/+24.0. Matlab: cascade tax (skip karne ki keemat) IS me bhaari, OOS me
  lagar-sab. **Gray yeh keemat NAHI deta** - yahi gray ka poora point hai.

## 3. Rules ka status

- **G-RULE (kept >=55% AND live dNet>0 AND avg not worse AND DD not worse,
  sab cells):** **4/4 PASS** Stage B ke apne 4 cells (champion/utcsat x IS/OOS)
  par. **All-6 FAIL** - sirf is/age10 (-2.0R) ki wajah se.
- Age10: Stage B ka find/removal rule kabhi 4 cells (champion/utcsat) par
  pre-registered tha - age10 usmein tha hi nahi. Sirf 20 trades flag hui,
  cohort khud +2.0R profit ka tha (isliye skip karne par 2R ka nuksan).
- **RESEARCH_POLICY:** kuch bhi adopt nahi - sirf tumhara ruling.

## 4. Purana "15m wick dead" verdict - kya woh galat tha?

**Us cohort ke liye verdict SAHI hai (dead), par wo cohort hi galat tha.**
Cost relief jod kar bhi (exact, parity-proven):

| 15m cohort | Harness | + Cost relief | **LIVE** |
|---|---|---|---|
| IS champion | -6.7 | +26.1 | **+19.4** |
| IS utcsat | -7.0 | +21.4 | **+14.3** |
| OOS champion | -78.0 | +7.9 | **-70.1** |
| OOS utcsat | -78.1 | +7.9 | **-70.2** |

OOS -70/-70 - kisi bhi hisaab se negative. Toh "15m wala gate dead" aaj bhi
dead hai; bas woh gate Stage B ne kabhi find kiya hi nahi tha.

## 5. Tumhara ruling - 4 options

**A. ADOPT (Stage B lanes: champion/utcsat) - recommended**
   - Gate ON: short signal + 1h wick/ATR14 < 6.026 -> gray (no fill, state
     preserved). Age10 par lagu nahi.
   - Aage kya hoga: main AGENT_COORDINATION me ruling note karta hoon, phir
     **dusra agent (engine owner)** `v18_streak_halt.py` me gray implementation
     lagayega; mera kaam research + docs tak.
   - Risk: short entries ka ~13-15% skip hoga; agar market structure badle toh
     gate winners bhi chhod sakta hai (gate sasta hai - ek flag se OFF bhi ho
     sakta hai; cascade-free by design).

**B. ADOPT EVERYWHERE**
   - Upar sab + age10 bhi - yaani is/age10 ka -2.0R accept karna.

**C. HOLD (validation-first)**
   - Abhi kuch mat karo; pehle replay/forward validation chahiye (live-
     equivalent data par gate chalakar n>=50 trades ka sample). CANDIDATE
     rehta hai.

**D. REJECT**
   - Sirf document rehta hai, engine me kuch nahi jaata.

## 6. Files

- Harness: `backtest/tests/exp_gray_wick1h.py` (pre-registered P1-P4)
- Results: `backtest/tests/_gray_wick1h.json`
- Records: CHECKLIST **24.96**, EXPERIMENT_LOG **row 101**, SUMMARY bullet
- Commit: `4f97f90` (live-engine bhi ff hokar isi par hai)
- Purane galat-gate ke harness (evidence): `exp_wick_short_pathtrue.py`
  (docstring ka "identical to Stage B" claim false hai - usi me likha tha),
  `exp_cascade_tax_test.py`, `exp_sl_fine_cascade.py`
