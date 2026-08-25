# Intraday Trading System — Market Khulne Ke Baad Kya Karein

> Initial bias (pre-open) toh ready hai. Ab market khula — ab kya?
> Ye doc batata hai **9:15 ke baad har candle pe kya karna hai**, course ke 6 sessions ke basis pe.
> (S1–S6 = course session files reference)
>
> **CANONICAL CASES:** Har scenario (B1–B10, Bc1–Bc9, U1–U5) ki updated
> definitions + implementation tracker: `intraday-trading-explained.md` ke
> **CASE MASTER LIST** section mein. Bias-ke-against trading retired hai —
> counter-swing = RETRACEMENT (Phase 5 updated).

---

## System Ka Hierarchy — Kya Primary Hai, Kya Optional

```
1. INITIAL BIAS (pre-open)     → DIRECTION batata hai (buy / sell / wait)
2. PACE OF MOMENTUM BREAK      → WHERE entry milegi (S/R level)
3. DOMINATION                  → WHEN enter karna hai (confirmation candle)
4. N/M/W PATTERNS              → Optional confirmation (beginners ke liye simplified shorthand)
```

> "N/M shorthand exists... it may sound like beginner stuff, but it's kept deliberately simple." (S5)

**Humare liye:** Initial bias + pace break + domination = PRIMARY. N/M/W sirf optional confirmation hai.

---

## Pehle Samjho: Do Alag Duniya Hain

| | Pre-open (Initial Bias) | Intraday (Live Trading) |
|---|---|---|
| **Data** | Kal ka completed chart | Aaj ki live candles |
| **Kab banta hai** | Market band hone ke baad, raat ko | Market khulne ke baad, 9:15 se |
| **Kya batata hai** | Kal ki direction (▲/▼/●) | Aaj kahan entry milegi, kahan SL hoga |
| **Reference** | `bias-engine-explained.md` | Ye doc |

Initial bias batata hai **kis taraf jaana hai**. Intraday system batata hai **kahan enter karna hai**.

---

## MARKET STRUCTURE — Foundation Concepts

> "Price is God. What we trade is price, so what we analyze is price. Other confirmations exist, but when they go AGAINST what price shows, execution still follows price — because price carries the highest weightage of all." (S1)

### Market never moves in one direction:

> "The market never moves in one direction. This single fact is the foundation of everything. Nobody has ever seen a market go straight up forever." (S1)

### Market makes 2-3 swings before final move:

> "The market doesn't go from point A to B in one move: it typically makes two or three swings before its final high, and multiple swings down before its final low." (S1)

### Supply & demand mechanics:

> "Market rising with higher lows, bought each time at higher prices => demand higher than supply. Price falling to support means supply exceeded demand at those higher prices." (S2)

### Trapped traders fuel the move:

> "Buyers trapped at higher levels panic-exit on reversal, creating fresh selling that fuels the move." (S4)

### Limited possibilities framework:

> "Only two participants exist — buyer and seller — and only two activities exist: buying and selling. No third activity exists anywhere in the market." (S3)

**Matlab:** Market mein sirf 2 cheezein hoti hain — buying aur selling. Isliye patterns limited hain aur identifiable hain.

---

## THE TIMELINE — Har Minute Ka Rule

```
9:15  ─── Market khula
       │   PURE NOISE. 2-4 green ya 2-4 red candles bante hain.
       │   Direction nahi mili. Volatility HIGH hai. SLs hit ho rahe hain.
       │   ❌ KUCH MAT KARO.
       │
9:45  ─── First actionable candle
       │   Ye boundary hai: unsettled → settling.
       │   9:45 candle pehli domination candle ho sakti hai.
       │   ✅ Ab dekhna shuru karo.
       │
9:45-10:00 ─── S/R FORMATION ZONE
       │   Pehla swing complete hota hai (4-10 candles).
       │   ~10 AM tak S/R levels form ho jaate hain.
       │   ✅ MARK karo 10 AM candle. Retracement ka wait karo.
       │
10:00-11:12 ─── BEST EXECUTION WINDOW
       │   Morning-session sweet spot.
       │   Formed S/R pe continuation ya reversal trade.
       │   ✅ Best entries yahan milte hain.
       │
~11:12 ─── CUTOFF
       │   Morning-session trades mat lo after this.
       │   Quality significantly degrade hoti hai.
       │
12:00 ─── ABSOLUTE BOUNDARY
       │   Morning-session ke liye BILKUL kuch nahi.
       │
1-2 PM ─── SECOND SESSION
       │   Price settle hoti hai, volumes return.
       │   Same pace-of-momentum break method.
       │   ⚠️ Volume + momentum hona chahiye. Morning se kam hai.
       │
       │   "Second half trades need volume + momentum present." (S6)
```

### Opening candle pattern:

> "Any day opens with either 2-4 green candles or 2-4 red candles — nothing else exists." (S2)

### Doji/small candle at open:

> "A doji/small candle right after the first candle = swing not yet confirmed." (S3)
> "Two dojis + small candle at 9:45 → no action." (S6)

### Sessions after trending days are easiest:

> "Sessions AFTER trending sessions are EASIEST. Plan: short resistance, expectation = low breakdown." (S6)

### Single-candle poke rule:

> "A single candle poking against the level is NOT a valid retracement — it needs a real, visible multi-candle pullback. Single poke = noise; multiple candles = signal." (S1)

### Rule #1: No trades before 9:45 — HARD RULE

> "No trades before 9:45 — hard rule, non-negotiable." (S1)
> "Executes from the 9:45 candle onward — following this timing rule alone saved multiple legs." (S4)

### Rule #2: Never trade INSIDE the first swing

> "Let it complete (rarely over 4-5-6 candles; max-to-max 5-6; absolute bound 8-10), THEN take continuation OR reversal. Entering mid-first-swing is how people get chopped." (S5)

### Rule #3: First swing never runs continuously

> "Does the first swing ever continue hugely? Class confirmed in chorus: generally NO — 1-2 exceptional days only. Certainty that resistance WILL come is your edge." (S5)

**Matlab:** Pehla swing jo bhi kare (upar ya neeche), uske baad RETRACEMENT aayega. Wo retracement = tumhara entry point.

---

## PHASE 1: MARKET KHULA (9:15-9:45) — OBSERVATION ONLY

### Kya dekhna hai:

1. **Gap check:** Gap up hai ya gap down?
2. **Opening candles:** 2-4 green ya 2-4 red candles bante hain
3. **Initial direction:** Konsi taraf ja raha hai?

### Gap rules:

| Gap type | Kya hota hai | Action |
|---|---|---|
| **Gap-up in buying flow** | Gap IS the continuation. Morning retrace expected. | Support at 9:45-10 pe buy |
| **Gap-down in buying flow** | Gap IS the retracement. "Won't keep falling." | Build support → buy |
| **Gap-up continuation trap** | Single candle drop at higher levels → unlikely to continue | Expect rejection → wait → buy |
| **Gap-down in selling flow** | Continuation expected | Short on resistance |

> "Gap-down ALREADY counts as the retracement. Even if support breaks near 9:45 in a selling pattern, if flow is buying and prior close was at highs, do NOT short." (S6)

### FIRST-CANDLE NEGLECT:

> "First candle fully consumed/reversed by the next → neglect entirely; count the swing from the reversal point." (S4)

**Example:** Pehli candle red thi,agli green ne use puri tarah consume kar liya → pehli candle ko BHOOL jao. Swing us point se count ho.

### Single candle from intraday low/high:

> "A single candle bouncing from intraday low = not a reversal yet. Needs follow-through." (S6)

---

## PHASE 2: FIRST SWING FORMATION (9:45-10:00) — THE SETUP

### Pehla swing identify karo:

1. **Kis direction me bana?** (buying ya selling)
2. **Kitni candles me bana?** (4-10 candles)
3. **Kaunsi type ka swing hai?** (Type A ya Type B)

### Type A vs Type B:

| | Type A (Strong) | Type B (Retracement-type) |
|---|---|---|
| **Pattern** | ONE resistance banata hai aur SUSTAIN karta hai | Highs break karta hai ek ek candle se, phir reverse hota hai |
| **Pace** | High — continuous momentum | Low — retracement ke saath |
| **Entry** | Direct support/confirmation pe | Extra caution, better confirmation chahiye |

> "Identify pace of momentum FIRST. A slowly/weakly built post-10AM swing demands extra caution on entry; an aggressive high-pace swing brings different methods." (S3)

### Two entry types (Type 1 vs Type 2):

> "Type 1 (easy to identify): high made; selling domination forms BELOW the high → lower-high/lower-low pattern; low breaks with domination → act." (S5)
> "Type 2: highs break one-by-one (only 1-2 candles against) while domination stays selling-side — slower pace, needs clean pattern-break-candle confirmation." (S5)

### Two weakness build-ups:

> "Two types of weakness/selling build-up: (a) sell → fall → clean continuation; (b) weakness building BUT each candle's high keeps breaking — up, sold, new high, sold again — domination without LH/LL structure; analyzed via option chart, volume, price strength." (S5)

### S/R formation:

> "Wherever the FIRST break prints is where S/R forms." (S5)
> "Mark the ~10 AM candle, then wait for a retracement. When retracement completes and a fresh support/resistance forms, enter there in the direction of the original swing." (S1)

**Process:**
1. Pehla swing complete hua (~10 AM)
2. Usme S/R level identify karo
3. Retracement ka wait karo
4. S/R pe fresh confirmation ke baad enter karo

### Minimum expectations from swing type:

> "Weak selling swing → small support → general expectation: intraday high breakout (recovery). Weak buying swing → reversal toward the intraday low." (S3)
> "Continuation case → ride accordingly if strong. Reversal pattern → minimum expectation = intraday high / low breakdown." (S3)

### Four second-swing patterns after buying swing:

> "Four patterns: (1) Retraces fully to support = weakness → short. (2) Retraces, makes a HIGHER LOW, continues = strength → buy. (3) Higher low, then LOWER HIGH, then falls = reversal. (4) No retrace at all — sustains high and continues = strong continuation." (S3)

### Fake break-up pattern:

> "Fake break-up: rally → retracement → FAKE break above resistance → sharp retracement downward. Common trap." (S3)

### Exhaustion concept:

> "Even a continuously rising market cannot go up in one straight line forever — profit booking enters, exhaustion enters, and it WILL retrace." (S3)

### 70-80% recovery = execute:

> "Execute at 70-80% recovery — don't wait for full breakout; sell the call right there rather than waiting for the last 20%." (S2)
> "For even higher probability, tighten the trigger to 80% instead of 70%." (S4)

### Confirmation needs follow-through:

> "One big candle alone isn't confirmed: big size at crucial timing but consumed nothing, no next-candle continuation → wait more. Confirmed when: big selling reversing off support + domination candle CLOSES + first-time upward continuation follows." (S5)

---

## PHASE 3: PACE OF MOMENTUM BREAK — PRIMARY ENTRY ENGINE

### Pace break kya hai:

> "Observe the NATURE of the first swing: activity pattern, speed. Wherever the established pattern turns UNUSUAL — speed or structure — that's the pace-of-momentum break: highest-probability S/R location." (S5)

**Ye PRIMARY entry mechanism hai.** Pace break = tumhara S/R level = tumhara entry point.

### Three break types:

| Type | Kya hai | Example |
|---|---|---|
| **1. Candle-wise** | Rhythm toota | 1-green-1-red → 3 consecutive selling candles |
| **2. Domination-wise** | Aggressive candle consumes/reverses | Big red consuming previous green |
| **3. Candle-size** | Unusual size candle | Session average se bahut bada candle |

### Pace break identify kaise karein:

```
Pehla swing observe karo (9:45-10:00)
        ↓
Uska RHYTHM samjho (e.g., 2 greens, 1 red, 2 greens...)
        ↓
Jab rhythm TOOTA — wohi pace break hai
        ↓
Woh level = tumhara S/R = entry point
```

**Example:**
- Pehla swing: 2 green → 1 red → 2 green → 1 red (rhythm)
- Phir: 3 consecutive RED candles (rhythm break!)
- Woh 3rd red candle ka low = pace break level = S/R

### Rhythm reading predicts next candle:

> "Rhythm '2-3 greens, 1 red rejection, greens resume' => next red will likely be absorbed, highs broken again. NO action on lone reds — pattern intact. Break arrives only via: 2-3 sideways candles / lows breaking after a high, OR one big domination red." (S5)

### Confirmation rules:

> "One big candle alone isn't confirmed: big size at crucial timing but consumed nothing, no next-candle continuation → wait more." (S5)

**Confirmed jab:**
1. Domination candle CLOSE hui (wick nahi, body close)
2. Next candle SAME direction me follow-through aaya
3. Big candle + close + follow-through = confirmed break

### Swing voiding:

> "Buying swing VOIDED once lows break 3-4 consecutive candles — whole leg reclassified selling; buy setups ignored till fresh valid break." (S6)

### Two pattern-break types:

> "Two observation points mark a break: (1) number of candles — several push highs, lower high forms, lows start breaking; (2) domination — single aggressive candle consumes the previous one (large body), most significant when FIRST occurrence inside the swing." (S6)

### Entry process (PRIMARY):

```
Initial bias dekho (▲ ya ▼)
        ↓
Pehla swing observe karo (9:45-10:00)
        ↓
Pace break identify karo (rhythm toota)
        ↓
S/R level mark karo
        ↓
Retracement ka wait karo S/R tak
        ↓
Domination candle aayi (confirmation)
        ↓
✅ ENTER KARO
```

### Entry timing: CLOSING TIME, not mid-candle:

> "No entry question before the candle forms. Entry can build at CLOSING time — when the candle has consumed enough and closes near the extreme. Mid-candle entries aren't confirmations; unconfirmed entries get run over when price just extends." (S6)

### Missed the candle?

> "A retracement/lower-level entry still keeps you safe: SL below lows + divergence shows if weakness persists." (S6)

### Never short the absolute low:

> "Bad-probability execution; take the pullback — options give near-support price there." (S6)

### ORDER TYPES: LIMIT used creatively:

> "Use LIMIT creatively, almost like market orders — buy-limit placed ABOVE price acts as buy-stop (crosses level -> buys); bargain limit below fills only lower down." (S5)
> Orders used: LIMIT, SL, SL-M.

### Which entry method — Pattern Break or Domination?

> "Both ARE confirmations; domination-entry candles ARE the pattern-break candles. Rule: whichever confirmation comes first, use it." (S6)

### Candle-close rule: NO rule:

> "No rule — everything is CONFIRMATION-based; confirmation first, wherever the candle is mid-forming; do not wait for the close." (S6)

---

## PHASE 4: DOMINATION — CONFIRMATION ENGINE

### Domination kya hai:

Market continuously reveal karta hai kaun side dominate kar raha hai:
- **Buyer domination:** Buyers price ko upar push kar rahe hain, sellers sustain nahi kar pa rahe
- **Seller domination:** Sellers price ko neeche push kar rahe hain, buyers sustain nahi kar pa rahe

### Domination ke rules:

1. **Reversal = strength confirmation:** Sellers pushed, couldn't sustain, buyers pushed back → strength confirmed
2. **Double domination = high probability:** Koi side dominate ho → opposed → phir dominate → opposing side ki probability bahut high
3. **Max 2-3 bluffs:** Reversal bluffs at most 2-3 baar hoti hain
4. **Domination cannot continue indefinitely:** Market nature hai — sustain nahi hota
5. **Never switch sides in confusion:** Confused bias → DO NOT flip buy/sell/buy

> "Any side's domination confirmatorily opposed TWICE → the opposing side's probability becomes very high. A market rarely fully reverses 70% and keeps flip-flopping beyond that." (S4)

### Against-flow menu details:

> "Flow-favorable (ATH + strong buying): ONE candle of support suffices for buys. Against flow: EITHER a lower high forms -> execute, OR double-domination: buyer dominates -> seller dominates -> buyer -> seller again; execute ON THE SECOND SELLER DOMINATION." (S6)

### Momentum-miss principle:

> "Against flow without clean candle-wise confirmation, deliberately LET momentum miss; wait proper confirmation; guard against price flipping back above highs — letting lows break first yields the higher-probability execution." (S6)

### Domination identify kaise karein:

| Signal | Kya dikhta hai |
|---|---|
| **Big candle consuming previous** | Single aggressive candle = domination |
| **Wick reversal** | Buyers/sellers ne price ko wapas push kiya |
| **Follow-through** | Domination candle ke baad next candle bhi same direction me |
| **Rhythm break** | 2-3 greens, 1 red pattern toota → domination shift |

> "Single aggressive candle consumes the previous one (large body), most significant when FIRST occurrence inside the swing." (S6)

### Wick rules:

> "The wick issue exists (wicks = pressure). But the trade runs on CONFIRMATION — complete confirmation -> execute regardless of the wick; alignment in favor governs." (S6)

### Wick-wait rule:

> "Wick ban rahi hai → wait for candle close. Wick = pressure. Confirmation close ke baad aata hai." (S6)

### Volume doubles on domination:

> "Falling market + significant/double volume increase in the option = confident-move confirmation (proper domination shows double volume)." (S5)

### All named patterns reduce to domination:

> "All named patterns reduce to DOMINATION: cup & handle = deep fall (selling) then FULL reversal (cup); handle = selling-domination arrives and buyers dominate it AGAIN at higher levels. Flags likewise. Ultimately everything is reversal-from-low-to-high or high-to-low via domination." (S5)

### Domination + Pace Break = Entry Trigger

```
Pace break mila (S/R level identified)
        ↓
Ab domination ka wait karo us level pe
        ↓
Domination candle aayi (big candle consuming + closing)
        ↓
Next candle follow-through de rahi hai
        ↓
✅ ENTRY CONFIRMED
```

---

## PHASE 5: DO ENTRY MODES — WITH FLOW vs RETRACEMENT

> **NOTE (updated):** Purana "AGAINST FLOW short/buy against bias" approach
> RETIRED hai. Final decision ("bias overrides pattern", S6): bias ke against
> trade NAHI hota — opposite swing sirf RETRACEMENT hai, aur us retracement ne
> jo S/R banaya WAHI trade hota hai. Case-wise details:
> `intraday-trading-explained.md` canonical hai.

### Mode 1: WITH THE FLOW (direct execution)

**Kab:** Jab first swing / pace break INITIAL BIAS ke direction me hai.

> "Buying trend, market retraces: no N/M check needed. Support identifies via pace-of-momentum break → execute directly." (S5)

**Process:**
1. Initial bias bullish hai (▲)
2. Selling swing bana (retracement) ya direct buying chali
3. Pace break + domination ne support confirm kiya
4. ✅ Direct buy — aggressive break candle pe entry allowed (close-quality check ke saath)

### Mode 2: RETRACEMENT AT THE LEVEL (counter-break ka S/R)

**Kab:** Bias bullish hai par counter-swing (selling) ne apna structure break kiya — ye SHORT signal nahi, ye RETRACEMENT LEG hai jiska level support banega.

**Process:**
1. Initial bias bullish hai (▲), buying swing ne break-down diya (counter-break)
2. Break ka level = candidate support zone mark karo
3. Selling leg ko aage chalne do ("maybe after breaking lows first" — S5)
4. Leg ke extreme pe wait karo: **bias-colored DOMINATION** candle (consume ≥60% body ya big-candle, close upper-half mein) + follow-through ≤2 candles
5. ✅ SUPPORT PE BUY — SL leg-low ke neeche average-size

> "Bias overrides pattern." (S6) — Isliye kabhi bhi bias ke against short/buy nahi.
> Mirror bearish bias ke liye: up-counter-break → resistance → red domination → short.

### Flow exception — Major low test:

> "Overview selling + market testing a MAJOR LOW = test AGAINST the selling direction = in your favor → direct call allowed WITHOUT extra confirmation." (S5)

---

## PHASE 6: WHEN TO NEGLECT / SKIP

### Skip rules:

| Scenario | Rule |
|---|---|
| **Before 9:45** | ❌ NO EXECUTION. Hard rule. |
| **Inside first swing** | ❌ Let it complete first |
| **No reversal/domination** | ❌ "No reversal/domination failure = don't trade the case" (S4) |
| **Confused** | ❌ "Never switch sides in confusion" (S4) |
| **Gap-down already retracement** | ❌ Don't auto-short if flow is buying (S6) |
| **First candle consumed** | ❌ Neglect it, count from reversal point |
| **No confidence** | ❌ "No confidence → no execution" (S6) |

### Indecision market / confusion protocol:

> "ATH made -> sell-off -> support -> LOWER HIGH -> selling arrived and the day CLOSED on selling-side support = indecision market, movement possible both ways, NO bias held. When confused there's ONE path — wait for tomorrow and observe." (S6)

### Bias overrides pattern:

> "Opened into higher levels; buying overview. It dropped toward lows — valid lows-break confirmation — but the SELL was deliberately SKIPPED: bias had flipped to buying-swing regime. Bias overrides pattern." (S6)

**Matlab:** Agar initial bias bullish hai aur bearish signal aata hai — SKIP karo. Bias jeetta hai.

> "Morning view and major overview conflict → prioritize the morning view; execute it first." (S4)

**Par:** Agar morning view (first swing) overview ke against hai — morning view pehle execute karo, overview baad me.

### Standard rule for bias-less days:

> "Previous day gave no clarity -> NEXT DAY take direction of the FIRST swing that forms." (S6)

---

## PHASE 7: RISK MANAGEMENT — SL, TARGET, EXIT

### Stop-loss:

> "SL should be average candle size — that makes the 1:3 target a general realistic expectation." (S6)

**Calculation:**
1. Last 10-15 candles ka average range nikalo (high - low)
2. SL wahan rakho (entry ke paas)
3. Agar low bahut door hai (12-15 pts SL) → SL thoda upar rakho, slightly bigger than average

### Average candle size measurement:

> "Measure average range (sum of highs-lows / candles) or estimate slightly above general candle size. SL sits near the low, so minimum expected move approximately one average candle." (S5)

### Never park SL at extreme:

> "Never park the SL exactly at the extreme: slightly beyond/inside (bit ABOVE intraday lows for longs). If price travels that extra bit, the idea is already dead." (S4)

### Oversized-SL exception:

> "Low too far away (12-13-15 point SL)? Target turns unrealistic. Place the SL slightly above the low, slightly bigger than average size instead." (S6)

### Target:

> "1:3 target a general realistic expectation. Indian markets make it realistic automatically." (S6)

### Acceptable R:R range:

> "If 1:3 or 1:4 isn't available, exit at 1:2 or even 1:1.5 — peace of mind over max R:R. Green panels matter more than squeezing the last points." (S2)

### High success rate preference:

> "Prefer methods with HIGH SUCCESS RATE — seeing green panels repeatedly builds the confidence trading requires, even at lower R:R." (S2)

### 5-point immediate momentum rule:

> "After entry, roughly 5 points of favorable momentum should arrive almost immediately in maximum cases. That instant push protects the small SL. No quick push = entry needs improvement." (S5)

### Self-testing funnel:

> "Test yourself post-session: take 10 entries; if MOST hit SL with no post-entry momentum, entries are wrong. Correct behavior: 5-6 instant points (140->150/155 same candle) = greater than 1:1 pulled within the FIRST candle. By the 1:2 zone, SL sitting 12 points away leaves a 24-point funnel to play with — safety compounds." (S6)

### NO TRAILING rule:

> "Never trail SLs to entry. Either fixed ratios (exit when ratio arrives) or hold. Trailing has negative points; he personally never trails." (S4)

### Exit rules:

| Situation | Action |
|---|---|
| **Target hit** | ✅ Book profit |
| **SL hit** | ❌ Exit, accept loss |
| **>1:2 traveled, reversal** | Cost-to-cost exit |
| **3 attempts against you** | Exit (three-attempts rule) |
| **No momentum after entry** | Exit early |
| **1:2 or 1:1.5 if 1:3 unavailable** | Exit early — peace over max R:R |

### Cost-to-cost exit:

> "Approached a realistic 1:3 — beyond roughly 1:2.2 up to ~1:2.5, missing 1:3 by merely 5-7 points — then reverses sharply back toward cost → MAY exit at break-even/cost-to-cost." (S6)

**Rule:** Target tak pahuncha par 1:3 nahi mila → phir reverse ho raha hai → cost pe exit karo.

### Cost-to-cost exit unlocks second trade:

> "Cost-to-cost exit unlocks a second trade with fresh direction planning." (S5)

### Against-overview trades: exit early:

> "Against-overview trades: exit early — the overview says counter-moves aren't continuous; exit on first decent adverse bounce/momentum." (S4)

### After entry: NO analysis:

> "ALL analysis happens BEFORE entry. After entry: NO analysis — changing-overview feelings, bounces off resistance, breaking news — none may disturb you. Once entered, end analysis right there." (S6)

### After-entry permitted intervention:

> "Single permitted intervention: approached a REALISTIC 1:3 — beyond roughly 1:2.2 up to ~1:2.5, missing 1:3 by merely 5-7 points — then reverses sharply back toward cost -> MAY exit at break-even/cost-to-cost rather than ride to full SL." (S6)

### Three-attempts exit rule:

> "Market proceeded AGAINST the same level THREE times. Each buyer attempt knocked down by sellers is itself buyer-weakness; odds of an against-flow move keep rising → third reversal forming = exit cost-to-cost." (S6)

### First leg exit at 1:1.5-1:2:

> "Playing two legs? First leg exits at 1:1.5-1:2 — sufficient." (S4)

### Three-day SL streaks digestible:

> "3-day SL streaks are digestible in high-R:R systems: one winning day covers three losing days." (S4)

### Daily overview corollary:

> "Once a level is built, the market does NOT come back to retest it in maximum cases — that's why well-placed stops survive." (S4)

---

## PHASE 8: TWO-ENTRY SYSTEM

### Leg 1 vs Leg 2:

| | Leg 1 | Leg 2 |
|---|---|---|
| **Source** | Morning-session/swing-based | Overview-based |
| **Timing** | 9:45-11:12 | After Leg 1 exits |
| **SL** | Small (pace break pe) | Same line as Leg 1 |
| **Rule** | First trade | Sirf jab Leg 1 exit ho jaaye |

### Important rules:

1. **Never run two same-direction positions simultaneously**
2. **Re-enter only after proper exit (including stop-out)**
3. **Both legs share the same SL marking/line**
4. **Beginners: MAX two entries per day**

### Second position fires BEFORE first is cut:

> "The opposite-side second position fires on the overview trigger BEFORE the losing first is formally cut (overview says: if rejection comes, short it). Execute second -> then cut the clearly-losing first." (S2)

### Direction matching = single position, never doubled:

> "Overview AND morning both say buy -> ONE position only. They clash (buy vs sell) -> plan BOTH sides; the double-position approach applies only under conflict." (S2)

### Three sub-rules for second entry:

> "Three sub-rules: (1) First entry hits target with sufficient momentum -> close the day. (2) First stops out + second setup forms per overview -> execute the second entry. (3) No lower high formed -> invalidation: if price keeps breaking previous highs instead, the selling-side overview is dead that day -- skip." (S4)

### Two-layer system (confirmatory → identification):

> "Layer 1 (confirmatory): if a buying swing reverses, there's a 70-80% chance price reaches the support area. Layer 2 (identification): judge weakness/strength just by WATCHING the swing itself — prepare early for whether reversal or continuation is more likely. Execution still happens ONLY on confirmation." (S4)

### Two decisions per session:

> "Every session offers exactly two decisions: (1) Retracement trade — enter on the retracement in the swing's direction (morning-session entry). (2) Support-based trade — after support forms, plan the buying side (overview-based entry). Both can execute in the same session." (S2)

### Conservative step-down option:

> "Emotions/confusion high or SLs hitting repeatedly -> step DOWN one level: trade only W/M/V-shape reversals. Fewer executions, each very high win-probability." (S4)

---

## PHASE 9: OPTION BUYING vs SELLING

### Option selling (preferred for this system):

> "Option selling is the preferred, easier route — more confirmation time, comfortable holding." (S2)

**Kyun:**
- Selling pe confirmation ka time milta hai
- Theta decay tumhare favor me kaam karta hai
- Bigger SL fit hota hai, positions hold hoti hain

### Selling duration-match advantage:

> "Bigger SL = longer hold = more theta captured, PLUS the direction edge from confirmations — double advantage for sellers." (S4)

### Selling success rate vs R:R:

> "Selling only at confirmed support/resistance = approximately 80% success rate; selling at any random candle drops to 50-60%. Tradeoff: the high success rate needs wider stops -> more risk per trade." (S1)

### Option buying:

> "Small capital → option BUYING. But adds risk — needs quick momentum capture." (S2)

### Option buying capital limitation:

> "Large capital can't deploy efficiently — e.g., 60,000 quantity at a 200-300 premium can't fill in a small range without price jumps -> worse fills -> lower overall probability. Small capital earns great percentage returns." (S4)

### Strike selection — Three pillars:

> "Three pillars: volume, price behavior, weekly-vs-monthly." (S6)

### Weekly first, monthly fallback:

> "Preference order: WEEKLY first, always. Weekly: check 100 pts ITM, then 200 pts ITM. Monthly fallback: 100 pts ITM or ATM." (S6)

### Strike selection via volume break:

> "Scan ATM + ITM (~1-2-3 strikes): usually ONE shows the volume break/divergence, others don't. The strike with the volume break is strongest; prefer it." (S5)

### Which chart for volume:

> "Watch OPTIONS for volume when executing options (not futures). Stock traders watch futures volume as the norm. In Nifty he watches the OPTION STRIKE's own volume." (S5)

### Current expiry for momentum:

> "If momentum is expected, CURRENT expiry delivers more movement — that can be taken too." (S6)

### Hero-zero / expiry trading:

> "On expiry take a slightly OTM strike when N/M forms and buy it. Patterns work on expiry day and every session." (S4)

---

## VOLUME & OPTION STRIKE — Detailed Guide

### Session volume signature:

> "Session volume pattern: open spike (first 1-2 candles carry volume — market nature) -> mid-session reduction -> the BREAK of that reduction marks where domination occurs (maximum cases) -> close spike." (S5)

**Matlab:** Volume ka pattern fixed hai — open pe spike, mid me low, break pe domination, close pe spike.

### Divergence reading (spot vs option):

> "Spot breaks highs, option doesn't follow; or option sags to lows / sustains lows early while spot holds — extra weakness/strength info. Often appears BEFORE spot reverses -> execute even more confidently." (S5)

> "Reverse case: spot breaks lows but option stops breaking, buying starts early = buying-side confirmation." (S5)

### Option chain (OI/AOC/POC) not needed daily:

> "Not daily — everything reflects in PRICE, and price carries highest weightage." (S4)

### Morning volume decides domination/day bias:

> "Morning volume decides domination/day bias; Indian market's two-session structure." (S4)

---

## PSYCHOLOGY & DISCIPLINE — The Real Edge

### Rule #1: No confidence → No execution:

> "No hasty entries. Nervousness or missing confirmations -> don't take that entry, or don't trade the session at all. First rule: no confidence -> no execution. No confidence + heavy quantity -> emotion -> fear -> collapse. Whoever feared is dead." (S6)

### Environment rule:

> "Environment must be RIGHT: family/travel-with-company/disturbance -> no. Traveling alone, separate room, things closed, KNOWING nobody disturbs for 3-4 hours." (S6)

### Equipment rules:

> "One script -> one laptop/PC suffices. Mobile NOT for execution (price-checking fine). No fancy multi-screen rigs unless genuinely running multiple books simultaneously." (S6)

### Emotion mid-trade = exit signal:

> "Feeling fear/emotion mid-trade is itself a signal -- exit; whether target or SL was coming doesn't matter; the mental state isn't right for execution." (S2)

### Think in batches of TEN trades:

> "Don't think ONE trade — think 10 trades: same execution repeated gives some 1:3s and 2-4 SLs, so nothing today carries lasting impact." (S6)
> "Think in batches of TEN trades, not one — clarity comes." (S5)

### Biggest loss story (environment lesson):

> "~15 LAKH wiped out in option buying — single day. Traveling, gadgets banned in temple, couldn't quit mid-trade. Lesson: never take the market lightly; execute only while AT the system; never leave a system mid-trade. Discipline per rules." (S6)

### After execution: quit:

> "The moment execution stops, he QUITS the markets entirely — done between 10:30/11/12 varying; review only in the evening post-close. Outsiders would think he does nothing." (S6)

### Mindset-building path: 1-3 months:

> "Begin with this system even from a negative mindset; continue without haste 1-3 months; confidence builds automatically, then advance." (S4)

### Confidence threshold before advancing:

> "Confidence is essential — once it arrives (consistent losses stop appearing, things start changing), THEN switch methods. Don't rush to complicated systems before basics are solid." (S2)

### Soft-hearted traders: avoid small SLs:

> "Soft-hearted/emotionally sensitive traders should avoid very small SLs — use the safe-side setups instead." (S4)

### Missing entries disturb psychology:

> "Missing entries disturb psychology: N/M entries don't need split-second decisions, but his current system does; strong mindset comes from practice — otherwise 2-3 good sessions precede sudden loss streaks." (S4)

### Meta-rule: follow your plan:

> "Once in the trade, FOLLOW YOUR PLAN — decided 'no action before 1:2 / exit after 1:3'? Do exactly that even if price overshoots then reverses." (S5)

### One script discipline:

> "Every script behaves slightly differently — hopping between scripts/expiries weekly dilutes feel. Pick ONE script, practice it, build the steady hand — like a racing driver practicing his own car." (S3)

### Backtest worst-case scenarios:

> "Always backtest worst-case scenarios, not best-case." (S4)

### Repetition ≠ familiarity:

> "Consistency cannot come from one isolated concept. Everything learned so far — base concept, swings, overview, domination — activates together inside each execution. Examples may look familiar from videos, but without the full concept chain they can't be replicated consistently." (S5)

---

## POSITION SIZING & MONEY MANAGEMENT

### Big SL + Small Quantity (NOT small SL):

> "Use a LARGER stop with SMALLER quantity — don't place tiny stops. Bigger SL + small quantity keeps pressure manageable." (S2)

### Consistent rupee-loss per trade:

> "SL AMOUNT should be similar across trades; points differ per condition — QUANTITY is your control variable to normalize money at risk." (S4)

**Matlab:** Har trade mein same ₹ risk karo. SL points badal sakte hain, quantity adjust karo.

### Range too big → reduce quantity:

> "Range too big -> reduce quantity, and book earlier since momentum arrives relatively smaller." (S4)

### Capital increment rule (+30% max):

> "Never 1L -> 2L -> 4L quickly. Max +30% per step; only after >= 10 trades AND >= 1 month of successful results; fund increments preferably from profits. Focus = CONSISTENCY, not doubling. Failure mode: earn 2-3 months, scale, lose everything." (S6)

### ROI expectations: process-first:

> "Follow process; size to digestion capacity; add capital slowly — ROI builds itself. Sustained 30-40%/monthly claims ignore scaling limits; large capital forces method change — smaller relative risk, wider SL, smaller targets — ROI falls automatically." (S6)

### Emotion control: quantity beyond digestion breeds emotion:

> "Knowledge + execution + digestible quantity = no emotion. Quantity beyond digestion breeds emotion — shrink, scale gradually; discipline + confidence fix the rest." (S6)

### Realistic monthly returns: 20-30%:

> "Realistic returns: monthly expectations of 50-80% are unrealistic here; think 20-30%." (S4)

### 8-of-11 positive session stat:

> "In his marked backtest 8 of 11 sessions closed positive (within the sample: 1 day x 2 SLs, 2 days x 1 SL each). Consistency builds psychology." (S4)

### Probability target: 60-70%:

> "From first-swing observation alone, correct-call probability should be approximately 60-70%. Not 100% — 1-2 sessions will be wrong because the market stays exceptional and unpredictable. Acceptable." (S3)

---

## PRACTICAL CHECKLIST — Har Din Ka Process

### Pre-market (raat ko):
- [ ] Initial bias nikalo (▲/▼/●)
- [ ] Overview zone check karo (extreme/high/mid/low)
- [ ] Closing session read dekho
- [ ] Multi-day flow dekho

### Market open (9:15):
- [ ] Gap check karo (up/down/flat)
- [ ] Opening candles observe karo
- [ ] ❌ KUCH MAT KARO before 9:45

### First swing (9:45-10:00):
- [ ] Pehla swing identify karo (direction, type A/B)
- [ ] S/R level mark karo
- [ ] Pace break identify karo (rhythm toota)
- [ ] Domination read karo (kaun jeet raha hai)

### Execution window (10:00-11:12):
- [ ] Retracement ka wait karo S/R tak
- [ ] Domination candle ka wait karo (confirmation)
- [ ] **WITH flow:** Direct execution on pace break + domination
- [ ] **Counter-swing aaya?** RETRACEMENT mode — uska S/R pe bias-direction entry
- [ ] SL = average candle size (structure low/high ke paas, absolute extreme pe NAHI)
- [ ] Target = 1:3

### Post-entry:
- [ ] 5-point immediate momentum aaya? → Entry sahi hai
- [ ] Nahi aaya? → Entry improve karo
- [ ] >1:2 traveled? → Cost-to-cost exit ready rakho
- [ ] 3 attempts against? → Exit cost-to-cost

---

## SCENARIO EXAMPLES

### Scenario 1: Buying market, gap-up, morning retrace

```
Context: Initial bias = ▲ BULLISH (extreme highs)
Market: Gap up open
9:15-9:45: Red candles aaye (noise)
9:45: First green candle → buying swing bana
10:00: S/R formed at support level (pace break identified)
10:00-10:30: Retracement aaya support tak
10:30: Domination candle (green consuming red + close + follow-through)
Entry: BUY at support
SL: Below the low
Target: 1:3
```

### Scenario 2: Selling market, gap-down, morning bounce

```
Context: Initial bias = ▼ BEARISH (extreme lows)
Market: Gap down open
9:15-9:45: Green candles aaye (noise)
9:45: First red candle → selling swing bana
10:00: S/R formed at resistance level (pace break identified)
10:00-10:30: Bounce aaya resistance tak
10:30: Domination candle (red consuming green + close + follow-through)
Entry: SHORT at resistance
SL: Above the high
Target: 1:3
```

### Scenario 3: Against flow — buying market, selling signal

```
Context: Initial bias = ▲ BULLISH (extreme highs)
Market: Opens, selling starts
9:45-10:00: Selling swing bana
10:00: Resistance formed
10:00-10:30: Pehli rejection (buyers push par fail)
10:30-11:00: Doosri rejection (phir push par phir fail)
11:00: Teesri rejection → ✅ ENTRY (the train has started)
SL: Above the high
Target: 1:3
⚠️ Note: Against flow hai — extra confirmation chahiye
```

### Scenario 4: Indecision — skip

```
Context: Initial bias = ● UNBIASED
Market: Opens flat
9:45-10:00: No clear swing
10:00-11:12: Choppy, no domination
Action: ❌ SKIP. No clear direction.
Rule: "No reversal/domination failure = don't trade the case"
```

### Scenario 5: Sessions after trending day

```
Context: Kal trending day tha (big move)
Market: Opens flat/small gap
Expectation: EASIEST session type
Plan: Short resistance, expectation = low breakdown
Rule: "Sessions AFTER trending sessions are EASIEST." (S6)
```

---

## COMMON MISTAKES

| Mistake | Rule |
|---|---|
| 9:45 se pehle trade lena | ❌ Hard rule — wait for 9:45 |
| First swing ke andar enter karna | ❌ Let it complete (4-10 candles) |
| W/M sirf higher-low dekh ke trade karna | ❌ Observe DOMINATION reversal, not just price level |
| Confusion me side switch karna | ❌ "Never switch sides in confusion" (S4) |
| Confirmation ke bina entry lena | ❌ "No confidence → no execution" (S6) |
| Bias ke against trade lena | ❌ "Bias overrides pattern" (S6) |
| Average candle size se bada SL rakhna | ❌ Keep SL small, target realistic |
| 1:3 na milne pe hold karna | ❌ Cost-to-cost exit if >1:2 traveled |
| SL trail karna entry tak | ❌ "Never trail SLs to entry" (S4) |
| Entry ke baad analysis karna | ❌ "After entry: NO analysis" (S6) |
| SL extreme pe park karna | ❌ "Never park SL exactly at extreme" (S4) |
| Quantity digestion se zyada rakhna | ❌ "Quantity beyond digestion breeds emotion" (S6) |
| 1L se seedha 4L kar dena | ❌ Max +30% per step, after 10 trades + 1 month |
| Mobile pe execution karna | ❌ "Mobile NOT for execution" (S6) |
| Ek trade ko soch ke pressure lena | ❌ "Think in batches of TEN" (S6) |
| Choppy days pe trade karna | ❌ "For now, don't study choppy days" (S3) |
| Shorting absolute low | ❌ "Bad-probability execution" (S6) |
| Mid-candle entry without close | ❌ "Entry at CLOSING time" (S6) |

---

## QUICK REFERENCE

```
9:15 ─── OBSERVE (no trade)
9:45 ─── FIRST SWING (identify, don't enter)
10:00 ─── S/R FORMED via PACE BREAK (mark levels)
10:00-11:12 ─── EXECUTE (with flow: pace break + domination / against flow: 2+1 rejections)
11:12 ─── CUT OFF (no morning trades)
12:00 ─── ABSOLUTE (nothing)
1-2 PM ─── SECOND SESSION (needs volume + momentum — same method as morning)
```

**Entry:** Pace break + domination + confirmation (at candle CLOSING time)
**SL:** Average candle size (never at extreme)
**Target:** 1:3 (or 1:2 / 1:1.5 if 1:3 unavailable)
**Max entries:** 2 per day
**Trailing:** NEVER
**After entry:** NO analysis
**Golden rule:** No confidence → No execution
**Think in batches:** 10 trades, not 1

---

*Code: Intraday logic to be implemented in `backend/src/` (TBD)*
*Reference: `docs/bias-engine-explained.md` for pre-open bias*