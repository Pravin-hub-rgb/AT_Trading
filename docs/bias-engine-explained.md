# Ek Din Ka Bias — Shuru Se Aakhir, Har Scenario Ke Saath

> Ye kahani **21 August** ke label ki hai — jo asal me **20 August ki RAAT ko** hi ban jata hai (close ke turant baad).
> Subah sirf dekhna hota hai kya bana. Har scene pe "par agar..." likha hai — wahi saare possible scenarios hain.
> (S1–S6 = course session files reference)

---

## Scene 0 — Raat ko (market band hua)

Bees August ka session khatam hua. Nifty ne close kiya **24231.85** pe.
Bas — aaj ka data ab freeze ho gaya. Aur abhi, isi raat, **kal ka bias ban jayega**.
Monday ka bias Friday raat ko ready. Subah koi calculation nahi — sirf dekhna hai kya likha aaya.

---

## Scene 1 — Wahi raat: daily chart kholo

Do cheezein dhoondni hain: sabse **aakhri confirmed swing high** aur sabse **aakhri confirmed swing low**.

Mil gaye:
- **SH 24774.30** — 3 August ka high. Candidate 3 Aug ko bana tha, par confirm hua lagbhag 17 August ko — kyunki rule hai: candidate ke baad **10 trading din tak break na ho**, tabhi wo swing kehlayega.
- **SL 23606.30** — 24 July ka low. Waise hi apne 10 din poori karke July ke end me confirm hua tha.

*Par agar... koi level abhi-abhi bana ho? Wo engine ko dikhta hi nahi — unconfirmed candidate invisible hai. Isi wajah se backtest aur live dono ko bilkul same cheez dikhti hai.*

---

## Scene 2 — Window slide check (roz ka ritual)

Ek sawaal: **kal ke close ke baad koi naya swing confirm to nahi ho gaya?**

Aaj: nahi hua. Window wahi purani rahegi — SH 24774.30 / SL 23606.30.

*Par agar... hota? Jaise end-of-August me 24025 wala low confirm hua tha — us din window SLIDE karti hai, naya range ban jata hai, aur pos dobara calculate hoti hai. Zone flip bhi ho sakta hai. Isliye ye check roz zaroori hai.*

---

## Scene 3 — Kal ka close ko range me rakho

Scale samjho: **0% = SL pe chipka hua, 100% = SH pe chipka hua.**

pos = (24231.85 − 23606.30) ÷ (24774.30 − 23606.30) ≈ **54%**

Beech-betar, thoda upar ki taraf. Ab asli sawaal shuru.

---

## Scene 4 — Zone check (ek-ek karke, saare possibilities)

**Kya close SH ke UPAR nikal gaya? (100% se aage)**
Nahi.
*Par agar hota — Zone 0: naya high ban chuka. Bias ▲ BUYING. Short yahan kabhi nahi (strength side, S4 veto). Haan, continuously nahi chalega — exhaustion se steps/pullbacks aayenge (S3/S5) — par dip hi best buying opportunity hai (S6). Bias tabhi badlega jab wahan LOWER HIGH banne lage.*

**Kya close SH ke paas hai? (70–100%)**
Nahi.
*Par agar hota — Zone 1: ▲ BUYING. High test = strength. Bas.*

**Kya close SL ke paas hai? (0–30%)**
Nahi.
*Par agar hota — Zone 3: ▼ SELLING. Low test = weakness.*

**Kya close SL ke NEECHE hai? (0% se neeche)**
Nahi.
*Par agar hota — Zone 4: naya low ban raha hai. ▼ SELLING hi rehta hai — strength se tode ja raha hai to jab tak bounce karke wapas confirmed SL ke upar na aa jaye. (Rare flow-end reversal setup v2 me suppress hai — simple rakha hai.)*

**Toh kahan hai? Beech me. (30–70%) → ZONE 2**
Yahan akela location kaafi nahi. Ab poochte hain — **kis taraf se aa rahe ho?**

---

## Scene 5 — Zone 2 ka path

Aakhri confirm hone wala pivot kaunsa tha? **HIGH** (SH, 3 Aug — SL se baad ka).
Matlab top ban ke hum gir rahe hain — *falling from the swing high.*

Aur pos 54% hai — 40% se upar. Rule lagta hai:
**falls come in steps** — seedhi nahi girti, bounce le lete hue girti hai.
→ **LEAN MILI: ▲ BUYING**

*Par agar... SL se UTTE hote (last pivot LOW hota) aur pos ≤ 60% hota — to ▼ SELLING (rises pehle resistance leti hain).*
*Par agar... 30–40% ya 60–70% wali patli patti me hote — picture CHUP rehti (silent). Tab Scene 6 ka jawab hi final hota.*
*Par agar... lean mili hi nahi hoti aur closing read bhi ulta bolti — phir bhi zone jeet-ta ("the overview protects you"). Aur agar zone chup hota aur closing read ladti — UNBIASED.*

Abhi lean mil gayi — **ye final hai**, agle scene sirf double-check hai.

---

## Scene 6 — Helper layers: kal ke 5-min candles se do jawab

### Helper 1 — Swing STRUCTURE (primary helper)

Kal ke 5-min candles pe wahi pivot detector chalta hai jo chart pe chalta hai.
**Pivots POORE DIN (9:15-15:30) se calculate hote hain** — sirf closing session se nahi.
Har swing ko pichhle same-kind swing se compare karke tag milta hai:

- Highs: pichhle high se upar = **HH**, neeche = **LH**
- Lows: pichhle low se upar = **HL**, neeche = **LL**

Structure verdict:
- **HH + HL sequence = bullish structure**
- **LH + LL sequence = bearish structure**
- mix hua = mixed/unclear

Aur ek check — **break-with-close**: din ke aakhri swing high/low ke paar candle CLOSE bhi hui?
(Sirf wick ghusi to count nahi — S5/S6 ka domination rule.)

Aaj nikla: **mixed** — `HHx2/LHx4; HLx2/LLx1 | prior low closed beyond`.

**Kyun poore din se?** Course kehta hai previous day ka analysis poore din ka structure dekhna hai — sirf 12:00-3:30 nahi. First swing (9:15-9:45) bhi count karta hai, par uski pivots ke liye sufficient data chahiye (n=4 each side).

### Helper 2 — Sustain check (close position in FULL DAY range)

Din ke close ka position **poore din ke range** ke andar check hota hai:

- **Close in top 30% of day range** → strong sustain (bullish)
- **Close in bottom 30% of day range** → strong sustain (bearish)
- **Close in middle 40%** → weak sustain (ambiguous)

**20 August ka data:**
Day high 24262.85, Day low 24176.85 → Range = 86.0 pts
Close 24231.85 → (24231.85 - 24176.85) ÷ 86.0 ≈ **63%** — middle area
→ Sustain: **weak**

### Helper 3 — Closing session read (12:00-3:30 net move)

12:00 se 15:30 tak ka net move / day range se signal milta hai.

**20 August ka data:**
Session open 24216.55 → session close 24232.95 = **+16.4 pts**
Range 86.0 pts → 16.4 ÷ 86.0 ≈ **19%** — threshold 15% se upar.
→ Read: ▲ **buying held into 12-3:30**

*Aaj ke example me closing session ▲ bol raha hai, par structure mixed hai aur sustain weak hai — toh UNBIASED.*

---

## Scene 7 — MERGE (final verdict)

```
Zone (bigger picture):   ▲ BUYING lean      ← boss
Prev-day structure:      mixed              ← chup (kuch prove nahi)
Sustain (full day):      weak               ← chup (middle 40%)
Closing session read:    ▲ buying held      ← agrees
```

Hierarchy: **Zone > Structure > Sustain > Closing read > UNBIASED**. Zone ki lean mili to wahin khatam —
neeche wale sirf reason me likhe jaate hain ("both layers agree" / "overrides").

**FINAL LABEL — 21 AUGUST: ▲ BULLISH**

Chart pe 21 Aug ki pehli candle ke neeche marker, SH/SL dashed lines,
zone-boundary dots, prev-day swing dots (HH/HL green · LH/LL orange) —
aur tooltip me alag sections: `ZONES:` aur `PREV DAY:`.

---

## EXTREME ZONES — Har Scenario Detail Mein

Jab market all-time high ya major low ke paas hoti hai, to special rules lagte hain.
Ye rules course ke **Session 4** aur **Session 6** se aate hain.

### Zone 0 / Zone 1 — EXTREME HIGHS (pos ≥ 85%)

Market Strength zone me hai. Course kehta hai:

> "At an all-time high we don't short — even if a buying swing reverses." (S4, Line 41)

Lekin ye blanket rule nahi hai. Closing session ke data se nuance aata hai.

---

### SCENARIO A: Extreme highs + Closing session BULLISH (dono agree)

**Kya hota hai:** Market extreme highs pe hai (pos ≥ 85%). Kal ka closing session (12:00-15:30) me buying hui — price upar close hui.

**Example:**
- Zone: `new_high` (pos = 102%, SH ke upar)
- Closing signal: `bullish` (net +45 pts, 22% of day range)
- Sustain: `strong` (close session ke top 30% me)

**Result: ▲ BULLISH**

**Kyun:** Dono layers agree karte hain. Overview kehta hai "at highs, won't fall continuously" aur closing session bhi buying dikha raha hai. Koi conflict nahi. "Both layers agree."

**Kab kabhi galat ho sakta hai:** Agar next din lower high ban jaaye to fresh analysis chahiye — par raat ko ye label sahi hai.

---

### SCENARIO B: Extreme highs + Closing session FLAT (kuch nahi bola)

**Kya hota hai:** Market extreme highs pe hai. Closing session me koi clear direction nahi — net move bahut chhota hai (threshold 15% se neeche).

**Example:**
- Zone: `highs_extreme` (pos = 88%)
- Closing signal: `None` (net +5 pts, 3% of day range — flat)
- Sustain: `weak` (close beech me)

**Result: ▲ BULLISH**

**Kyun:** Closing session ne kuch nahi bola. Jab closing chup hota hai, to overview ka default lagta hai. Extreme highs pe overview hamesha bullish hai — "strength side, no shorting." Closing session flat hai to koi conflict bhi nahi.

**Course reference:** Closing session flat = "12-3:30 flat/ambiguous" — koi signal nahi, overview ka default chalega.

---

### SCENARIO C: Extreme highs + Closing session BEARISH + WEAK sustain (retracement — healthy)

**Kya hota hai:** Market extreme highs pe hai. Closing session me selling hui — lekin close beech me tha (din ke bottom 30% ke upar). Matlab selling hui par sustained nahi hui.

**Example:**
- Zone: `highs_extreme` (pos = 91%)
- Closing signal: `bearish` (net -20 pts, 10% of day range)
- Sustain: `weak` (close at 45% of full day range — mid-area)

**Result: ▲ BULLISH (retracement, healthy)**

**Kyun:** Ye NORMAL retracement hai. Course kehta hai:

> "Market never moves in one direction forever. It typically makes two or three swings before its final high." (S1, Lines 20-22)

> "Retracement does NOT invalidate your swing." (S1, Line 22)

Extreme highs pe profit booking aana normal hai. Selling hui par sustained nahi — matlab buyers ne support diya, close beech me raha. Ye "healthy pullback" hai. Overview bullish rehta hai.

**Kaise pehchane — retracement vs weakness:**
- Retracement = selling hui par close mid-range me (weak sustain) → bullish hold
- Weakness = selling hui aur close din ke bottom pe (strong sustain) → Scenario D dekho

**Course reference:** "Falls come in steps" (S2) — extreme highs se girte waqt bounce aate hain, ye unme se ek hai.

---

### SCENARIO D: Extreme highs + Closing session BEARISH + STRONG sustain + LOWER HIGH formed (indecision)

**Kya hota hai:** Market extreme highs pe hai. Closing session me strong selling hui — close din ke bottom pe hai (strong sustain). Aur sabse important: **lower high bana hai** — matlab kal ke din me price ne naya high banane ki koshish ki par ASLI high se neeche reh gaya.

**Example:**
- Zone: `highs_extreme` (pos = 89%)
- Closing signal: `bearish` (net -55 pts, 28% of day range)
- Sustain: `strong` (close at 12% of full day range — near bottom)
- **Lower high: YES** (kal ka high = 24750, parso ka high = 24820 → lower high)

**Result: ● UNBIASED (indecision)**

**Kyun:** Ye woh exact pattern hai jo **Session 6** me describe kiya gaya hai:

> "ATH made -> sell-off -> support -> LOWER HIGH -> selling arrived and the day CLOSED on selling-side support = indecision market, movement possible both ways, NO bias held." (S6, Lines 9-11)

Teen cheezein ek saath hui hain:
1. **Extreme highs** — market strength zone me tha
2. **Lower high formed** — price naya high nahi bana paaya, buyers fail hue
3. **Strong selling close** — selling sustained thi, close support ke paas

Jab ye teeno milke aayein — to "indecision" hai. Na bullish bol sakte (kyunki lower high = weakness), na bearish (kyunki extreme highs pe short karna course ke against hai). Toh **UNBIASED**.

**Course ka confusion protocol:**
> "When confused there's ONE path — wait for tomorrow and observe." (S6, Line 13)
> "Previous day gave no clarity -> NEXT DAY take direction of the FIRST swing that forms." (S6, Line 92-94)

**Kaise detect karte hain stale data se:**
1. Check karo: closing session bearish hai? (signal = bearish)
2. Check karo: sustain strong hai? (close session range ke bottom 30% me)
3. Check karo: lower high bana hai? (kal ka high < parso ka high)
4. Teeno YES → UNBIASED

---

### SCENARIO E: Extreme highs + Closing session BEARISH + STRONG sustain but NO lower high (retracement, still bullish)

**Kya hota hai:** Scenario D jaisa hi — strong selling close hai — par lower high NAHI bana. Kal ka high parso ke high se UPAR hai. Matlab price ne naya high banaya, phir profit booking aayi.

**Example:**
- Zone: `new_high` (pos = 105%, naya ATH ban chuka)
- Closing signal: `bearish` (net -40 pts, 20% of day range)
- Sustain: `strong` (close at 15% of full day range)
- **Lower high: NO** (kal ka high = 24900, parso ka high = 24820 → NEW HIGH, not lower)

**Result: ▲ BULLISH (retracement)**

**Kyun:** Lower high nahi bana — matlab buyers ne pehle naya high banaya. Phir profit booking aayi. Ye healthy retracement hai, weakness nahi. Course kehta hai:

> "Even a continuously rising market cannot go up in one straight line forever — profit booking enters, exhaustion enters, and it WILL retrace." (S3, Line 150)

Naya high banna = strength. Uske baad selling = exhaustion/profit booking = normal. Overview bullish rehta hai.

**Fark Scenario D se:**
| | Scenario D (Indecision) | Scenario E (Retracement) |
|---|---|---|
| Lower high bana? | HAAN — buyers fail | NAHI — naya high bana |
| Selling kyun hui? | Buyers weak hue | Profit booking / exhaustion |
| Bias | ● UNBIASED | ▲ BULLISH |

---

### SCENARIO F: Extreme lows + Closing session BULLISH + STRONG sustain + HIGHER LOW formed (indecision — mirror case)

**Kya hota hai:** Market extreme lows pe hai (pos ≤ 15%). Closing session me strong buying hui — close din ke top pe hai. Aur **higher low bana** — price ne support test kiya par previous low se upar raha.

**Example:**
- Zone: `lows_extreme` (pos = 8%)
- Closing signal: `bullish` (net +60 pts, 30% of day range)
- Sustain: `strong` (close at 88% of full day range — near top)
- **Higher low: YES** (kal ka low = 23650, parso ka low = 23580 → higher low)

**Result: ● UNBIASED (indecision — mirror)**

**Kyun:** Scenario D ka mirror hai. Extreme lows pe buyers aa rahe hain par abhi structure clear nahi — higher low bana (strength) par extreme zone ke andar (weakness context). Dono taraf se signal aa rahe hain = indecision.

**Course reference:** "At lower levels -> won't rise continuously" (S4, Line 38) — par lower high bana hai to upward move bhi weak hai. Confusion = unbiased.

---

### SCENARIO G: Extreme lows + Closing session BEARISH (dono agree — weakness)

**Kya hota hai:** Market extreme lows pe hai. Closing session me bhi selling hui — close din ke bottom pe.

**Example:**
- Zone: `new_low` (pos = -3%, SL ke neeche)
- Closing signal: `bearish` (net -35 pts, 18% of day range)
- Sustain: `strong` (close at 10% of full day range)

**Result: ▼ BEARISH**

**Kyun:** Dono layers agree. Extreme lows = weakness zone. Closing session bhi selling dikha raha hai. "Both layers agree" — weakness confirmed.

---

### SCENARIO H: Extreme lows + Closing session FLAT (default to overview)

**Kya hota hai:** Market extreme lows pe hai. Closing session flat hai — koi clear direction nahi.

**Example:**
- Zone: `lows_extreme` (pos = 12%)
- Closing signal: `None` (net +3 pts, 2% of day range)
- Sustain: `weak`

**Result: ▼ BEARISH**

**Kyun:** Closing flat hai to overview ka default. Extreme lows = bearish overview. Koi conflict nahi = bearish.

---

### SCENARIO I: Extreme lows + Closing session BULLISH + WEAK sustain (retracement — healthy)

**Kya hota hai:** Market extreme lows pe hai. Closing session me buying hui par close beech me hai (strong nahi).

**Example:**
- Zone: `lows_extreme` (pos = 10%)
- Closing signal: `bullish` (net +15 pts, 8% of day range)
- Sustain: `weak` (close at 55% of full day range)

**Result: ▼ BEARISH (retracement from lows, healthy bounce)**

**Kyun:** Mirror of Scenario C. Extreme lows se bounce aayi par sustained nahi — matlab weak bounce hai. "Rises take resistance first" (overview logic). Overview bearish rehta hai.

---

### SCENARIO J: Extreme lows + Closing session BULLISH + STRONG sustain but NO higher low (retracement, still bearish)

**Kya hota hai:** Strong buying close hai par higher low NAHI bana — kal ka low parso ke low se NEECHE hai. Naya low bana, phir bounce aayi.

**Example:**
- Zone: `new_low` (pos = -2%)
- Closing signal: `bullish` (net +50 pts, 25% of day range)
- Sustain: `strong` (close at 90% of full day range)
- **Higher low: NO** (kal ka low = 23500, parso ka low = 23580 → NEW LOW, not higher)

**Result: ▼ BEARISH (retracement)**

**Kyun:** Naya low banna = sellers strong. Uske baad bounce = normal retracement. "At lower levels -> won't rise continuously" — bounce aayegi par naya trend nahi abhi. Overview bearish rehta hai.

---

## NON-EXTREME ZONES — Jab Zone chup ho

### SCENARIO K: Behavioral zone (70-85% ya 15-30%) + Closing session decides

**Kya hota hai:** Market highs ya lows ke paas hai (70-85% ya 15-30%), par extreme nahi. Zone ka apna lean nahi — closing session decides.

**Example:**
- Zone: `highs` (pos = 78%) — lean = None (behavioral)
- Closing signal: `bullish` (net +30 pts, 16% of day range)
- Sustain: `strong` (close at 75% of full day range)

**Result: ▲ BULLISH**

**Kyun:** Zone chup hai (behavioral zone = "don't short" par lean nahi). Closing session ne bola = closing session jeeta. Strong sustain + clear direction = closing session decides.

**Course reference:** "At major highs - behavioral: no short, closing session decides" (overview.py)

---

### SCENARIO L: Behavioral zone + Closing session flat → Overview tiebreaker

**Kya hota hai:** Zone chup hai + closing session bhi chup hai.

**Example:**
- Zone: `highs` (pos = 75%) — lean = None
- Closing signal: `None` (flat)
- Sustain: `weak` (close at 50% of full day range)

**Result: ▲ BULLISH (overview lean as tiebreaker)**

**Kyun:** Jab sab chup ho — overview lean as weak tiebreaker kaam karta hai. `highs` zone = "don't short" = implicit bullish lean. Not strong, but better than nothing.

---

### SCENARIO M: Mid zone (30-70%) + Closing session strong → Closing session decides

**Kya hota hai:** Market beech me hai. Zone ka lean nahi (mid_fall_unclear ya mid_rise_unclear). Closing session strong hai.

**Example:**
- Zone: `mid_fall_unclear` (pos = 45%) — lean = None
- Closing signal: `bearish` (net -40 pts, 20% of day range)
- Sustain: `strong` (close at 15% of full day range)

**Result: ▼ BEARISH**

**Kyun:** Zone chup + closing strong = closing session decides. Direction mili + sustain strong = bearish.

---

### SCENARIO N: Mid zone + Closing session flat + Flow agrees with overview → Double confirmation

**Kya hota hai:** Zone lean hai + flow bhi same side hai. Closing session flat hai par dono layers agree.

**Example:**
- Zone: `falling_from_highs` (pos = 58%) — lean = ▲ BULLISH
- Flow: `bullish` (HHx3/HLx3)
- Closing signal: `None` (flat)

**Result: ▲ BULLISH (overview + flow agree)**

**Kyun:** Overview + flow dono bullish = double confirmation. Closing flat hai to koi tension nahi.

---

### SCENARIO O: Koi layer nahi bol raha → UNBIASED

**Kya hota hai:** Zone lean nahi, closing session flat, flow bhi nahi.

**Example:**
- Zone: `mid_fall_unclear` — lean = None
- Closing signal: `None`
- Flow: None

**Result: ● UNBIASED**

**Kyun:** "Sab chup" — koi bhi layer direction nahi de raha. Pre-open lean nahi mila. Direction **morning behaviour** degi (live bias, alag concept).

---

## INDECISION vs RETRACEMENT — Quick Reference

| Signal | Indecision (UNBIASED) | Retracement (Overview holds) |
|---|---|---|
| **Extreme zone** | HAAN | HAAN |
| **Closing opposes** | HAAN (strong sustain) | HAAN (weak OR strong sustain) |
| **Lower/Higher high/low** | HAAN — structural failure | NAHI — new high/low bana |
| **Sustain** | Strong (close at extreme of full day range) | Weak (close mid-range) ya Strong par no lower high |
| **Course reference** | S6, Lines 9-14: "indecision market" | S1, Line 22: "retracement does NOT invalidate" |
| **Result** | ● UNBIASED | Overview bullish/bearish rehta hai |

**Decision tree:**
```
Extreme zone + closing opposes?
  ├─ Lower/higher high/low + strong sustain?
  │   └─ YES → UNBIASED (indecision)
  └─ NO (no structural failure ya weak sustain)
      └─ Overview holds (retracement)
```

---

## Multi-day Flow — Kab kaam aata hai

Flow tab kaam aata hai jab baaki sab chup ho:

```
Extreme zone override?     → NO (non-extreme zone)
Closing session strong?    → NO (flat ya weak)
Zone lean exists?          → NO (behavioral/mid zone)
Flow (3-6 day trend)?      → YES (HH+HL ≥ 3 ya LH+LL ≥ 3)
                            → Flow decides
```

**Flow as tiebreaker:**
- HH+HL ≥ 3 → bullish flow → bias bullish
- LH+LL ≥ 3 → bearish flow → bias bearish
- Mix → no flow signal → UNBIASED

**Flow confirmation:**
- Zone lean + flow same side → double confirmation → stronger bias
- Zone lean + flow opposite → zone wins (flow sirf tiebreaker hai, override nahi)

---

## Saare Scenarios Ek Nazar Me (recap)

**Extreme highs (pos ≥ 85%):**
- Closing bullish → ▲ BULLISH (agree)
- Closing flat → ▲ BULLISH (default)
- Closing bearish + weak sustain → ▲ BULLISH (retracement, healthy)
- Closing bearish + strong sustain + lower high → ● UNBIASED (indecision)
- Closing bearish + strong sustain + NO lower high → ▲ BULLISH (retracement)

**Extreme lows (pos ≤ 15%):**
- Closing bearish → ▼ BEARISH (agree)
- Closing flat → ▼ BEARISH (default)
- Closing bullish + weak sustain → ▼ BEARISH (retracement)
- Closing bullish + strong sustain + higher low → ● UNBIASED (indecision)
- Closing bullish + strong sustain + NO higher low → ▼ BEARISH (retracement)

**Non-extreme (30-70%):**
- Closing strong → closing session decides
- Closing flat + zone lean → zone lean (tiebreaker)
- Closing flat + flow → flow (tiebreaker)
- Sab chup → ● UNBIASED

**Behavioral (70-85% / 15-30%):**
- Closing strong → closing session decides
- Closing flat → zone lean as tiebreaker ("don't short/buy")

---

## Priority Hierarchy (Final)

```
1. Extreme zone override
   ├─ Closing agrees or flat → OVERVIEW WINS
   ├─ Closing opposes + structural failure + strong sustain → UNBIASED
   └─ Closing opposes + no structural failure → OVERVIEW WINS (retracement)

2. Closing session (direction + strong sustain)
   └─ Strong + clear direction → CLOSING SESSION DECIDES

3. Overview lean + Flow agreement
   └─ Double confirmation → OVERVIEW WINS

4. Overview lean alone (non-extreme)
   └─ Weak tiebreaker → OVERVIEW LEAN

5. Flow alone
   └─ Tiebreaker → FLOW DECIDES

6. Sab chup
   └─ UNBIASED
```

**Note:** Sustain = close position in FULL DAY range (top/bottom 30% = strong, middle 40% = weak).
Structure = HH/HL/LL/LH from FULL DAY pivots (9:15-15:30, n=4).

---

## Engine Kya NAHI Karta

Entry nahi batata — sirf bias. Aaj ka data nahi dekhta — sab open se pehle.
Confuse ho to saaf ● UNBIASED bolta hai.

**Next-day bias:** Engine last date ke data se next trading day ka bias bhi compute karta hai — taaki raat ko hi kal ka plan ban sake.

**Indecision ka matlab:** Kal market khulega to fresh data se fresh bias banega. Aaj ka UNBIASED = "kal morning ka pehla swing dekho, uski direction lo." Ye live-bias concept hai, alag se.

---

*Code: `backend/src/overview.py` (Scenes 1–5) · `backend/src/bias.py` (Scenes 6–7 + extreme zone scenarios + next-day bias)*
