big pickle:
Read P93/P94/P95, the round index, and went to the code for the two numbers your question rests on. I found two things that change the question. Both are verified in source.
⚠️ FIRST: bars_to_wend has a 16× unit bug
exp_inside80.py:166:
bwe = (we - e) / 900.0      # 900s = 15 min → the value is in 15m BARS
1 day = 96 bars, not 6. The doc divided by 6.
 	P95 says	actually	in hours
OUT cohort	"about 76 days"	458.8 bars	4.78 days (76.4h)
IN cohort	"about 13 days"	76.6 bars	0.80 days (19.2h)
Both are 16× too large. And 76.4 hours is exactly the mean window duration method/BIAS_WINDOW_THEORY.md reports (76h) — so the OUT cohort simply enters near the start of a mean-length window, and the IN cohort enters 19 hours before it closes. The mechanism survives; the scale does not.
This is the same bug species as P57's "4-day bucket built 4-hour," and it's why a table can look like a result.
⚠️ SECOND: "30+ days" is impossible by construction
v18_streak_halt.py:222-224 — three literals, no kwarg:
simulate_btc_trades_v7(..., rr_target=htf_rr, cap_days=16)
wend = t["exit_ts"] (line 242), so the window can never exceed 16 days. Median window 1.17d. Mean OUT countdown 4.78d.
No entry-time feature can promise a trade 30 days. The thing that authorises the trade is hard-capped at 16. Asking for a feature that finds long-countdown trades is asking for something the machinery cannot supply — the ceiling is cap_days, not your filter.
Q1 — can you build an arm on bars_to_wend?
Your two objections are both correct, and there is a third one you didn't make.
your point	verdict
keeping 20% can't make 193.4R from a +70.1R book	✅ right. P94: dNet ceiling is +180.5R IS / +118.6R OOS = 0.93× / 0.61× M
OOS had only 34 trades	✅ right, and it's a harder kill than you think
The third kill, and it is the real one. P63 measured the forward null's band at 40–70 trades. The outlive OOS book is 34–43 trades. So the cohort is not merely below M on net — it sits below the sample size at which this programme's own significance machinery can function at all. No threshold, no bars_to_wend cut, no clever AUC of 0.85 fixes an n=34 book. P94's "the constraint is trade count, not edge quality" is right, and it is worse than P94 says.
So: as a filter, dead. And that is the correct answer, not a dodge.
But your framing contains the actual lever. You asked for a feature that selects long-countdown trades. The real constraint is that the countdown is manufactured — it is htf_rr=3.0 and cap_days=16, and P95 just told you the long-countdown trades are the +4.9R ones. So the trade isn't "which trades have room," it's "why does the window close at all while the ratchet is still loose." That's htf_rr and cap_days, not bars_to_wend. See P97.
One honest caveat you should have: P95's own doc says bars_to_wend is "mechanically related to the label." Stronger than that — it is nearly the same variable. A trade outlives its window iff bars_to_wend_at_entry > bars_held. AUC 0.85 here is mostly arithmetic, and P95 reports no threshold because it is right not to. Do not let anyone build a threshold on 0.85.
Q2 — can an exit rule save the weak 80% by freeing a slot?
NO. And I can prove it from source in four lines.
v18_streak_halt.py:
567:  busy_until=""  # datetime string - timestamp-based, not index   ← the comment
577:  if busy_until and bar_time <= busy_until: continue
743:  busy_until=candles_ltf[exit_idx]["date"]                        ← a DATE
"2021-05-03 14:00:00" <= "2021-05-03"   ->   False
The concurrency guard is broken. A date string is compared against a datetime string, so it never blocks same-day re-entry. method/RISK_CONCURRENCY.md measured the result: max concurrent 6/5/6/3, against a design that intends one position. Its verdict: "Recorded, not fixed… Worth a separate experiment on its own merits."
So the answer to Q2 is not "the prior is against it":
The slot Q2 wants to free is not a binding constraint. And it doesn't look non-binding because you have capacity — it looks non-binding because the guard has a bug in it.
Which inverts your question into the most valuable thing in this round:
- gray-vs-skip beats skip when the slot is scarce and the replacement is better (the wick result: skip −39.0R, gray +28.1R). Here there is no scarcity, so gray ≡ skip. No cascade to exploit means no cascade to lose. The mechanism Q2 depends on is absent, and that is arithmetic, not a prior.
- And the real exposure is the opposite one: how much of +325.8R is 3–6-deep concurrency that only exists because of a string comparison? A live bot with correct code, or with real capital behind it, cannot do that. Unmeasured.
P96 — IS THE CHAMPION 3–6 DEEP BY ACCIDENT? (rank 1)
ID            : P96
R1 status     : open. method/RISK_CONCURRENCY.md identified the bug and deferred
                it in one line ("recorded, not fixed"); no experiment has
                run a fixed guard. exp_max_concurrent was swept as a CAP
                (5 free-to-better), which is the opposite question — that
                sweep found more concurrency is free, because the guard
                never binds.
THESIS        : The champion's pinned 500t/+325.8R contains 3-6 concurrent
                positions admitted by a type mismatch, not by a position
                policy. Part of the book is not deployable by a bot whose
                guard works.
COUNTER       : this is wrong if a corrected guard reproduces the shipped
                ledger within the cost model — i.e. the concurrent entries
                are all genuine same-day re-entries that a correct guard
                would have blocked for a *reason*.
FALSIFIER     : one run, one number — net R of the corrected-guard book,
                champion IS, against the shipped pin as control. |dNet| <
                M = 193.4R → the guard is immaterial and this is closed.
FAMILY        : four arms, all reported, none selected —
                (a) shipped pin (control, must be exact);
                (b) guard compares datetimes, not strings  [the fix];
                (c) guard compares datetimes AND enforces
                    exp_max_concurrent=1 (strictly serial);
                (d) placebo: guard fixed but compared against a synthetic
                    date that reproduces today's broken behaviour — this is
                    the arm that proves (b)'s delta comes from the fix and
                    not from re-timing. Without (d) this run is unreadable.
EXPECTED SIZE : unknown and genuinely two-sided. Removing concurrent
                entries removes trades AND removes double-counted overlap
                R. My expectation: a large negative dNet, because the
                concurrent entries are the exp_mltf/exp_persist re-entries
                the champion is explicitly built on. If dNet is small,
                the book is far more deployable than anyone assumed.
DATA NEEDED   : on disk. In-memory patch, 4 lines at :743 and :577. No
                production file edited; the pin is asserted, not moved.
BLOCKERS      : none. Not adoptable as an "improvement" — a fixed guard is
                a bug fix, not a parameter. Its result is a deployment
                bound, and it must be reported whatever it says.
PERIOD-CONTROL: not a filter. But report the per-half-year and per-year
                dNet: if the delta is concentrated after 2025H2 that is
                an era signature and I will say so rather than bury it.
P97 — THE WINDOW'S RIGHT EDGE: lift the two bounds nobody has lifted
ID            : P97
R1 status     : PARTIALLY TESTED — and I am putting this first because
                R1 says say it out loud, not because the idea is clean.
                • htf_rr SWEPT: {1.0,1.5,2.0,2.5,3.0,3.5,4.0} × ext
                  {1.0…3.0} (sweep_htf_rr.py, sweep_rr_grid.py), per-year
                  2023-2026 only. Grid TOPS OUT AT 4.0 = 1.33× shipped.
                • Re-swept at 2.0/2.5 on KING multi only
                  (experiment_registry.py:1235-1253, "pre-fix only").
                • CHECKLIST:567's own recorded finding: "best combo varies
                  BY REGIME." Never adjudicated against M or partition.
                • cap_days=16: NEVER SWEPT. A literal in three calls.
                  OPEN_RESEARCH_QUEUE [ ] P4, still open.
                • window_end="bias_flip" is a lengthening arm, run
                  2026-09-08: 485t +368.6R vs 330t +331.1R — +47% trades,
                  +37.5R, added cohort t=1.21 NOT significant. Not adopted.
                • NO_EXPIRY_P56 removed the window end entirely: ~1.7×
                  trades at PF ≥1.79 in 4/4 cells, dNet era-split
                  (IS −121/−141R, OOS +82/+101R). *** THIS IS THE 10th
                  ERA-SPLIT APPEARANCE AND IT IS THE OWNER'S DIRECTION. ***
THESIS        : The window is a leash shorter than the ratchet, and P93
                proves the leash is what kills trades: inside-window mean R
                is NEGATIVE in 4/4 (−0.157/−0.379/−0.126/−0.286) while
                outlivers are +4.4…+5.1R. HTF_ATTRIBUTION adds the other
                half: +3R-ending windows are the BEST windows (55.7% WR,
                +231.4R). So the window is being cut at the exact moment
                the 1h thesis is strongest. Lifting htf_rr and cap_days
                converts known-negative inside trades into known-positive
                outlivers — the first family in 31 experiments that adds
                trades of a MEASURED-BETTER composition.
COUNTER       : this is wrong if shortening the window is also good — then
                16d/3.0R is a knife-edge local optimum and this is the
                11th era-split wearing a mechanism.
FALSIFIER     : one run, one number — the TWO-SIDED criterion, pre-
                registered before any cell: lengthening must be ≥0 in both
                eras both lanes AND shortening must be ≤0 in both eras both
                lanes. If cap=8 and htf_rr=2.0 are ALSO positive, family
                dead. If lengthening is era-split, family dead.
                Second, independent falsifier, and this is the one that
                makes it a different experiment from NO_EXPIRY: the ADDED
                COHORT's trimmed mean must exceed the champion's, and the
                outlive share of the book must RISE. A window change that
                adds trades of the same composition is NO_EXPIRY again.
FAMILY        : all five arms, no best-of —
                htf_rr ∈ {2.0, 3.0[ship], 6.0, ∞} × cap_days ∈
                {8, 16[ship], 30, 45}, plus window_end="exit_ignore_target"
                (window ends at SL or cap, never at the target — a
                different code path from raising htf_rr, and the only one
                that keeps the target for the 1h book itself).
                The 2-D grid is reported in full. NO cell selected, which
                is the whole lesson of P69's 0.40% peak.
EXPECTED SIZE : my honest prior is LOW and I will not dress it up.
                NO_EXPIRY is the extreme arm of this family and it lost on
                gate 1. The best I can hope for is a magnitude
                improvement inside the era-split, which is not adoption.
                What I DO expect: a decisive answer on whether window
                length is a real axis or a fitted one, and a
                composition table nobody has.
DATA NEEDED   : on disk. cap_days needs lifting out of three literals
                into a kwarg — in-memory patch, pin asserted first.
BLOCKERS      : none. Both knobs are inside the engine signature already
                (htf_rr) or a three-line literal (cap_days).
PERIOD-CONTROL: this is the §5a ban, so it owes §6 explicitly. Run the
                §6 instrument (exp_ceiling_regime_ctrl.py, unmodified) on
                the added cohort: R_i = a + b·cohort_i + g_halfyear, with
                month-cluster t + month bootstrap + half-year bootstrap,
                all three reported. P87's discriminator: **b = 0 means the
                window change is a regime proxy and this is the 11th
                era-split.** b > 0 with all three agreeing in 3/4 cells is
                the only outcome that would revive it. My prior on that is
                low, and that is why it is rank 2, not rank 1.
Q3 — non-filter ideas, ranked honestly
#	idea	verdict
1	Concurrency guard (P96)	Run first. The only unmeasured thing I found that is a validity question, not an edge question. A live bot cannot do 3–6 concurrent positions, and the reason it can is a string comparison. Cheap, decisive, and its answer changes how much of the book is real.
2	Window right edge (P97)	Your direction, and the only lever that can increase supply — but one arm of it is already run and it is the 10th era-split. Mechanism is new, prior is bad. I would run it after P96 and only because P97's falsifier is a different test from NO_EXPIRY's, not because I expect it to work.
3	Entry fill convention (P98)	The book fills at the close of the bar in which the break occurred (v18_streak_halt.py:585) — the extreme of the bar that signalled. next_open exists at test_1m_precise.py:141 and test_c14.py:123 but only on the dead C14/1m paths. Exit-side fills have been audited (ANCHOR_BASIS_AUDIT); the entry side never has. Same family as P96 — a deployment bound, adoptable never. Three fills, all reported: shipped close / next open / next open + 5bp. Expect a real cost concentrated in longs and loading on P69's ATR%, because a breakout fill's cost scales with that bar's range.
4	Sizing	Blocked, permanently. No execution channel (v18_streak_halt.py has zero hits for equity/size/notional), and sizing cannot move net R in R-units (P9). Kelly's answer is already computed (method/KELLY_CONTINUOUS.md: 0.2–0.3% of bankroll for a heavy-tailed book).
5	The 15m LTF's unused 3R target (v18:592, computed/stored/never checked)	Dead before it starts. P93: the runners are the book. A profit target on the LTF deletes the only cohort worth keeping.
6	min_bars rebalancing between the 1h and 15m chains	Won't propose. min_bars=50 is a documented sharp optimum and the 1h/15m legs are deliberately lag-matched. Sweeping the ratio is a knob search after seeing a structural story — the P69 trap with extra steps.
Bottom line, three sentences. Your Q1 premise is off by 16× and its target is impossible against cap_days=16; the lever is the window's right edge, and one arm of that family already lost on gate 1. Your Q2 fails on a bug, not a prior — and that bug is the reason P96 is my first proposal. The genuinely under-measured thing in this repo is not an edge, it is how much of +325.8R is deployable, and two of the three items above are about that, not about making money.


---
nemotron
Based on my analysis of P93/P94/P95 and all prior work, here's my plan with three proposals:
PROPOSAL 1 — Q1: bars_to_wend THRESHOLD ARM
ID : BARS_TO_WEND_ARM_P96
R1 status : new (P95 measured AUC 0.84-0.87 but explicitly did NOT fit a threshold; P69 grid-peak trap warned against)
THESIS : A threshold on bars_to_wend at entry can isolate the outlive cohort (7-20× edge) without circularity, but the arm must clear M = 193.4R — which requires either (a) a threshold admitting >20% of trades, or (b) a threshold that admits the same ~20% but with higher per-trade R than +4.9.
COUNTER : this is wrong if the threshold that maximizes net R admits ≤22% of trades and still fails M (P94 arithmetic: 34 OOS trades × +4.9R = +166.6R max, < 193.4R), OR if the period-control regression (§6) shows b ≈ 0 (the threshold is just smuggling era information).
FALSIFIER : Single run exp_bars_to_wend_threshold.py sweeping thresholds 100-500 bars (step 25). Output: for each threshold, net R IS/OOS, trade count, and period-control b (cluster-robust t, month-bootstrap, half-year-bootstrap) for all 4 cells. Pass = any threshold clears M in ≥3/4 cells AND b > 0 with t > 2 in ≥3/4 cells. Fail = no threshold clears M, or all passing thresholds have b ≤ 0.
FAMILY : 17 thresholds × 4 cells = 68 arms. All thresholds must be tested together (R3); we adopt the single best threshold only if it passes the falsifier, else none.
EXPECTED SIZE : Best case: threshold ~300 bars admits 25-30% of trades (70-85 IS, ~40-50 OOS) at +4.5R/trade → +315R IS / +200R OOS. Realistic: threshold admits 20% (same as outlive cohort) → fails M. The arithmetic is brutal: M requires either MORE trades or HIGHER R/trade.
DATA NEEDED : on disk (champion trades with bars_to_wend computed in P95)
BLOCKERS : None from §7. No size channel needed. Forward data not required for threshold selection (period-control uses full history).
PERIOD-CONTROL : Expect b = +0.5 to +2.0 if threshold captures real microstructure (time-to-develop). b = 0 means threshold is just an era proxy (like P55/P67/P68).
PROPOSAL 2 — Q2: ADAPTIVE SLOT POLICY (NON-FILTER)
ID : SLOT_POLICY_ADAPTIVE_P97
R1 status : new (CLOSED_DO_NOT_REPEAT §63: "Relax cooldown/max_consecutive_losses" = 0/4, but that was UNIFORM relaxation. Adaptive slot policy based on bars_to_wend is untested. P94 §90-98: "question is why champion takes the other 80%... touches slot and cooldown policy rather than an entry rule... points at more trades rather than fewer")
THESIS : The champion's 1-slot policy lets early weak trades (low bars_to_wend ≈ 77 bars / 13 days) occupy the slot and block later strong trades (high bars_to_wend ≈ 459 bars / 76 days). An adaptive slot policy that grants extra concurrent slots when bars_to_wend is high (long window ahead) and restricts slots when bars_to_wend is low (window expiring soon) captures more outlive-cohort trades without filtering entries.
COUNTER : this is wrong if (a) the extra slots just add more inside-window trades (negative mean R, P93), not outlive trades, OR (b) the period-control b for the adaptive policy is ≤ 0 (it's just an era proxy), OR (c) max DD increases > 1.5× champion (27.7R IS).
FALSIFIER : Single run exp_slot_policy_adaptive.py testing 3 policies: (1) 1 slot always (control), (2) 2 slots if bars_to_wend ≥ 300 else 1, (3) 3 slots if bars_to_wend ≥ 400, 2 slots if 200-399, 1 slot if < 200. Output: net R, trade count, max DD, period-control b for all 4 cells. Pass = any policy beats control on net R in ≥3/4 cells with b > 0 (t > 2) AND max DD ≤ 1.3× champion. Fail = no policy beats control, or DD explodes, or b ≤ 0.
FAMILY : 3 policies × 4 cells = 12 arms. Test all; adopt best only if it passes falsifier.
EXPECTED SIZE : Policy (2) target: +50 to +100R over champion in OOS (capturing more outlive trades), IS +20 to +60R. Trade count increases 20-40%. Max DD ≤ 35R IS.
DATA NEEDED : on disk (champion trades, bars_to_wend, window timestamps)
BLOCKERS : Engine modification needed — exp_max_concurrent is a cap, not dynamic. Requires in-memory patch to btc_engine.py slot allocation logic (per repo rules: patch in memory, install to sys.modules).
PERIOD-CONTROL : Expect b = +1.0 to +3.0 if policy captures real "time to develop" edge. b = 0 means slot allocation is just tracking era.
PROPOSAL 3 — Q3: FS-ONLY ENGINE WITH SWING-TRAIL (NON-FILTER, ARCHITECTURE)
ID : FS_ONLY_SWING_TRAIL_P98
R1 status : open (CLOSED_DO_NOT_REPEAT §128-127: "True FS-only engine... explicitly listed as open"; P73 ran HYBRID not pure FS-only; method/FS_ONLY_ENGINE.md tested fixed target only, not swing-trail). Other bots: Nemotron P2, LongCat P1 both propose this — CONVERGENCE on highest-priority open direction.
THESIS : The FS mark (final swing confirmation) is the completion of the same 1h swing the champion trades. 2,900 IS / 1,634 OOS confirmed swings exist, but only 314/179 produced a B2/FLIP entry. FS entries with the champion's proven swing-trail exit (trailing="swing", exp_trail_half=1, exp_trail_delay_r=1.0) will capture the full trend move on the 9× larger pool, producing a larger book with same per-trade quality.
COUNTER : this is wrong if (a) FS-only net R is negative in either era, (b) WR collapses below 22% (FS is lagging confirmation with no edge), (c) ex-best-5 worse than control, (d) period-control b ≤ 0.
FALSIFIER : Single run exp_fs_only_swing_trail.py — pure FS entry (no B2/FLIP), swing-trail exit. Output: net R, trade count, WR, PF, period-control b for all 4 cells. Pass = net R > 0 both eras, WR ≥ 22%, ex-best-5 ≥ control, b > 0 (t > 2) in ≥3/4 cells. Fail = any cell negative net R, or WR < 22%, or b ≤ 0.
FAMILY : 1 engine variant × 4 cells = 4 arms. (Not a grid — single coherent architecture change.)
EXPECTED SIZE : IS: 400-600 trades, +200 to +400R. OOS: 200-300 trades, +50 to +120R. Per-trade R lower than champion (~+0.4-0.6 vs +0.65) but volume 2-3× higher.
DATA NEEDED : on disk (all 15m/1h/1m data, FS marks already computed in swing dicts)
BLOCKERS : Requires in-memory engine patch (FS entry path + swing-trail exit). No size channel needed. No new data.
PERIOD-CONTROL : Expect b = +2.0 to +5.0 (P94 outlive cohort b = +4.9 to +5.25; FS cohort should inherit similar structural edge). b = 0 means FS entries are just era-correlated.
RANKING & RATIONALE
Rank	Proposal	Why
1	FS_ONLY_SWING_TRAIL_P98	Highest upside: 9× larger trade pool, explicitly open in CLOSED_DO_NOT_REPEAT, convergence across 3 researchers (Nemotron, LongCat, this), attacks ARCHITECTURE not filtering. Only risk: FS may be too late (lagging). Falsifier is sharp — dies immediately if WR < 22%.
2	SLOT_POLICY_ADAPTIVE_P97	Only non-filter idea addressing the CORE problem (P94: "why champion takes the other 80%"). Uses bars_to_wend (P95's only separating feature) as slot allocator, not filter. Solves "more trades not fewer". Engineering barrier but no data barrier.
3	BARS_TO_WEND_ARM_P96	Honest assessment: likely fails M on arithmetic alone (P94 showed 20% cohort maxes at 0.93×M). Included for completeness because P95 AUC 0.85 is the strongest entry-time signal found. Run only if Proposals 1-2 fail or as parallel path.
R1 VERIFICATION CHECKLIST
Proposal	CLOSED_DO_NOT_REPEAT	Other Bots	Status
BARS_TO_WEND_ARM	Not listed (P95 explicitly no threshold)	Not proposed	✅ New
SLOT_POLICY_ADAPTIVE	§63 tested uniform relax only	Not proposed	✅ New (adaptive ≠ uniform)
FS_ONLY_SWING_TRAIL	§128-127: explicitly OPEN	Nemotron P2, LongCat P1	✅ Open, convergent
EXECUTION ORDER
1. Week 1: exp_fs_only_swing_trail.py (highest upside, harnesses exist)
2. Week 2: exp_slot_policy_adaptive.py (engine patch needed)
3. Week 3: exp_bars_to_wend_threshold.py (only if 1-2 fail; low M-clearance probability)
QUESTIONS FOR YOU
1. FS-only: Test as replacement (B2/FLIP removed) or addition (B2/FLIP + FS)? CLOSED_DO_NOT_REPEAT §126 warns: P73 hybrid assumed additions but "survivors vs newcomers" never decomposed. I recommend replacement first (cleaner causal test), then addition if replacement works.
2. Slot policy: Should I patch btc_engine.py in-memory (per repo rules) or create a wrapper harness? The dynamic slot logic needs to intercept _allocate_slot() or equivalent.
3. Parallel vs sequential: Run all three in parallel (separate processes) or sequential? Parallel gets answers faster but uses more compute.


---
space bunny opencode ka:
Read all of P89–P95 plus the harnesses. Two errors in the brief's premise that change your three answers — I'll lead with those.
🔴 Correction 1 — P95's "76 days" is a 16× unit error
exp_inside80.py:166 computes bwe = (we - e) / 900.0 where both are unix seconds. So bwe is in 15m bars:
P95 says	Actual
OUT mean 458.8 bars = "76 days"	4.78 days
IN mean 76.6 bars = "13 days"	0.80 days
AUC 0.847 is unaffected (monotone rescale), and the finding stands. But every downstream sentence built on "76 days vs 13 days" is wrong by 16×.
🔴 Correction 2 — "is this trade going to get 30+ days?" is impossible on the shipped book
cap_days=16 caps window life at 16 × 96 = 1536 bars. Your best observed bars_to_wend is ~459. No trade in this book can ever be given 30 days of window. 30 days needs 2880 bars.
method/WINDOW_LIFE.md already measured the answer: uncapped windows reach 98.1 days. So the feature you're asking for doesn't exist — cap_days is the binding constraint, and it was already run.
Q1 — Can you build an arm on bars_to_wend? Yes. Your two objections are both wrong, for one reason.
Your worry: "20% trades rakhne se M nahi banta."
That arithmetic assumes a subset. A gate is not a subset. Here's the closed arithmetic (P93's IS numbers reconcile exactly to the pin):
OUT  103t × +4.915 = +506.2R gross,  − 24.3R costs  = +481.9R net
IN   396t × −0.157 =  −62.2R gross,  − 93.5R costs  = −155.7R net
                     ─────────────────────────────────────────────
                     +326.2R   ≈  champion +325.8R   ✓ closes
Remove the IN cohort → champion becomes +481.9R. dNet = +156.1R = 0.81×M. You need +37.3R more to clear M. That's +0.094R per freed slot across 396 slots. The book averages +0.65R/trade.
OOS is tighter: dNet +108.5R = 0.56×M, needing +0.41R per freed slot across 208.
Why this is categorically unlike the 31 failures
Every filter in this repo removed a cohort that was worse but still profitable — that's the repo's own post-mortem (EXPERIMENT_LOG:831: "in IS the gates were removing money, not adding it"). The IN cohort is net-negative in 4 of 4 cells. It is the first candidate in the programme whose dropped bucket was losing money before the gate touched it. That is the whole reason M is reachable here and wasn't anywhere else.
The objection you didn't name (and it's the serious one)
P95 flagged it: "some of the 0.85 is arithmetic rather than predictive." Worse than that — the label is defined in terms of the feature. outlive ≡ hold > bars_to_wend. So AUC 0.85 is not an out-of-sample estimate of anything. It is a duration claim wearing a cohort label.
My correction to P95's own reasoning: the independence null here doesn't have an obvious sign (large bwe forces a long hold by definition, but hold correlates with bwe too), so I won't claim AUC 0.85 is fake. But it carries no information about why long holds are profitable. That has to be tested separately.
ID            : P96
R1 status     : NEW. P95 measured the AUC and explicitly refused to fit a
                threshold. P94 measured the cohort and it failed M at 0.47-0.93x.
                Neither ran a path-true gate. Nothing exists.
THESIS        : The first cohort in this programme whose dropped bucket is
                NET-NEGATIVE in 4/4 cells (-0.157/-0.379/-0.126/-0.286 gross).
                A causal entry-time proxy for it exists (bars_to_wend, AUC
                0.843-0.867). Removal is worth +156R IS before the cascade.
COUNTER       : Wrong if bars_to_wend only predicts HOLDING PERIOD and not
                profitability - i.e. if it is a duration feature, and long
                holds are profitable only because the trail lets winners run
                (P92: drawdown shape is a top-5% property). Then the gate
                removes 396 trades to buy 37R of cascade, and the cascade
                never arrives.
FALSIFIER     : One run, one number. Re-run the AUC against a label that is
                NOT mechanically tied to the feature:
                    AUC( bars_to_wend  ->  hold > 96 bars )
                0.5 => bwe is the identity, family closed.
                >= 0.60 => bwe is a genuine duration predictor, proceed.
                Do this BEFORE the engine work. It is descriptive, costs
                nothing, and needs no new pin.
FAMILY        : {bwe >= T} for T in {192, 384, 768} bars, fixed in advance.
                All three must pass. Plus hold>96 as the identity check.
                Plus gray-vs-skip (the wick gate showed this is not optional:
                skip -39.0R IS vs gray +28.1R IS, a 67R swing).
EXPECTED SIZE : 0.81x M in IS, 0.56x in OOS, BEFORE the cascade. M is reachable
                only if freed slots return >= 0.09R (IS) / 0.41R (OOS) each.
                I do not expect to clear M. I expect 0.6-0.9x.
DATA NEEDED   : on disk
BLOCKERS      : none
PERIOD-CONTROL: b = (kept - dropped) after a half-year FE, month-clustered.
                P87's harness, unmodified. b must be POSITIVE, which is the
                opposite sign from every filter P87 has ever been run on -
                that is the whole point and it is the thing to check first.
CAVEAT        : P93 lost 28 of 279 OOS trades to window matching, and those
                28 are worth ~+0.93R each (26.0R/28 by residual). They are
                excluded and they are GOOD. This is the run's biggest hole.
Q2 — Can an exit rule save the weak 80%? No, and I can tell you why in 20 minutes for free.
Your idea: exit the short-bwe trades early to free the slot.
The IN cohort is already the fast-exit cohort. They were entered with 0.8 days of window left, they got boxed, they hit the trail or the stop. Their −0.157R average is already realised at −1R. There is nothing left to save. An early exit on a trade that is already stopped is a no-op.
Worse, structurally: you cannot condition the exit on bwe being small, because bwe never changes after entry. So the rule is "for trades entered with low bwe, use a tighter exit" — a legitimate causal rule that buys you the difference between "lost at −1.0R" and "exited at −0.6R" on trades that are mostly the former.
The cheap decisive check, no engine work:
Report the IN cohort's R distribution: median, % at exactly -1.00R,
% below -0.50R, and its mean bars_held.
If >60% of IN trades sit at exactly −1.0R, there is no loss left to compress and Q2 is closed permanently — exit-side work on this cohort can never be worth more than a few R. I'd run this before anything else; it is 20 minutes and it either kills the whole exit direction or reframes it.
And the deeper point: not entering frees the slot from the start; exiting early frees it later, and the replacement arrives later still. For a book whose problem is that the OUT cohort needs 4.8 days, entry policy strictly dominates exit policy. This is architecture, not a trade.
Q3 — Something nobody has touched
**Rank 1 — CLOSED 2026-10-01. ~~exp_window_entry_cap — cap entries per parent window.~~** It already ran. See :416, point 4: CHECKLIST 24.9 records the result as **"OOS-only, NOT ROBUST"**. Not a proposal.
method/ENGINE_SHELF.md:28 lists it UNTESTED. It is a slot policy, not a filter: it throttles, does not veto, and the cascade question doesn't bite in the same form (ENGINE_SHELF:38-40 says exactly this).
The mechanism is already measured. P95: bwe falls monotonically as a window ages, so the N+1'th entry in a window is guaranteed lower-bwe than the N'th. And WINDOW_LIFE says the champion runs 1.6 trades per window, 2.6 uncapped.
ID            : P97
R1 status     : ~~NEW, and on the shelf as untested. method/ENGINE_SHELF.md:28.~~ **CLOSED — it ran, and the result was OOS-only / NOT ROBUST (:416). "Untested" in ENGINE_SHELF means "no robust result", not "never run".**
                Distinct from P96: P96 is a time threshold, this is a count.
COUNTER       : Wrong if entry ordinal within a window carries no
                information - i.e. the 2nd entry in a window is no worse
                than the 1st once you control for the half-year. Plausible,
                because a 2nd entry only fires when the 1st left room, which
                means the 1st failed.
FALSIFIER     : One run, one number, and it costs nothing because it is
                PURELY DESCRIPTIVE on the existing champion book:
                    mean net R and trade count, bucketed by ordinal within
                    the parent window, all four cells, with a half-year FE.
                If mean R is flat or rising in ordinal, this family is dead
                and no engine work is justified. If it falls in ordinal,
                proceed to the path-true arm.
                This is the cheapest high-information run in the whole list.
FAMILY        : {cap = 1, 2, 3} against the shipped uncapped. All must pass.
                Plus the cap_days axis {16, 999} - see below, they are one
                family.
EXPECTED SIZE : Unknown and I will not guess. Trades removed = 0.6 per
                window x 309 windows IS = ~185 entries. If those are the
                lowest-bwe tail, they are part of the -155.7R IN cohort.
DATA NEEDED   : on disk
BLOCKERS      : none. Path-true engine work needed for the arm, but the
                falsifier is post-process only.
PERIOD-CONTROL: b on ordinal, half-year FE, month-clustered. Sign should be
                negative (later ordinal = worse).
Rank 2: the P96 / P97 / cap-off family merge — R3 honesty
cap_days off (P49, 4/4 positive, +75.3R IS / +55.1R OOS, adds 86/34 trades) and entry_cap are the same mechanism from two ends: both raise bars_to_wend for the marginal trade. Under R3 they are one family and the weaker one drags the other. P49's cap-off already has a measured mechanism and 4/4 same-sign — it is the strongest untested-through-§6 item in the repo and it has never been through the P87 instrument.
Say this in the write-up or R3 will be violated silently.
Rank 3: §7's blocker #1 is wrong as stated — and P91 opened the door
The brief says "any sizing change has no execution channel." That is true of v18_streak_halt.py and false of the live bot:
live_loop.py:1869   qty = self._calculate_qty(entry_price, sl_price)
The live bot has risk-based lot sizing. So the blocker is a backtest-harness limitation, not a deployment one.
And P91 built the measure where sizing would actually matter: absolute return per unit notional. ~~P91's finding — every short book loses money in price terms in both eras (IS −0.4415, OOS −0.7471) while reading +53.2R and +68.4R — means a live-only short-side size reduction is a real, executable, zero-backtest-change risk decision.~~ **RETRACTED 2026-10-01 — the premise was a sign-convention error, so there is nothing to size.**

**What happened:** `exp_entry_fill_absolute.py`'s `abs_return()` never read `t["dir"]`, so it computed `(exit − entry)/entry` for shorts too — which is the *negative* of PnL. A profitable short exits below entry, so its raw change is negative. P91 read those negatives as losses. Re-derived in `exp_p121_short_absolute.py`, the shorts are **+0.4415** IS and **+0.7471** OOS in absolute terms, against +105.7R and +83.6R — exact negations, and the two metrics **agree**. There is no divergence to size against. See `method/FILL_ABSOLUTE_P91.md`.
That is the first sizing question this repo has ever been able to answer, and it took P91 to make it answerable.
Rank 4: P89 and P91 contradict each other on the short side and nobody has reconciled them
 	says about shorts
P89	OOS b = −0.29 → no deficit to correct; shorts are fine
~~P91	shorts are −0.44 IS / −0.75 OOS in absolute terms → a real drag~~ **RETRACTED 2026-10-01 — sign-convention error; shorts are +0.44 / +0.75 and agree with R.**
They used different measures (R vs absolute) on the same trades. One of them is an artefact. Until that is settled, the entire P84/P86 "protect the long side" programme is resting on an unexamined premise — it may have been solving a denominator problem.
One run: absolute return per unit notional ~ short + half-year FE, month-clustered, four cells. If b < 0 and significant, shorts are a genuine drag and the fix is size, not filter. If b ≈ 0, P91's absolute number is itself a stop-distance artefact and P89 stands.
This is cheap and it is the highest-leverage thing on the list, because it decides whether a whole direction was real.
Honest ranking
#	ID	Verdict
1	P89/P91 reconciliation	Cheapest, decides whether a whole direction was real. Do first.
2	P97 descriptive falsifier	20 minutes, zero engine work, kills or licenses the slot-policy family.
3	P96 identity check	20 minutes, decides whether bars_to_wend is a feature or a tautology.
4	P96 path-true gate	0.6–0.9× M. First gate in the programme whose dropped cohort loses money.
5	P97 engine arm	Only if #2 fires.
6	cap-off through §6	Best-motivated item never period-controlled.
7	Q2 exit rule	Kill it. 20-minute distribution check will close it.
~~8	Short-side sizing (absolute)	Live-executable, unscored in R, real. Needs a risk decision, not a backtest.~~ **STRUCK 2026-10-01 — the premise was retracted, so there is nothing to size. Do not pick this up.**
The single most likely outcome: none of these clear M. The honest case for running them anyway is that P96 is the first removal whose dropped cohort was losing money — and M is a whole-book null being applied to a cohort change, which P63 already said is the wrong bar for the forward slice and arguably here too.
Want me to write the P89/P91 reconciliation and the two 20-minute falsifiers as one harness? They share the data load and the P87 instrument, so it is one file, ~10 minutes of runtime.

---
long cat:
Padh liya — P93, P94, P95, round index, closed list, backlog. Ab honest research review:
Q1 — bars_to_wend pe arm bana sakte ho? Nahi. Owner sahi hai.
Owner ke weak points, seedha:
1. "OOS me sirf 34 trades" — ye outlive cohort hai, bars_to_wend cohort nahi. 34 trades = exit_ts > window_end se selected (P94, circular). Ek 20% bars_to_wend filter 279 OOS trades me se ~56 rakhega. To owner ka number thoda understate karta hai — par conclusion sahi hai.
2. M arithmetic sahi hai. Outlive cohort khud fail karta hai: 0.47–0.93×M (P94). bars_to_wend filter usi cohort ko approximate karega. 56 OOS trades ko +4.7R/trade chahiye M ke liye — outlive cohort +4.389R/trade pe hai. Filter ko outlive cohort se BEHAD trades identify karne honge, jo circular hai (outlive cohort hi best possible hai).
3. 0.85 AUC ka mechanical component. P95 khud kehta hai: "a trade cannot outlive a window that is nearly closed." 0.85 ka kuch hissa arithmetic hai, predictive nahi. Kitna — ye run se pata nahi chala. Bina threshold ke ye description hai, gate nahi.
Verdict: Filter ke roop me bars_to_wend kaam nahi karega. 31 failures ka pattern repeat hoga.
Q2 — Exit rule se bach sakte hain? P93 ne band kiya, par owner ka idea alag hai — mostly closed.
Owner ka idea: "13-din trades ko jaldi exit karke slot khaali karo, nayi 76-din lo."
Problem ye hai: P93 ne dikhaya — window end pe jo trades still open hain, wo best hain (+4.4R avg). Jo trades window ke andar close ho jaate hain, wo already ratchet stop se closed hain. To window end pe exit karne se sirf winners katte hain — ye P93 ka finding hai.
Owner ka idea tab kaam karega agar exit window end pe nahi, pehle ho. Yaani: trade ko jaldi exit karo agar wo +1R tak nahi pahuncha. Ye time stop hai, SL variant nahi.
Ye open hai — closed list me nahi. Par exit family sabse zyada closed family hai (FS_TIME_DECISION, SL_TIGHTEN, pivot trail, half-swing, parent death — sab dead). Trigger alag hai (time + R guard, ya price/structure), par family risk high.
Magnitude honest estimate: Slow losers (inside cohort, ~80% trades) average −0.2R. Time stop unhe −0.1R pe cut karega → 0.1R × 400 = 40R. Slot turnover: agar avg hold 13 bars se 7 bars gire, to 115 extra trades × 0.65R = 75R. Total 115R. M (193R) se par hai.
Q3 — Non-filter idea? Time stop + slot policy — yehi ek "zyada trades" wala idea hai.
P94 ne flag kiya tha: "pehla finding jo ZYADA ki taraf ja raha hai." Time stop wahi hai:
- Filter nahi — entry pe trade nahi drop karta.
- SL variant nahi — price pe nahi, time + R guard pe.
- Regime detection nahi — entry-time knowable, calendar nahi.
- Slot policy hai — exit se slot free hua, naya trade aaya.
Par honest ranking: ye long shot hai. Magnitude ~115R, M se 80R short. Aur exit family ka risk sabse zyada hai.
§9 Proposal — P96
ID            : P96 — TIME STOP WITH +1R GUARD
R1 status     : open. Exit family closed hai (FS_TIME_DECISION, SL_TIGHTEN,
                pivot trail, parent death P93) — par time stop + R guard
                alag trigger hai. Closed list me nahi.
THESIS        : Trade jo N bars me +1R nahi pahuncha, uska thesis fail hua.
                Exit karo, slot free karo, naya trade lo. Winners (jaldi +1R
                pahunchte hain) bache rahenge, tail bacha (+1R guard se).
COUNTER       : Ye galat hai agar slow losers bhi tail me hain (kuch +10R
                trades dheere +1R pahunchte hain). +1R guard mitigate karega
                par eliminate nahi. Aur agar freed slot ka replacement bhi
                average se bura nikale, to slot turnover ka benefit zero.
FALSIFIER     : Ek run, ek number — dNet(time stop vs champion), 4 cells.
                |dNet| < M = 193.4R → dead.
FAMILY        : (a) exit if not +1R in N bars [primary, N = 5/10/15 bars],
                (b) exit if not +1R in N bars OR at window end if R < 0
                [structure + time hybrid], (c) P93 unconditional [closed,
                control ke roop me]. Sab pass ya koi nahi.
EXPECTED SIZE : ~115R total (40R exit savings + 75R slot turnover).
                M se 80R short. Honest: long shot.
DATA NEEDED   : on disk. P93/P95 machinery reuse (window matching,
                bars_to_wend, trade ledger).
BLOCKERS      : §7 se koi nahi. Engine edit nahi — exit post-process.
PERIOD-CONTROL: §6 instrument, cohort = early-exited trades. b positive
                chahiye. b ≈ 0 → era smuggling, dead.
Honest ranking
Idea	M clear?	Verdict
Q1: bars_to_wend filter	Nahi (0.47–0.93×M)	Closed by P94 arithmetic
Q2: exit at window end	Nahi (P93: winners katte hain)	Closed by P93
Q3: time stop + slot	~115R, M se short	Long shot — run if kuch aur nahi
Sach ye hai: P95 ka finding real hai (80% window-limited hain, entry-mistake nahi) — par actionable space narrow hai. Filter fail hai (M), exit fail hai (P93), time stop weak hai (magnitude). Champion ke 80% "price of admission" hain — unke bina good trades nahi milte, aur unhe kaatne ka koi cheap tareeka nahi mila P55–P95 me.
Agar owner chahe to P96 run kar sakta hai — ek run me settle ho jayega.
---
mimo:
Recap — where we are
Programme: champion_multi_sw10 (v18), pin IS 500t/+325.8R, OOS 279t/+70.1R, gate bar M=193.4R.
Done this session (all read-only, source-verified):
- Read the R1-mandated set + the P93/P94/P95/P56/RISK_CONCURRENCY/TRADE_EXPANSION docs and the peer answers already in method/ROUND_SUMMARY_P55_P95.md.
- Delivered last round's P93 answer in chat.
- Four verified findings nobody else has:
1. bars_to_wend is non-causal — exp_inside80.py:166 takes we from res["intervals"], built at v18_streak_halt.py:242 as int(t["exit_ts"]) (parent's future exit). Peers killed the 16× unit bug; nobody saw the look-ahead.
2. Champion has no slot at all — test_experiments_craze.py:955 rewrites the gate to if (not exp_mltf) and busy_until… (champion is exp_mltf=True), and :85 sets exp_max_concurrent=0 so the cap branch never runs → Big Pickle's P96 arms (b)/(d) are exact no-ops; RISK_CONCURRENCY's string-bug story is inert on this path.
3. Live is serial, backtest is up to 6-deep — live_loop.py:1777-1801 in_trade skip at 0R; ANCHOR serial +293.2R vs +446.2R. **PARTLY WITHDRAWN 2026-10-01 — see method/LIVE_CONCURRENCY_P118.md.** The +293.2R vs +446.2R comparison is champion-serial vs champion-deep, NOT live vs backtest. The live engine runs v18, a different book, and v18 is serial *natively* — `v18_streak_halt.py` has no concurrency parameter and `test_v18_causal_integrity.py:39` omits `exp_mltf`, so its 352 trades are already its cap-1 count. v18's own record is +146.55R net / PF 1.947. So the serial cost quoted here is a property of the champion, and "this is the real deployability bound" is withdrawn: it is a strategy-selection question, not a deployability one.
4. Two peer R1 conflicts — exp_window_entry_cap already ran (CHECKLIST 24.9, "OOS-only, NOT ROBUST"); "FS-only swing-trail" is marked closed (OPEN_RESEARCH_QUEUE:22) though the harness that closed it used fixed target_r (exp_fs_only_engine.py:160,208) — label and arms disagree.
Next step (the deliverable)
Write the empty --- mimo: section in chat, three questions in §9 format:
#	Answer	Proposal
Q1	Not on the reported feature — it's non-causal	P99 causal-countdown audit: AUC of bwe vs three variants (cap-budget w[0]+16d−e, open-parent horizon, shipped control), 4 cells, pre-registered: AUC<0.60 in ≥2 cells → whole P95 line dead; ≥0.75 in 4/4 → threshold arm licensed
Q2	No — freeing a position frees nothing, there is no gate	P101 blocked-signal census: count, per raw signal, which gate rejected it. Expect occupancy = 0 → closes Q2 permanently. Pair with space bunny's R-distribution check
Q3	Serial-vs-concurrent is the untouched architecture question	P100 slot-parity bound: one path-true run, exp_max_concurrent=1 vs pin, 4 cells. Two-sided (~150R prior). Merges into P96 with the correction that only its arm (c) can produce a number
Plus the cheap logic nobody added: pre-engine ceiling gate — if a threshold's post-process dNet can't clear 193.4R OOS, close the family without ever running the engine (OOS best-known cohort = P94's +118.6R = 0.61×M).
Own ranking: P99 → P100 → P101; P99 first because it gates two peers' top picks in ~20 minutes.
Proceed with writing the section in chat (no file edits), or do you want the ranking/order changed first?