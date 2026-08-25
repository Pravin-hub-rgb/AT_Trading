# Intraday Trading Explained — Story Se Seekho

> Ye doc tumhe **step-by-step** batata hai ki har bias + market condition mein **exactly kya karna hai**.
> Story jaise socho — "agar A hua, toh B karo; agar C hua, toh D karo."
> Reference: `intraday-trading-system.md` for rules, `bias-engine-explained.md` for initial bias.

---

## Pehle Samjho: Din Ka Timeline

```
9:15  ─── Market khula
       │   Opening candles bante hain (2-4 green ya 2-4 red)
       │   Ye FIRST SWING ban raha hai — par ABHI COMPLETE nahi hua
       │   Market UNSETTLED hai, direction nahi mili
       │   ❌ KUCH MAT KARO — trade mat lo
       │
9:45  ─── Market settle hota hai
       │   First swing almost complete
       │   Ab direction dikh rahi hai
       │   ✅ Ab dekhna shuru karo
       │
~10:00 ─── First swing COMPLETE + S/R formed
       │   Pace break identify karo
       │   Retracement ka wait karo
       │   ✅ AB trade kar sakte ho
       │
10:00-11:12 ─── BEST EXECUTION WINDOW
~11:12 ─── CUTOFF (morning trades ke liye)
12:00 ─── ABSOLUTE BOUNDARY
1-2 PM ─── SECOND SESSION (needs volume)
```

**Key insight:** 9:15-9:45 = first swing BAN RAHA HAI (forming). Ye swing hai, par trade mat karo — market unsettled hai. Trade tab shuru hota hai jab swing complete ho aur S/R ban jaaye (~10 AM).

**Definition (important):** FIRST SWING = **9:15 → 9:45 ka initial move KHUD hai** — open hote hi market jo kiya, wahi swing hai. Ye "9:45 ke baad shuru" nahi hota; 9:45 tak wo COMPLETE ho jaata hai aur uske baad entries ka game shuru hota hai (retracement ya breakout).

---

## Kaise Padho Is Doc Ko

```
Step 1: Tumhara INITIAL BIAS kya hai? (Bullish / Bearish / Unbiased)
            ↓
Step 2: Market khula — 9:15-9:45 mein kya hua? (gap up/down/flat)
            ↓
Step 3: 9:45 ke baad FIRST SWING kis direction mein bana?
            ↓
Step 4: First swing overview ke saath hai ya against? (WITH = same direction, RETRACEMENT = opposite = support/resistance pe trade)
            ↓
Step 5: Swing HEALTHY hai ya WEAK? (niche dekho)
            ↓
Step 6: Us case ke rules follow karo
```

---

## HEALTHY SWING vs WEAK SWING — Pehle Ye Samjho

> "Two things observed in any swing: its **size** and how deep the **retracement** against it runs. **Retracement always carries the higher weightage**: deeper retrace = weak swing = reversal generally expected." (S4)

### Healthy (Strong) Swing kya hota hai:

```
Candles:    Green → Green → Green (koi red consume nahi kar raha)
Retrace:    Shallow (<30% of swing)
Size:       Bada (5+ candles, extended)
Pattern:    Continuous momentum, no interruption
Type:       Type A — ONE resistance banata hai aur SUSTAIN karta hai
```

**Example:** 9:45 ke baad 5 consecutive green candles, koi bhi red ne previous green ko consume nahi kiya = HEALTHY buying swing.

### Weak Swing kya hota hai:

```
Candles:    Green → Red (consuming) → Green → Red (consuming)
Retrace:    Deep (>50% of swing)
Size:       Chhota (2-3 candles, didn't extend)
Pattern:    Candles ek dusre ko reverse kar rahe hain
Type:       Type B — Highs break karta hai ek ek candle se, phir reverse hota hai
```

**Example:** 9:45 ke baad green aaya, phir red ne usse consume kiya, phir green aaya, phir red — ye WEAK swing hai.

### Swing Quality Check:

| Signal | Healthy ✅ | Weak ❌ |
|---|---|---|
| **Candle pattern** | Same direction candles | Alternating consuming candles |
| **Retracement depth** | Shallow (<30%) | Deep (>50%) |
| **Swing size** | Big (5+ candles) | Small (2-3 candles) |
| **Momentum** | Continuous | Interrupted |
| **Type** | Type A (sustains) | Type B (reverses) |

### Weak Swing ki Minimum Expectation:

> "Weak selling swing → small support → general expectation: intraday high breakout (recovery)." (S3)
> "Weak buying swing → reversal toward the intraday low." (S3)

**Matlab:** Agar buying swing WEAK hai → expectation hai ki low tak jaayega. Agar selling swing WEAK hai → expectation hai ki high tak jaayega.

### Swing Kab VOIDED Hota Hai:

> "Buying swing VOIDED once lows break **3-4 consecutive candles** — whole leg reclassified selling." (S6)

**Matlab:** Agar buying swing ke baad 3-4 consecutive red candles lows tod dein = swing khatam, ab selling leg hai.

### Confirmation Needs Follow-Through:

> "One big candle alone isn't confirmed: big size at crucial timing but consumed nothing, no next-candle continuation → wait more. Confirmed when: big selling reversing off support + domination candle CLOSES + first-time upward continuation follows." (S5)

**Matlab:** Ek bada candle kaafi nahi — next candle bhi same direction mein honi chahiye (follow-through).

---

# PART 1: BULLISH BIAS (▲)

> Tumne raat ko initial bias nikala: **▲ BULLISH**.
> Market khula. Ab kya?

---

## Case B1: Gap-Up + First Swing Bullish = EASIEST TRADE

### Situation:

```
Pre-open: ▲ BULLISH
Market: Gap up khula
9:15-9:45: Opening candles aaye (2-4 red ya green — first swing forming)
9:45: Market settle hua
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Gap-up matlab buyers already strong hain. 9:15-9:45 mein jo bhi candles aaye — wo first swing ban rahe hain. 9:45 ke baad buying swing bana = direction clear hai.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo (trade mat karo)
2. 9:45 ke baad: Buying swing identify karo
3. Swing HEALTHY hai? (green candles, shallow retrace, big size)
   → YES: WITH FLOW trade — direct entry milegi
   → NO (weak swing): Extra caution, better confirmation chahiye
4. Pace break identify karo (rhythm toota)
5. S/R level mark karo (support)
6. Retracement ka wait karo support tak
7. Domination candle ka wait karo (green consuming red + close + follow-through)
8. ✅ BUY karo
```

### Entry:

```
Entry: Support pe, domination candle ke baad (candle CLOSE ke time pe)
SL: Support ke thoda neeche (average candle size, never at extreme)
Target: 1:3
```

### Why this works:

> "Gap-up in buying flow: gap IS the continuation. Morning retrace expected. Support at 9:45-10 pe buy." (S1)

**Ye WITH FLOW trade hai.** Direction tumhare favor mein hai. Direct entry milegi.

---

## Case B2: Gap-Up + First Swing Bearish = RETRACEMENT (BUY at Support!)

### Situation:

```
Pre-open: ▲ BULLISH
Market: Gap up khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Gap-up tha par selling aa gayi. **Par tumhara bias BULLISH hai.** Selling = RETRACEMENT hai, weakness nahi. Overview protects you.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Selling swing bana
3. Selling IGNORE karo — overview bullish hai
4. Pace break identify karo (selling ka rhythm toota)
5. Support level mark karo
6. Domination candle ka wait karo (green consuming red + close + follow-through)
7. ✅ SUPPORT PE BUY karo
```

### Entry:

```
Entry: Support pe, domination candle ke baad (candle CLOSE ke time pe)
SL: Support ke thoda neeche (average candle size)
Target: 1:3
```

### Why this works:

> "Bias overrides pattern." (S6, Line 97)
> "Gap-up in buying flow: gap IS the continuation. Morning retrace expected. Support at 9:45-10 pe buy." (S1)

**Gap-up = buyers strong.** Selling sirf retracement hai. Support pe buy karo. **SHORT MAT KARO.**

---

## Case B3: Gap-Down + First Swing Bullish = GAP IS RETRACEMENT (BEST OPPORTUNITY!)

### Situation:

```
Pre-open: ▲ BULLISH
Market: Gap down khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

**Ye BEST case hai!** Buying bias hai + prev day selling retracement thi + gap down = aur zyada discount mil raha hai. Gap DOWN hi retracement hai — market ne already neeche ja ke support test kar liya.

### Kya karna hai:

```
1. Gap-down ko SHORT MAT KARO — flow buying hai
2. "Gap-down ALREADY counts as the retracement" (S6)
3. 9:45 ke baad buying swing bana
4. Pace break identify karo
5. Support level mark karo
6. Domination candle ka wait karo
7. ✅ BUY karo — better price mil raha hai!
```

### Entry:

```
Entry: Support pe, domination candle ke baad
SL: Support ke neeche
Target: 1:3
```

### Why this works:

> "Gap-down in buying flow: gap IS the retracement. Won't keep falling." (S5)
> "Gap-down ALREADY counts as the retracement." (S6)
> "Gap-down handling: buying swing created after gap-down still bought per flow (support → pattern break → buy)." (S6)

**Gap-down = free retracement = better entry price!** Tumhe alag se retrace ka wait nahi karna.

---

## Case B4: Gap-Down + First Swing Bearish = RETRACEMENT (BUY at Support!)

### Situation:

```
Pre-open: ▲ BULLISH
Market: Gap down khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Gap-down + selling = bearish signal dikh raha hai. **Par tumhara bias BULLISH hai.** Gap-down = FREE RETRACEMENT. Selling = retracement. Overview protects you.

### Kya karna hai:

```
1. Gap-down ko SHORT MAT KARO — flow buying hai
2. "Gap-down ALREADY counts as the retracement" (S6)
3. 9:45 ke baad selling swing bana
4. Selling IGNORE karo — overview bullish hai
5. Pace break identify karo
6. Support level mark karo
7. Domination candle ka wait karo
8. ✅ SUPPORT PE BUY karo — better price mil raha hai!
```

### Entry:

```
Entry: Support pe, domination candle ke baad
SL: Support ke neeche
Target: 1:3
```

### Why this works:

> "Gap-down in buying flow: gap IS the retracement. Won't keep falling." (S5)
> "Gap-down ALREADY counts as the retracement." (S6)
> "Gap-down handling: buying swing created after gap-down still bought per flow (support → pattern break → buy)." (S6)
> "Bias overrides pattern." (S6)

**Gap-down = free retracement = better entry price!** Selling IGNORE karo, support pe buy karo. **SHORT MAT KARO.**

---

## Case B5: Flat Open + First Swing Bullish = DIRECT WITH FLOW

### Situation:

```
Pre-open: ▲ BULLISH
Market: Flat open (no gap)
9:15-9:45: Opening candles (mixed)
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Flat open + buying swing = WITH FLOW. Sab simple hai.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Buying swing bana
3. Swing HEALTHY hai? → WITH FLOW direct entry
4. Pace break identify karo
5. S/R level mark karo
6. Retracement ka wait karo
7. Domination candle ka wait karo
8. ✅ BUY karo
```

### Entry:

```
Entry: Support pe (pace break level)
SL: Below the low (average candle size)
Target: 1:3
```

### Simplest trade:

> "Buying trend, market retraces: no N/M check needed. Support identifies via pace-of-momentum break → execute directly." (S5)

---

## Case B6: Flat Open + First Swing Bearish = RETRACEMENT (BUY at Support!)

### Situation:

```
Pre-open: ▲ BULLISH
Market: Flat open
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Flat open + selling = bearish dikh raha hai. **Par tumhara bias BULLISH hai.** Selling = RETRACEMENT hai. Overview protects you.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Selling swing bana
3. Selling IGNORE karo — overview bullish hai
4. Pace break identify karo (selling ka rhythm toota)
5. Support level mark karo
6. Domination candle ka wait karo (green consuming red + close + follow-through)
7. ✅ SUPPORT PE BUY karo
```

### Entry:

```
Entry: Support pe (pace break level)
SL: Below the low (average candle size)
Target: 1:3
```

### Why this works:

> "Bias overrides pattern." (S6, Line 97)
> "Buying trend, market retraces: no N/M check needed. Support identifies via pace-of-momentum break → execute directly." (S5)

**Selling = retracement.** Overview bullish hai toh support pe buy karo. **SHORT MAT KARO.**

---

## Case B7: Extreme Highs + Strong Buying = CONTINUATION

### Situation:

```
Pre-open: ▲ BULLISH (extreme zone — 85%+)
Market: Gap up / flat
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH — aggressive pace, healthy swing
```

### Kya ho raha hai:

Extreme highs + strong buying = market momentum ke saath ja raha hai. Overview bullish hai, market bhi bullish hai.

### Kya karna hai:

```
1. WITH FLOW trade
2. Swing HEALTHY hai? → Direct entry
3. Pace break identify karo
4. Support pe buy karo
5. SL tight rakho (momentum strong hai)
6. Target: 1:3
```

### Why this works:

> "At high levels / all-time high -> won't fall continuously." (S4)
> "Higher level test = strength." (S2)

---

## Case B8: Extreme Highs + Selling = RETRACEMENT (Don't Short!)

### Situation:

```
Pre-open: ▲ BULLISH (extreme zone — 85%+)
Market: Flat / gap up
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (selling swing)
```

### Kya ho raha hai:

Extreme highs + selling = retracement ho raha hai. Par tumhara bias BULLISH hai. **SHORT MAT KARO.**

### Decision tree:

```
Selling swing HEALTHY hai?
    │
    ├─ YES (strong selling)
    │       │
    │       ├─ Lower high bana? + Strong selling close?
    │       │       → UNBIASED (indecision) → SKIP karo
    │       │
    │       └─ Otherwise → Retracement hai, overview holds
    │               → Support pe BUY karo
    │
    └─ NO (weak selling) → "Weak selling swing → intraday high breakout expected" (S3)
            → Retracement hai, overview holds
            → Support pe BUY karo
```

### Why this works:

> "Extreme + closing opposes + otherwise → bias (retracement, overview holds)" (bias-engine-explained.md)

**Overview BULLISH hai.** Selling sirf retracement hai. Support pe buy karo.

---

## Case B9: Extreme Highs + Selling + Indecision = UNBIASED

### Situation:

```
Pre-open: ▲ BULLISH (extreme zone — 85%+)
Market: Selling aayi
Selling: Strong hai, lower high bana, selling close kiya
```

### Kya ho raha hai:

Extreme highs + strong selling + lower high + selling close = INDECISION. Market confuse hai.

### Kya karna hai:

```
1. ❌ SKIP karo
2. Aaj kuch nahi karna
3. Kal ka market dekho — direction woh lega jo pehla swing banega
```

### Why this works:

> "Extreme + closing opposes + lower high + strong sustain → UNBIASED (indecision)" (bias-engine-explained.md)

---

## Case B10: Morning View vs Overview Conflict

### Situation:

```
Pre-open: ▲ BULLISH
Market: Flat open
9:45-10:00: First swing = BEARISH (selling swing bana)
Overview: Still BULLISH
```

### Kya ho raha hai:

Morning view (first swing) bearish hai, par overview bullish hai. Conflict hai.

### Kya karna hai:

```
1. Morning view pehle execute karo
2. Selling swing ka trade lo (if confirmed)
3. Phir overview ka trade plan karo
4. Doosra trade Leg 2 ke through
```

### Why this works:

> "Morning view and major overview conflict → prioritize the morning view; execute it first." (S4)

---

# PART 2: BEARISH BIAS (▼)

> Tumne raat ko initial bias nikala: **▼ BEARISH**.
> Market khula. Ab kya?

---

## Case Bc1: Gap-Down + First Swing Bearish = EASIEST TRADE

### Situation:

```
Pre-open: ▼ BEARISH
Market: Gap down khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Gap-down matlab sellers strong hain. 9:45 ke baad selling swing bana = direction clear hai.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Selling swing identify karo
3. Swing HEALTHY hai? (red candles, shallow retrace, big size)
   → YES: WITH FLOW trade — direct entry milegi
   → NO (weak swing): Extra caution
4. Pace break identify karo
5. Resistance level mark karo
6. Retracement ka wait karo
7. Domination candle ka wait karo (red consuming green + close + follow-through)
8. ✅ SHORT karo
```

### Entry:

```
Entry: Resistance pe, domination candle ke baad
SL: Resistance ke thoda upar (average candle size)
Target: 1:3
```

### Why this works:

> "Gap-down in selling flow: continuation expected. Short on resistance." (S1)

**WITH FLOW trade.** Direct entry milegi.

---

## Case Bc2: Gap-Down + First Swing Bullish = RETRACEMENT (SHORT at Resistance!)

### Situation:

```
Pre-open: ▼ BEARISH
Market: Gap down khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Gap-down tha par buying aa gayi. **Par tumhara bias BEARISH hai.** Buying = RETRACEMENT hai, strength nahi. Overview protects you.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Buying swing bana
3. Buying IGNORE karo — overview bearish hai
4. Pace break identify karo (buying ka rhythm toota)
5. Resistance level mark karo
6. Domination candle ka wait karo (red consuming green + close + follow-through)
7. ✅ RESISTANCE PE SHORT karo
```

### Entry:

```
Entry: Resistance pe, domination candle ke baad (candle CLOSE ke time pe)
SL: Resistance ke thoda upar (average candle size)
Target: 1:3
```

### Why this works:

> "Bias overrides pattern." (S6, Line 97)
> "Gap-down in selling flow: continuation expected. Short on resistance." (S1)

**Gap-down = sellers strong.** Buying sirf retracement hai. Resistance pe short karo. **BUY MAT KARO.**

---

## Case Bc3: Gap-Up + First Swing Bearish = GAP IS RETRACEMENT (BEST OPPORTUNITY!)

### Situation:

```
Pre-open: ▼ BEARISH
Market: Gap up khula
9:15-9:45: Opening candles aaye
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

**Ye BEST case hai!** Bearish bias hai + prev day buying retracement thi + gap up = aur zyada premium mil raha hai. Gap UP hi retracement hai — market ne upar ja ke resistance test kar liya.

### Kya karna hai:

```
1. Gap-up ko BUY MAT KARO — flow bearish hai
2. "Gap-up in selling flow: gap IS the retracement" (S1)
3. 9:45 ke baad selling swing bana
4. Pace break identify karo
5. Resistance level mark karo
6. Domination candle ka wait karo
7. ✅ SHORT karo — better premium mil raha hai!
```

### Entry:

```
Entry: Resistance pe, domination candle ke baad
SL: Resistance ke upar
Target: 1:3
```

### Why this works:

> "Gap-up in selling flow: gap IS the retracement." (S1)

**Gap-up = free retracement = better entry price!**

---

## Case Bc4: Gap-Up + First Swing Bullish = RETRACEMENT (SHORT at Resistance!)

### Situation:

```
Pre-open: ▼ BEARISH
Market: Gap up khula
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Gap-up + buying = bullish signal dikh raha hai. **Par tumhara bias BEARISH hai.** Gap-up = FREE RETRACEMENT. Buying = retracement. Overview protects you.

### Kya karna hai:

```
1. Gap-up ko BUY MAT KARO — flow bearish hai
2. "Gap-up in selling flow: gap IS the retracement" (S1)
3. 9:45 ke baad buying swing bana
4. Buying IGNORE karo — overview bearish hai
5. Pace break identify karo
6. Resistance level mark karo
7. Domination candle ka wait karo
8. ✅ RESISTANCE PE SHORT karo — better premium mil raha hai!
```

### Entry:

```
Entry: Resistance pe, domination candle ke baad
SL: Resistance ke upar
Target: 1:3
```

### Why this works:

> "Gap-up in selling flow: gap IS the retracement." (S1)
> "Bias overrides pattern." (S6)

**Gap-up = free retracement = better entry price!** Buying IGNORE karo, resistance pe short karo. **BUY MAT KARO.**

---

## Case Bc5: Flat Open + First Swing Bearish = DIRECT WITH FLOW

### Situation:

```
Pre-open: ▼ BEARISH
Market: Flat open
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Flat open + selling = WITH FLOW. Simple hai.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Selling swing bana
3. Swing HEALTHY hai? → WITH FLOW direct entry
4. Pace break identify karo
5. S/R level mark karo (resistance)
6. Retracement ka wait karo
7. Domination candle ka wait karo
8. ✅ SHORT karo
```

### Entry:

```
Entry: Resistance pe (pace break level)
SL: Above the high (average candle size)
Target: 1:3
```

---

## Case Bc6: Flat Open + First Swing Bullish = RETRACEMENT (SHORT at Resistance!)

### Situation:

```
Pre-open: ▼ BEARISH
Market: Flat open
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Flat open + buying = bullish dikh raha hai. **Par tumhara bias BEARISH hai.** Buying = RETRACEMENT hai. Overview protects you.

### Kya karna hai:

```
1. 9:15-9:45: OBSERVE karo
2. 9:45 ke baad: Buying swing bana
3. Buying IGNORE karo — overview bearish hai
4. Pace break identify karo (buying ka rhythm toota)
5. Resistance level mark karo
6. Domination candle ka wait karo (red consuming green + close + follow-through)
7. ✅ RESISTANCE PE SHORT karo
```

### Entry:

```
Entry: Resistance pe (pace break level)
SL: Above the high (average candle size)
Target: 1:3
```

### Why this works:

> "Bias overrides pattern." (S6, Line 97)

**Buying = retracement.** Overview bearish hai toh resistance pe short karo. **BUY MAT KARO.**

---

## Case Bc7: Extreme Lows + Strong Selling = CONTINUATION

### Situation:

```
Pre-open: ▼ BEARISH (extreme zone — 15% or less)
Market: Gap down / flat
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH — aggressive pace, healthy swing
```

### Kya ho raha hai:

Extreme lows + strong selling = market momentum ke saath ja raha hai. Overview bearish hai, market bhi bearish hai.

### Kya karna hai:

```
1. WITH FLOW trade
2. Swing HEALTHY hai? → Direct entry
3. Pace break identify karo
4. Resistance pe short karo
5. SL tight rakho (momentum strong hai)
6. Target: 1:3
```

### Why this works:

> "At lower levels -> won't rise continuously." (S4)
> "Lower level test = weakness." (S2)

---

## Case Bc8: Extreme Lows + Buying = RETRACEMENT (Don't Buy!)

### Situation:

```
Pre-open: ▼ BEARISH (extreme zone — 15% or less)
Market: Flat / gap down
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (buying swing)
```

### Kya ho raha hai:

Extreme lows + buying = retracement ho raha hai. Par tumhara bias BEARISH hai. **BUY MAT KARO.**

### Decision tree:

```
Buying swing HEALTHY hai?
    │
    ├─ YES (strong buying)
    │       │
    │       ├─ Higher low bana? + Strong buying close?
    │       │       → UNBIASED (indecision) → SKIP karo
    │       │
    │       └─ Otherwise → Retracement hai, overview holds
    │               → Resistance pe SHORT karo
    │
    └─ NO (weak buying) → "Weak buying swing → intraday low breakdown expected" (S3)
            → Retracement hai, overview holds
            → Resistance pe SHORT karo
```

### Why this works:

> "Extreme + closing opposes + otherwise → bias (retracement, overview holds)" (bias-engine-explained.md)

**Overview BEARISH hai.** Buying sirf retracement hai. Resistance pe short karo.

---

## Case Bc9: Extreme Lows + Buying + Indecision = UNBIASED

### Situation:

```
Pre-open: ▼ BEARISH (extreme zone — 15% or less)
Market: Buying aayi
Buying: Strong hai, higher low bana, buying close kiya
```

### Kya ho raha hai:

Extreme lows + strong buying + higher low + buying close = INDECISION. Market confuse hai.

### Kya karna hai:

```
1. ❌ SKIP karo
2. Aaj kuch nahi karna
3. Kal ka market dekho — direction woh lega jo pehla swing banega
```

### Why this works:

> "Extreme + closing opposes + higher low + strong sustain → UNBIASED (indecision)" (bias-engine-explained.md)

---

# PART 3: UNBIASED (●)

> Tumne raat ko initial bias nikala: **● UNBIASED**.
> Market khula. Ab kya?

---

## Case U1: First Swing Bullish = Take Bullish Direction

### Situation:

```
Pre-open: ● UNBIASED
Market: Flat open
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BULLISH (green candles, buying swing)
```

### Kya ho raha hai:

Unbiased + first swing bullish = market ne direction de diya. Ab usi direction mein trade karo.

### Kya karna hai:

```
1. First swing observe karo (bullish)
2. Swing HEALTHY hai? → Direct entry
3. Pace break identify karo
4. S/R level mark karo (support)
5. Retracement ka wait karo
6. Domination candle ka wait karo
7. ✅ BUY karo
```

### Entry:

```
Entry: Support pe
SL: Below the low
Target: 1:3
```

### Why this works:

> "Previous day gave no clarity -> NEXT DAY take direction of the FIRST swing that forms." (S6)

---

## Case U2: First Swing Bearish = Take Bearish Direction

### Situation:

```
Pre-open: ● UNBIASED
Market: Flat open
9:15-9:45: Opening candles
First swing (= 9:15→9:45 ka initial move KHUD): BEARISH (red candles, selling swing)
```

### Kya ho raha hai:

Unbiased + first swing bearish = market ne direction de diya (neeche).

### Kya karna hai:

```
1. First swing observe karo (bearish)
2. Swing HEALTHY hai? → Direct entry
3. Pace break identify karo
4. S/R level mark karo (resistance)
5. Retracement ka wait karo
6. Domination candle ka wait karo
7. ✅ SHORT karo
```

---

## Case U3: No Clear Swing = SKIP

### Situation:

```
Pre-open: ● UNBIASED
Market: Flat open
9:15-9:45: Opening candles
9:45-10:00: No clear swing (choppy)
10:00-11:12: Still choppy, no domination
```

### Kya ho raha hai:

Unbiased + no clear swing = market ne direction nahi diya.

### Kya karna hai:

```
1. ❌ SKIP karo
2. Aaj kuch nahi karna
3. "No reversal/domination failure = don't trade the case" (S4)
```

---

## Case U4: After Trending Day = EASIEST Session

### Situation:

```
Pre-open: ● UNBIASED
Previous day: Trending day tha (big move up ya down)
Market: Flat / small gap
```

### Kya ho raha hai:

Kal trending day tha. Aaj sabse easy session hai.

### Kya karna hai:

```
1. First swing dekho
2. Kal ke trend ke OPPOSITE side pe trade karo (reversal expected)
3. Example: Kal buying trend tha → aaj resistance pe short karo
4. Expectation: low breakdown
```

### Why this works:

> "Sessions AFTER trending sessions are EASIEST. Plan: short resistance, expectation = low breakdown." (S6)

---

## Case U5: Indecision Market = Wait for Tomorrow

### Situation:

```
Pre-open: ● UNBIASED
Market: Opens
9:45-10:00: Buying swing bana → phir selling aayi
10:00-11:12: Choppy, no clear direction
```

### Kya karna hai:

```
1. ❌ SKIP karo
2. "ATH made -> sell-off -> support -> LOWER HIGH -> selling arrived
    and the day CLOSED on selling-side support = indecision market,
    movement possible both ways, NO bias held." (S6)
3. "When confused there's ONE path — wait for tomorrow and observe." (S6)
```

---

# QUICK REFERENCE

## Timeline:

```
9:15 ─── OPENING (first swing forming — NO TRADE)
9:45 ─── SETTLE (observe direction)
~10:00 ─── FIRST SWING COMPLETE + S/R FORMED (start trading)
10:00-11:12 ─── BEST EXECUTION WINDOW
11:12 ─── CUT OFF
12:00 ─── ABSOLUTE (nothing)
1-2 PM ─── SECOND SESSION (needs volume)
```

## Gap Rules:

```
Gap-up + Buying flow → Gap IS continuation → Buy at support
Gap-up + Selling flow → Gap IS retracement → Buy at support (Overview bullish!)
Gap-down + Buying flow → Gap IS retracement → Buy at support (BETTER PRICE!)
Gap-down + Selling flow → Gap IS continuation → Short at resistance
```

**Key:** "Bias overrides pattern." (S6) — Agar overview BULLISH hai toh selling = retracement → BUY at support. Agar overview BEARISH hai toh buying = retracement → SHORT at resistance.

## Swing Quality Check:

```
Healthy Swing → WITH FLOW direct entry
Weak Swing → Extra caution, better confirmation, or skip
Weak selling swing → "intraday high breakout expected" (S3) — don't short
Weak buying swing → "intraday low breakdown expected" (S3) — don't buy
Buying swing VOIDED → 3-4 consecutive candles break lows
```

## Overview Rules:

```
OVERVIEW = DIRECTION (hamesha)
First swing = ENTRY POINT (kahan enter karna hai)

BULLISH overview + selling = RETRACEMENT → BUY at support
BEARISH overview + buying = RETRACEMENT → SHORT at resistance

"Bias overrides pattern." (S6)
```

## Risk Rules:

```
SL = Average candle size (never at extreme)
Target = 1:3 (or 1:2 / 1:1.5 if 1:3 unavailable)
Max entries = 2 per day
Trailing = NEVER
After entry = NO analysis
No confidence = NO execution
Entry at CLOSING TIME of candle (not mid-candle)
```

---

*Reference: `intraday-trading-system.md` for detailed rules*
*Reference: `bias-engine-explained.md` for initial bias calculation*

---

# CASE MASTER LIST — Implementation Tracker

> Engine har din ko in cases mein se EK classify karta hai (`case` field har
> trade pe). Panel ke **Case dropdown** se kisi bhi case ke trades/stats/chart
> boxes filter hote hain. Status: ✅ implemented · ⚠️ partial/emergent · ❌ TODO

## Cases — Biased Days (▲ / ▼)

| Case | Bias | Open | First Swing | Action | Status |
|------|------|------|-------------|--------|--------|
| B1  | ▲ | Gap-Up    | Bullish | WITH FLOW direct entry              | ✅ |
| B2  | ▲ | Any       | Bearish | RETRACE — counter-break level pe support buy | ✅ |
| B3  | ▲ | Gap-Down  | Bullish | Gap IS retrace — WITH FLOW direct   | ✅ |
| B4  | ▲ | Gap-Down  | Bearish | RETRACE — support buy (better price) | ✅ |
| B5  | ▲ | Flat      | Bullish | WITH FLOW direct                    | ✅ |
| B6  | ▲ | Flat      | Bearish | RETRACE — support buy               | ✅ |
| B7  | ▲ extreme-highs | Any | Strong Buying | Continuation WITH FLOW     | ✅ |
| B8  | ▲ extreme-highs | Any | Selling | RETRACE — don't short             | ✅ |
| B9  | ▲ extreme-highs | Selling + LH + strong selling close | INDECISION → skip | ⚠️ natural (prev-day concept) |
| B10 | ▲ | Any conflict | Morning view vs overview | Bias overrides — aligned only | ✅ concept |

Mirror: Bc1–Bc10 (▼) same logic, opposite direction. ✅

## Cases — Unbiased Days (●)

| Case | Bias | Condition | Action | Status |
|------|------|-----------|--------|--------|
| U1 | ● | First swing Bullish | Take bullish direction, trade | ✅ |
| U2 | ● | First swing Bearish | Take bearish direction, trade | ✅ |
| U3 | ● | No clear swing / choppy | SKIP                          | ✅ natural |
| U4 | ● | Kal TRENDING day tha | Opposite-of-yesterday plan ("easiest session") | ❌ TODO |
| U5 | ● | Indecision tape (LH + sell-close) | Wait for tomorrow | ✅ natural |

## Modifiers & Concepts — TODO Queue (one at a time implement honge)

| # | Concept | Source | Kya Karta Hai | Status |
|---|---------|--------|---------------|--------|
| M1 | **Swing Health System** | S3/S4 | Healthy vs weak swing (retracement depth + size); Type A/B; two-point weakness; weak swing → breakout expected (support-hold wait galat) | ❌ TODO |
| M2 | Double-domination / END pattern | S4/S6 | Side dominated → opposed → phir dominate = opposing side high-probability | ❌ TODO |
| M3 | Wick-domination variant | S6 | Upper/lower-wick domination + reversal + sustaining = valid pattern break | ❌ TODO |
| M4 | Exhaustion counts | S6 | Gap-up from highs: counter-swing ~5/8/10 candles chalta hai | ❌ TODO |
| M5 | Fake break-up pattern | S2-doc | Break-up jo fail ho → reverse signal classification | ❌ TODO |
| M6 | 70-80% recovery execute rule | S2/S4 | Deep recovery of prior leg = execution zone | ❌ TODO |
| M7 | Target fallback 1:2 / 1:1.5 | Risk rules | Jab 3R structure allow na kare | ❌ TODO |
| M8 | Second session (1-2 PM) | S5 | Volume-conditioned second window (index volume N/A — proxy chahiye) | ❌ TODO |
| M9 | Entry Type 1 vs Type 2 | Phase 2 | Aggressive vs conservative entry styles | ❌ TODO |
| M10 | Oversized-SL exception | S6 | Points kam hon toh SL slightly bigger than avg near low | ⚠️ partial (structure anchor) |
| —  | Volume doubling on domination | S5 | Index spot volume = 0 → N/A | N/A |
| —  | Options buying/strikes | S5/S6 | Spot backtest scope se bahar | N/A |

## Classification Inputs (engine-side)

```
bias_eff   : bullish | bearish | unbiased(U1/U2 first-swing se)
gap_type   : gap-up | gap-down | flat     ← |open − prev_close| ≥ 0.27% (configurable;
                                            researched from labeled examples Oct-Dec'25
                                            + Mar-Apr'26 — 8/9 separation)
extreme    : highs | lows | none          ← bias overview zone (≥85% / ≤15%)
swing_dir  : buying | selling             ← engine ka first-swing classification

NOTE: prev_close/open 5-MIN data se aate hain (daily CSV kuch dates pe
corrupt hai — 237/260 rows mismatch, rebuild TODO).
```

---

*Reference: `intraday-trading-system.md` for detailed rules*
*Reference: `bias-engine-explained.md` for initial bias calculation*