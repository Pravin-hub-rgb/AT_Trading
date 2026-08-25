# BASE CONDITIONS — engine ke foundations (ek-ek karke fix karte hain)

Workflow per item: theory check → measure → fix → before/after stats → status ✅

1- Identifying first swing                      [✅ FIXED — time-based v1 live]
   abhi    : window 9:15 → 9:45; extreme-timing direction
             (LOW pehle + HIGH baad = BUYING · HIGH pehle + LOW baad = SELLING)
   advance : STRUCTURE-based — time nahi, structure dekho:
             low bana → uske UPAR 2 candle sustain = first swing BUYING confirm
             high bana → uske NEECHE 2 candle sustain = SELLING confirm
             (halt jahan hoti hai wahi completion point)
   status  : abhi wala live · advance backlog (M1 swing-health se judta hai)

2- Gap classification                           [✅ FIXED]
   abhi    : |open − prev_close| ≥ 0.27% → gap-up/down, warna flat
   proof   : labeled examples (Oct-Dec'25, Mar-Apr'26) pe 8/9 separation
   note    : prev_close/open 5-MIN data se (daily CSV corrupt — item 11)

3- Average candle size                          [✅ FIXED — 10-day stable baseline]
   abhi    : pichhle ≤10 SESSIONS ke 5-min candles ka mean range
             − har session ki pehli candle − ≥15:15 candles
   fallback: zero history → 21.5 pts (dataset-wide qualifying mean, researched)
   impact  : STABLE poore din · big-candle FAIR (aaj ka spike khud ko inflate
             nahi kar sakta) · gap-day SL ~15% tighter
   result  : backtest −6.06R → +9.14R (pehla positive total!)
   advance : median variant A/B (alag experiment)

4- Domination definition                        [⚠️ guessed numbers]
   abhi    : body consume ≥60% of prior body · big-candle ≥1.5× avg · close-q ≥50%
   todo    : notes/examples se real values research + wick-domination variant (M3)

5- Micro pivots (structure-break levels)        [⚠️ arbitrary]
   abhi    : n=2 Williams fractal intraday
   todo    : n sweep test

6- Swing voiding                                [⚠️ partial]
   abhi    : 4 consecutive lower-lows/higher-highs → leg reclassified
   todo    : course "3–4" bola — 3 vs 4 A/B test

7- Level tolerances & timeouts                  [⚠️ invented]
   abhi    : near-tol 0.25×avg · invalid 1.0×avg · armed-timeout 12 · retro 24 · leg-min 3
   todo    : sweep A/B batch

8- Follow-through                               [✅ course-backed]
   abhi    : domination ke ≤2 candles mein same-direction close + extreme hold + progress

9- Risk layer                                   [✅ experimented]
   abhi    : SL = ref-extreme − mult×avg · target 3R · c2c >2R→BE unlock · max 2/day · EOD 15:15

10- Timing windows                              [✅ backed]
   abhi    : entries 9:45–11:12 · square-off 15:15 · first-swing settle 09:45

11- DATA foundation: Daily CSV close                [✅ FIXED at consumption point]
   issue   : daily-API close = official index methodology; 244/261 rows 5-min
             last-tick se mismatch (max ±85 pts) — sirf CLOSE, O/H/L perfect
   fix     : bias.compute_bias ab daily copy ka `close` 5-MIN truth se rewrite
             karta hai (O/H/L untouched, file on disk untouched)
   impact  : overview pos_pct/zones ab chart-consistent · 11 zone flips ·
             6 dino ka lean/bias corrected · backtest: +9.14R(noise-luck) →
             +5.14R (true baseline)
   note    : gap detection pehle se 5-min use karta hai ✓

12- Prev-Day Close Read layer                      [⚠️ NEW — documented input (overview doc §4)]
   abhi    : IGNORED completely (sirf overview prev_close use hota tha)
   define  : prev_close_read ∈ {STRONG, WEAK, MIXED} — §4 rules se:
             STRONG : close at highs / buying held 2nd-half / strong-swing override
             WEAK   : selling held 2nd-half / close at lows
             MIXED  : confused / dono signals mixed
   effect  : container-modifiers ka GATE (discussion phase):
             STRONG → aggressive entries LEGIT (S6:123 "prior close at highs"
                      wala template isi condition pe pass hota hai)
             WEAK   → aggressive DOWN-GRADE → full confirmation path
                      (S1: negative close → lower-level test warning,
                       continuation risk pe knife-catch nahi)
             MIXED  → default behavior
   advance : FLOW-AGE exhaustion (#13 backlog) — 3-6 day selling flow dying
             at lows = "easiest sessions" (law #11); flow_map data already hai
   status  : 🔒 POLARITY LOCKED — COURSE-FIRST
             (clash resolve hua tha: user ka "kal selling = exhaust = strong
              buy" vs course ka "PRIOR CLOSE AT HIGHS = dip-protected" —
              course jeeta. Multi-day exhaustion angle → item #13)
   implement: entry-matrix build ke saath (C3/C4/C5/C11/C13 gates)

13- Flow-Age Exhaustion                            [❌ BACKLOG]
   idea    : 3-6 day one-directional flow ki AGE exhaustion signal deti hai
             (law #11: "selling flows die into sideways closes at lows")
   source  : flow_map already pivots/flow track karta hai
   note    : item 12 ke baad hi, overload na ho
