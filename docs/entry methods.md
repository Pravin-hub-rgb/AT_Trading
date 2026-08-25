# ENTRY METHODS — Fixed Set (Cases Inko Reuse Karte Hain)

> RULE: Methods KABHI nahi badhenge yahan se (naya idea aaya toh discussion,
> prove hone pe hi add). Cases badhte rahenge — har case ki last line bas
> yahi bolegi: "Entry Method #X".

Naming note: engine internals abhi `direct`/`retro` bolte hain — rename to
`break-family` / `level-family` planned. Yahan final names use ho rahe hain.

---

## M1 — AGGRESSIVE BREAK ⚡⚡

| | |
|---|---|
| **Kab** | Retrace ALREADY-DONE contexts (e.g. ▲+gap-down+selling-first) — arm AT OPEN |
| **Trigger** | Counter-swing ka bias-direction break (domination/candle-size, close-q ≥50%) |
| **Test-zone** | Opening/gap-low region (deep leg-low ka intezar NAHI) |
| **Leg-wait** | ZERO bars |
| **SL** | Ref extreme − mult × 10-day avg |
| **Fail-safe** | 2-bar ft_fail admission |
| **Gate** | prev-close READ = STRONG (weak pe downgrade → M3) |
| **Engine** | ⚠️ PARTIAL — fast-arm pending |

## M2 — PATTERN BREAK ⚡

| | |
|---|---|
| **Kab** | Normal aligned break (counter-swing exist karti hai, standard) |
| **Trigger** | Aligned pace-break candle close (aggressive types) ya structure-break confirm |
| **SL** | Standard |
| **Fail-safe** | 2-bar ft_fail admission |
| **Gate** | Default aligned contexts |
| **Engine** | ✅ LIVE (`direct` path) |

## M3 — LEVEL TEST 🐢

| | |
|---|---|
| **Kab** | Patient contexts — counter-move ka EXTREME test hua |
| **Trigger** | Level ± tol pe test → domination (consume ≥60% ya big ≥1.5×avg, close-q ≥50%) → follow-through ≤2 bars |
| **Leg-min** | ≥3 bars counter-leg pehle chale |
| **SL** | Leg extreme − avg×mult |
| **Engine** | ✅ LIVE (`level` path) |

## M4 — SWING-SUPPORT PER-FLOW ⚡⚡

| | |
|---|---|
| **Kab** | GAP-DOWN + first-swing BUYING (S6:105 "still bought per flow") |
| **Arm** | Classification ke TURANT baad — first swing ka apna low-region = zone |
| **Trigger** | Wahan support-hold/domination (support → pattern break → buy) |
| **Gate** | Container-specific |
| **Engine** | ❌ BACKLOG |

## M5 — ONE-CANDLE ENTRY

| | |
|---|---|
| **Kab** | Strong-flow / exhaustion-complete post-support ("single-candle entry legitimate", S6:118) |
| **Confirmation** | MINIMAL — ek candle hi kaafi |
| **Gate** | Sirf strong-contexts (prev-STRONG + flow support) |
| **Engine** | ❌ BACKLOG |

## M6 — COUNTDOWN LEVEL ⏱️

| | |
|---|---|
| **Kab** | GAP-UP containers — counter-candles COUNT (pehli opposite candle se) |
| **Unlock** | Count ≥ EXHAUSTION_N (~8, configurable) → level-entry early allow, FT-light |
| **Base** | M3 jaisa trigger, relaxed gates count-pure hone par |
| **Engine** | ❌ BACKLOG |

## M7 — SECOND-DOMINATION 🔁

| | |
|---|---|
| **Sequence** | Buyer-dom → seller-dom → buyer-dom → **seller-dom #2 = ENTRY** |
| **Source** | S6:105 against-flow menu ("execute ON THE SECOND SELLER DOMINATION") |
| **Engine** | ❌ BACKLOG |

## M8 — LOWER-HIGH EXECUTE 📉

| | |
|---|---|
| **Kab** | Lower high form ho jaaye (against-flow option) |
| **Trigger** | LH + uska break |
| **Source** | S6:105 |
| **Engine** | ❌ BACKLOG |

---

## STATUS SUMMARY

| Method | Engine | Notes |
|---|---|---|
| M1 Aggressive Break | ⚠️ partial | fast-arm + prev-read gate pending |
| M2 Pattern Break | ✅ live | |
| M3 Level Test | ✅ live | |
| M4 Swing-Support | ❌ backlog | E4 row |
| M5 One-Candle | ❌ backlog | strong-flow tier |
| M6 Countdown Level | ❌ backlog | E3/E6 rows |
| M7 Second-Dom | ❌ backlog | course-menu |
| M8 Lower-High | ❌ backlog | course-menu |
