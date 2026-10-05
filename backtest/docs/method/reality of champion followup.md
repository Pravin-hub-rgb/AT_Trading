# method/reality of champion followup.md

> ## 📌 SCOPE — backtest engine only
>
> No live engine is in this work. `live_loop.py` is stale (last touched 2026-09-26)
> and imports v18, not v19. Live-bot numbers are not a reference point here.
> **v19 is a backtest result, not a trading system.** See **SCOPE** below.

> ## ✅ RESOLVED — 2026-09-30, commit `7077046`
>
> The four objections in section *"Step 1"* (L209–L214 below) were **all correct
> when written**. All four are now closed. Full detail in **`method/P112_V19_REBUILD.md`**.
>
> | Objection | Status |
> |---|---|
> | `_v19_src.py` does not exist, harnesses cannot be re-run | **CLOSED** — both now import the committed engine |
> | Docstring corrupted, six consecutive quotes at line 17 | **CLOSED** — header is now an ASCII comment block |
> | Encoding damage visible throughout | **CLOSED** — rebuild was double-encoding bytes inherited from v18 |
> | "The pin is currently unproven" | **CLOSED** — reproduced by real disk import |
>
> ```
> IS   n=500  net=+325.78R  PF 2.384
> OOS  n=279  net=+70.15R   PF 1.591
> ```
>
> The bot sections below are the bots' own text. Where they say "unproven", read
> P112 — that is now superseded.
>
> ---
>
> # ANSWERS — what was actually run, and what it printed
>
> Written 2026-10-01. Every number below was produced by running the named file
> today. Five bots contributed: **big pickle, longcat, nemo, mimo, spance.**
>
> ### ⚠️ nemo found the pin is fake. Most important thing on this page.
>
> `nemo` asked: *"+325.78R ka provenance questionable hai. Kya ye kahin pinned
> hai?"* **It is not. nemo was right, and it is worse than nemo said.**
>
> ```
> experiment_registry.py
>   "champion_multi_sw10": { "engine": "patched",
>     "pins": {"n": 494, "net": 248.0, "dd": 21.2, "partials": 0} }   <- STALE
>
> exp_v19_import.py:24-25
>   print("  PIN  n=500  net=+325.8R")
>   print("  MATCH:", len(rs)==500 and abs(net_r(tr)-325.78)<0.5)     <- vs itself
> ```
>
> Two separate problems:
>
> 1. **The registry pin says 494 trades / +248.0R.** It disagrees with the engine by
>    6 trades and 77.8R. Never re-anchored.
> 2. **The harness pin is a literal typed into the harness.** It never reads the
>    registry. `MATCH: True` proves only that the engine still produces the number
>    *I typed in*. It cannot detect a registry/engine disagreement, which is the one
>    thing it existed to catch.
>
> **What survives:** the number is real. Re-run today, a real disk import of the
> committed file gives IS 500t / +325.78R / PF 2.384 and OOS 279t / +70.15R / PF 1.591.
>
> **What does not:** calling it "pinned" or "reproducible" as though an independent
> guard existed. It does not. Every earlier "the pin is proven" overstated this.
>
> The registry also still calls the champion `"engine": "patched"`, in 113 places.
> P112 made that obsolete - v19 is a real file.
>
> ---
>
> ## big pickle
>
> | Claim | Answer | Evidence |
> |---|---|---|
> | "5-6 params alag" | **3 of 6 differ.** `sl_buf_atr`, `chop_thresh`, `max_consecutive_losses` match; `mode`, `cooldown_bars`, `ext_stop_r` do not | table L43-L50, this file |
> | "ATR me look-ahead nahi" | **Correct.** Trailing window, entry at signal bar close, same instant | P112; `exp_v19_audit.py` B |
> | "`exp_mltf=OFF` serial nahi, guard string-bug se broken" | **Correct.** Gate compares a datetime to a date string, so it never blocks | `exp_v19_2x2.py` gate-ON: maxconc 1 |
> | "Live config backtest karo" | **Withdrawn** - live is stale, out of scope | `live_loop.py` last touched 2026-09-26 |
> | "6 positions = capital model chahiye" | **Overstated - and he said so himself later in the same reply.** R is scale-free, 6 x 1% = 6% margin | `method/CORRECTIONS_P106.md` |
> | "Concentration is the real risk" | **Correct, still unmeasured.** 6 entries in one 1h window, same direction by construction | nobody has measured it |
>
> ## spance
>
> | spance said | Answer | Evidence |
> |---|---|---|
> | `_v19_src.py` missing | **Closed.** Both proofs import the committed engine from disk | `exp_v19_import.py`, `exp_v19_oos.py` |
> | Docstring corrupted, six quotes at L17 | **Closed.** Header is an ASCII comment block; `py_compile` OK | `7077046` |
> | Encoding damage | **Closed.** v19 built from v18 as latin-1 with `newline=''` | `7077046` |
> | "the pin is unproven" | **Half right. nemo beat spance here.** It was unproven, it is reproduced - but the pin guarding it is circular, so "proven" overstates it. See top of page | this page |
> | "arm A is an artificial build" | **spance is right, I was wrong.** Arm A is a real book that is OOS-negative | `exp_v19_2x2.py` |
>
> ---
>
> ## longcat
>
> | Claim | Answer | Evidence |
> |---|---|---|
> | "+325.78R verified" | **The number, yes** - re-run today, 500t / +325.78R / PF 2.384. **But the pin behind it is broken**; see nemo above | `exp_v19_import.py` |
> | "`live_loop.py:1396` passes `fine_ltf=[]`, backtest uses 1m - a 4th difference" | **Confirmed by reading the line.** `fine_ltf=[],` at L1396; backtest passes `d["fine"]` | read directly |
> | "PERSIST=7 trailing ka counter nahi, regime switch ka" | **Confirmed.** `v19_champion.py:537-540` increments `_rg_c` only inside the regime block; the trail never touches it | read directly |
> | "max losing streak 3" | **Confirmed.** Registry `max_consecutive_losses: 3` | `experiment_registry.py` |
> | "Entry bar ka H-L range use hota hai" | **False.** Entry is the signal bar's **close**, 500/500, and the signal bar's own H/L is excluded from the exit path | `exp_v19_audit.py` B |
> | "double SL nahi, single SL + trail events" | **Agreed.** One stop variable, ratcheted by trail events | `v19_champion.py:698-701` |
>
> `longcat`'s `fine_ltf` point is a real backtest-vs-live parity gap. Recorded, not
> fixed - live is out of scope.
>
> ---
>
> ## nemo
>
> | Claim | Answer | Evidence |
> |---|---|---|
> | "Doc header contradicts itself" | **Real, worse than described.** L1 said "production candidate" while the body runs a backtest - now "backtest champion". The stray `# ## 1.` is a leftover numbering artifact | `5eec4d3`, `e971baa` |
> | "+325.78R provenance questionable" | **Correct, and worse than stated.** Registry pins 494 / +248.0R; the harness compares itself to a literal | top of this page |
> | "PERSIST regime nahi trailing" / "regime vs trailing unclear" | **mimo and nemo are both right.** It is a regime skip. It is also a *bar* count on the 15m timebase - not a position count, not hours. `PERSIST=7` at L539 increments once per 15m bar, so 7 = **105 minutes** | `v19_champion.py:300-301, 537-540` |
> | "Multi-position 11.8 average, max 6" | **Max 6 confirmed** (500-trade audit). The 11.8 average is reproduced by nothing in the repo, so I am not restating it | `exp_v19_audit.py` E |
> | "Capital: 6 concurrent = 6% margin, fine" | **Agreed, and already conceded in P106** | `method/CORRECTIONS_P106.md` |
> | "Engine directory has 24 engines" | **17, not 24.** `Get-ChildItem backend\src\btc\engines\htf_ltf -Filter *.py` returns 17. The wider point stands - several engines coexist | counted |
> | **"The champion is a family of configs, not one config"** | **The sharpest thing any bot said, and I agree.** `champion_multi_sw10` is one member. `PERSIST=7` is inherited, not earned; `exp_partial_r` is 0.0 and carries nothing. The edge is multi-position, orthogonal to most of the grid. The honest label is a mechanism, not a winner | P114, this page |
>
> ```
> arm                    |   ISn      ISnet    ISPF conc |  OOSn     OOSnet
> gate ON,  persist OFF  |   395    +137.72   1.859    1 |   230     -13.26
> gate ON,  persist ON   |   387    +150.40   1.931    1 |   219      -1.79
> gate OFF, persist OFF  |   500    +325.78   2.384    6 |   279     +70.15
> gate OFF, persist ON   |   500    +325.78   2.384    6 |   258     +67.75
> ```
> `exp_v19_2x2.py`, run 2026-10-01. The −1.79 row independently reproduces the
> −1.8R that spance quoted for "Arm B".
>
> **What the table says:** with the gate on, both single-position books are
> **negative OOS**. Multi-positioning is the only reason OOS is positive. That is
> spance's sharper framing and it holds.
>
> ## mimo
>
> | mimo said | What I found | Evidence |
> |---|---|---|
> | "6/6 params differ" | **3 of 6 differ.** `sl_buf_atr`, `chop_thresh`, `max_consecutive_losses` are identical; `mode`, `cooldown_bars`, `ext_stop_r` are not | the table at L43–50 of this file |
> | `exp_mltf=OFF` is not serial — the gate is string-broken | **Confirmed.** The gate compares a datetime to a date string, so it never blocks | `exp_v19_2x2.py`, gate-ON arm: maxconc 1 |
> | entry look-ahead | **None on the shipped fill.** `entry_price == close[signal bar]` on 500/500, and `close[i]==open[i+1]` on 500/500 | `exp_v19_audit.py` section B, both PASS |
> | porting the flags will not make the live bot multi-position | **Confirmed, and this is the blocker.** `live_loop.py:1778-1781` has its own guard: `in_trade = self._open_ltf_trade is not None` → `if in_trade:` → skip, journal at `r_multiple=0.0` | read directly, `live_stuff/live_loop.py` |
> | "P90's next-open arm is anti-causal" | **Confirmed and closed.** The arm filled at `open[i]`, the same bar, 15 min *before* the signal was confirmed. The true next-open is `open[i+1]`, and it differs on **0 of 500** trades because `close[i]==open[i+1]` | `method/P90_FILL_P109.md` |
> | "P91 retracted the number for the wrong reason" | **Agreed.** P91 blamed a denominator artefact. The operative fault was the one-bar-early fill, which a denominator argument would not catch | `method/P90_FILL_P109.md` |
>
> On the multi-position row: the finding stands, but it no longer blocks anything,
> because `live_loop.py` is out of scope. It is recorded so that whoever rewrites the
> live bot does not assume the port is sufficient. It is not — the live loop blocks
> the entry itself, so the 6-deep book needs a change there, not in the engine.
>
> ## One correction to P114
>
> P114 records that `PERSIST=7` "costs 2.40R OOS". The 2.40R is right, but the
> shape of it was described loosely. It is not a 2.40R haircut on an otherwise
> identical book — it **removes 21 OOS trades** (279 → 258) and nets 2.40R less. On
> IS it is bit-identical: 500 trades, +325.78R, PF 2.384, with persist on and off.
>
> PERSIST=7 is part of the champion's config, so it stays. It is not load-bearing.
>
> ## Audit result, stated honestly
>
> `exp_v19_audit.py`, run 2026-10-01: **11 checks, 10 PASS, 1 FAIL.**
> Breakdown — A: 4 PASS, B: 2 PASS, C: 1 PASS + 1 FAIL, D: 1 PASS, E: 2 PASS.
>
> The failure is section C, `recomputed R == reported R`, max drift **1.75e-03 R**.
> That is display-rounding scale, not a book error. All 187 SL exits are exactly
> −1.0R, no trail exit is worse than −1R, no duplicates, max concurrency 6. I am
> recording the FAIL rather than widening the tolerance to make it green.
>
> ## SCOPE — backtest engine only. There is no live engine in this work.
>
> `mimo` and `big pickle` both asked for the live bot's own backtest number. That
> question is **withdrawn, not answered.** The live bot is stale and out of scope,
> so its number is not a reference point for anything.
>
> The facts, so nobody reopens this:
>
> | | |
> |---|---|
> | `live_loop.py` last touched | **2026-09-26** (`bd78169`) |
> | P102–P114 and the v19 rebuild | 2026-09-30 / 10-01 |
> | What `live_loop.py:35` imports | `v18_streak_halt` — **not v19** |
> | Commits since live was last touched that changed the engine | P102, P112, P113, P114, `7077046`, `5eec4d3` |
>
> The live bot has not moved while the backtest engine moved six times. It cannot
> produce a comparable number, so comparing the champion to it would be measuring
> two different things and calling one of them a regression.
>
> `method/CORRECTIONS_P106.md` records a live-config run at 369t / +78.50R / PF 1.675
> against a golden-test claim of 351t / +137.33R. **That conflict is real and is
> still unresolved — and it is not ours to resolve.** It is a live-bot question.
> It does not block, inform, or qualify any backtest result in this repo.
>
> **What this work is:** one backtest engine, `v19_champion.py`, causally audited
> trade by trade, with the champion's edge attributed to a specific mechanism.
> The result reproduces on re-run, but it is **not** guarded by an independent
> pin - see the pin section above.
>
> **What this work is not:** a deployment. No live code is being changed, no
> capital model is being built, and no claim is being made that this bot runs
> anywhere. **v19 is a backtest result. It is not a trading system yet.**
>
> ---
>
> ## Open, and recorded as open
>
> 1. **No independent pin exists.** The registry says 494 / +248.0R; the engine
>    produces 500 / +325.78R; the harness compares itself to a typed literal.
>    `nemo` found this. It is the largest single gap in the work. Fixing it means
>    re-anchoring the registry *and* making the harness read the registry instead
>    of a constant. Until then nothing guards this number.
> 2. **The registry still calls the champion a patched engine** in 113 entries,
>    and still carries the stale 494 / +248.0R pin.
> 3. **Concentration is unmeasured.** Six same-direction entries inside one 1h
>    window. Flagged by `big pickle` and `nemo`, measured by nobody.
> 4. **Forward evidence is 2 trades over 12.5 days.** P63 wants 40-70.
> 5. **`longcat`'s `fine_ltf` parity gap** - backtest resolves exits on 1m, live
>    passes `fine_ltf=[]` and resolves on 15m. Recorded, not fixed, out of scope.
>
> ---

big pickle:
Teen corrections hain — teeno aapke bot ki. Aur ek cheez hai jo kisi ne nahi kahi.
❌ Correction 1: "HTF gate koi nahi khola" — GALAT. Already khola gaya hai, AABHI.
method/new bugs.md:601 — usi line me jo aapne quote ki:
## DEEP-DIVE AUDIT FINDINGS #2 — ~~ALL OPEN~~ ALL THREE NOW FIXED (re-verified 2026-09-26)
Jawab wahi line me likha tha. Aur git log me HEAD hi yeh hai:
7292a14 P101: HTF gate lookahead audit - champion is clean
"C12, C14 and C15 were fixed on 2026-09-17 and re-verified2026-09-26. Confirmed present in v19: close-time bisect at 6 sites, the 2700s window gate at 2 sites, and the causal streak counter."
Champion CLEAN hai. C14 (45min lookahead) aur C15 (60min lookahead) dono 2026-09-17 ko fix hue, 26 ko re-verify, dono ke regression tests pass. C15 ka price paya kar chuka hai: −80R net, causality ka honest cost.
Aapke bot ka "agar lookahead mila to 325R gir jayega" wala darra — wo darra purana tha, band ho chuka tha.
❌ Correction 2: "6 me se 6 params alag" — GALAT. 3 me se 3 alag.
Bot ne V18 padha aur SYMBOL_PARAMS chhoot diya. v18_params.py:
V18 = {  "sl_buf_atr": 0.25, "ext_stop_r": 1.5, "mode": "b2_vs_flip_chop",
        "cooldown_bars": 20, "max_consecutive_losses": 5 }        ← yeh BINANCE SPOT hai

SYMBOL_PARAMS["BTCUSDT_BYBIT"] = { "chop_thresh": 58.0, "cooldown_bars": 10,
        "sl_buf_atr": 0.01, "max_consecutive_losses": 3, ... }    ← yeh BYBIT hai
Backtest ka saara data Bybit ka hai. Toh live bot Bybit config chalata hai:
param	live (Bybit)	champion	 
sl_buf_atr	0.01	0.01	✅ same
chop_thresh	58.0	58.0	✅ same
max_consecutive_losses	3	3	✅ same
mode	b2_vs_flip_chop	atr_high	❌
cooldown_bars	10	8	❌
ext_stop_r	1.5	3.0	❌
6 me se 3 same hain. Research ka basis LIVE config hi hai — BP registry me chop 58 hai, Bybit se match karta hai. Ye deliberate design hai.
❌ Correction 3: "Live bot ka number UNKNOWN" — GALAT. Wo PINNED hai.
method/new bugs.md:642-653 — test_v18_causal_integrity.py::test_baseline, basis exactly mode=b2_vs_flip_chop, chop=58, cd=10, cl=3, slbuf=0.01 = live Bybit config:
351 trades | gross +211.72R | NET +137.33R | PF 1.907 | WR 27.6%
Yearly: 2023 +38.8 / 2024 +81.1 / 2025 +37.6 / 2026 +54.2  ← chaaron positive
Aapka live bot aaj +137.33R de raha hai, chaaron saal positive. Koi nahi jaanta nahi — golden test me pin hai.
Asli seedhi line (gross→net basis, signal/ANCHOR_BASIS_AUDIT.md:70):
live Bybit config (aaj) 351t  +137.33R   ← pinned, golden test
  + champion3 params          395t  +137.72R   ← bot ka "Arm A", verified nahi
  + exp_mltf + exp_persist     500t  +325.78R   ← CHAMPION
⚠️ v19 = 814-line nayi file, 4-line edit nahi. Pure copy. v18 untouched hai (comparison ke liye accha), par ab 2 engines hain — galat wala chala to chup-chaap production pe chala jayega.
🎯 Aur ek baat jo KISI ne nahi kahi
Dono ne bola "6 simultaneous positions = capital model chahiye." Wo overstated hai.
R = move / risk, jahan risk = SL distance se define hota hai — capital se nahi. Toh 6 concurrent positions ka matlab 6× equity nahi, balki 6× per-trade risk — jo 6% margin hai agar per-trade risk 1% hai.
+325.8R 6×-capital ka number NAHI hai. Ye scale-free hai. Live le sakte ho — jismein sirf Bybit ka concurrent-position margin limit aasman hai (BTCUSDT_BYBIT pe typically 5-10).
Asli capital concern alag hai, aur wo yeh hai: exp_mltf ek hi1h window me6 positions kholta hai, aur wo same direction me hote hain. 6 correlated positions = risk 6× nahi, concentration 6×. Ek adverse1h move saare 6 ko saath maarta hai. Ye real hai, aur kisi ne measure nahi kiya.
📋 Plan
Aapne bola tha "yeh investigate karna." Ho gaya. Ab teen options:
#	Kaam	Kyun	Cost
A	Correlated-cluster risk measure karo — champion ke 6-concurrent groups me ek adverse 1h move ka peak drawdown kya hai	Yehi ek cheez hai jo +325.8R / DD 17.8 number ko honest karti ya todti hai. Koi nahi measure kiya.	1 run, naya analysis
B	Cost model reconcile — engine "Costs 0.05%+2pt" likha hai, live config 0.055%/side + 5bp/10bp	Same nahi hai. Agar engine sasta cost maan raha hai to +137.33R bhi aur +325.8R bhi thoda upar hai	1 grep + arithmetic
C	v19 vs v18 ka byte-diff audit	814-line copy me galti se 1 extra line change to champion ka proof hi bekaar	5 min
Meri recommendation: C → B → A. C sabse sasta aur agar fail hua to baqi sab bekaar. B ek line ka kaam hai. A asli research hai.
Kaunsa chalaun? Ya saath me (C+B ek saath 10 min me).


---
longcat:
Investigation complete. Poora picture clear hai.
Seedha jawab: Champion REAL hai. Par live bot se match nahi karta.
Kya verify hua:
Claim	Verdict	Proof
500T/+325.8R real hai?	HAAN	v19_champion.py se reproduce hua — 500t/+325.78R IS, 279t/+70.15R OOS
busy_until exist karta hai?	HAAN	v18 line 567, 577, 743. Par exp_mltf=True me bypass
ATR me lookahead?	NAHI	Causal — trailing 14 bars, sirf _i tak
HTF GATE path me lookahead?	FIXED	C14 (45min) + C15 (60min) dono 2026-09-26 me fix ho chuke
Entry close vs next-open?	Minor	P90/P91 — backtest me farq nahi (close[i] = open[i+1])
HTF GATE path — stale flag hai:
method/reality of champion.md ne flag kiya tha, par method/new bugs.md line 601 kehta hai:
"ALL THREE NOW FIXED (re-verified 2026-09-26)"
- C14 (chop gate 45min lookahead) → FIXED
- C15 (window gate 60min lookahead) → FIXED
- L1 (open-window drop) → Note, no action
To doosra bot ka #1 recommendation stale hai. HTF gate path already clean hai.
🚨 Asli problem — ye hai:
 	Champion (backtest)	Live bot
Engine	v19 (exp_mltf + exp_persist as real code)	v18 (shipped)
Mode	atr_high	b2_vs_flip_chop
Positions	3-6 concurrent	1
ext_stop_r	3.0	1.5
sl_buf_atr	0.01	0.25
cooldown_bars	8	20
max_consecutive_losses	3	5
Champion multi-position book hai. Live bot single-position. Ye do alag systems hain.
Live bot ka config kabhi backtest nahi hua. Live bot ka real number koi nahi jaanta.
Sahi plan (doosre bot ke #1 ko replace karke):
#	Kaam	Kyun
1	Live bot ka actual config backtest karo — v18_params.py ke params, b2_vs_flip_chop mode	Yehi aapka real deployable number hai
2	Agar live config champion se bahut kam deta hai → decide: champion config live me port karo (engineering) ya live config accept karo	Multi-position ke liye capital model chahiye
3	HTF gate path — skip (already fixed)	Stale flag
Doosra bot ka #1 (HTF gate) waste hai. Asli sawaal: "live bot me kitna paisa hai?"
Meri recommendation:
Live bot ka config backtest karo. Yehi aapke "500T/325R real hai?" sawal ka seedha jawab hai. Agar live config +137R deta hai (jaisa P99 arm A ne dikhaya), to champion deployable nahi — par live bot profitable hai. Agar live config bhi +325R deta hai, to champion live me chal sakta hai.
Plan mode me hoon — run nahi kar sakta. Bolo to plan mode exit karke live config ka backtest chalaun?


---
nemo:
Now I have the complete picture from all 4 bots' investigation. Let me synthesize a clear plan.
SYNTHESIS: WHAT'S ACTUALLY TRUE
Question	Answer
Is 500T/+325.8R real?	YES — but it's a 3–6 concurrent position book (exp_mltf=True)
Does live bot run this?	NO — live bot is 1-position (live_loop.py places single market order)
Is there lookahead in ATR?	NO — verified clean by all 4 bots
Is there lookahead in HTF gate?	3 findings flagged in method/reality of champion.md — needs investigation
Entry timing issue?	Backtest: signal bar close. Live: next bar open (15 min gap). P90/P91 tested this.
busy_until exists?	YES (line 567, 577, 743) but bypassed in champion via exp_mltf=True
THE CORE PROBLEM
CHAMPION (backtest)          LIVE BOT (production)
├─ exp_mltf=True             ├─ Single position only
├─ 3–6 concurrent positions  ├─ busy_until ACTIVE
├─ busy_until BYPASSED       ├─ max_concurrent = 1
└─ +325.8R / +70.1R          └─ UNKNOWN (never measured at live config)
The champion is a real measurement of a system the live bot cannot execute.
PLAN: 3 PRIORITY STEPS
STEP 0 — PIN REPRODUCE (Hard Gate)
python exp_champion_true.py
Must print: PIN OK IS 500/+325.8 & OOS 279/+70.2  
If fails → STOP. Everything else is invalid.
STEP 1 — 4-ARM ABLATION (Single Run, Answers Your Core Questions)
Arm	Config	Question Answered
A	Shipped engine (no flags)	"Is as-shipped profitable?"
B	+ exp_persist=7	"Persist contribution?"
C	Champion (exp_mltf=True, persist=7)	"Reproduce 500/325.8?" (assert)
D	Champion + fixed busy_until guard	"Real deployable 1-pos number?" (P96: +137.7R/−13.3R)
All 4 cells × 2 lanes × 2 eras. Report: net R, n, PF, max_concurrent, fees/funding.
STEP 2 — ENTRY-FILL AUDIT (2-min print)
Print first 10 trades: entry_price, open[i], open[i+1], close[i], close[i]==open[i+1]?  
Decides: Is P90's "next-open" actually signal-bar-open (bug)? If yes, P90's +174.8R is stale.
STEP 3 — HTF GATE LOOKAHEAD INVESTIGATION (The 3 Findings)
From method/reality of champion.md line 25: "HTF GATE path me 3 findings hain. Wo alag jagah hai, maine abhi tak nahi kholi."
This is the highest risk — if lookahead exists here, champion R collapses.
DECISION MATRIX AFTER STEP 1
Outcome	Action
A ≈ C (serial ≈ champion)	Features not load-bearing → ship serial (A), no port needed
A ≪ C (gap > 50%)	Multi-position IS load-bearing → port exp_mltf + capital model
D OOS negative (−13.3R confirmed)	1-position book loses OOS → need architecture change, not just port
WHAT I NEED FROM YOU
1. Approve Step 0 → I run exp_champion_true.py (creates _craze_tmp.py, no repo changes)
2. If PIN OK → Approve Step 1 (4-arm ablation)
3. Priority order — HTF Gate (Step 3) or Ablation (Step 1) first?
- Ablation first (changes shipping decision immediately)
- HTF Gate first (if lookahead found, everything else void)
WHAT NOT TO DO (Per All 4 Bots)
- ❌ Don't port all 130 research flags — only exp_mltf + exp_persist if needed
- ❌ Don't assume live bot runs champion config (6 params differ)
- ❌ Don't re-run champion pin (HEAD clean, 6 commits, P79 prefix-invariance 100%)
Ready to start with Step 0? Or do you want HTF Gate investigation first?

---
mimo:
Verification — jo other bot ne bola, usme kya sahi hai / kya galat
✅ SAHI (source-verified, maine khud dekha)
Claim	Proof
Pin reproduce hua	commit d55a9e4; exp_v19_proof.py:27 asserts len==500 and abs(net-325.78)<0.5 + OOS script exp_v19_oos.py
busy_until champion me dead hai	test_experiments_craze.py:955 → if (not exp_mltf); registry:198 exp_mltf=True
P96 retraction sahi	exp_mltf=True deliberate hai — multi-position design hai, bug nahi
exp_persist = regime hysteresis	test_experiments_craze.py:935-941 — _rg_c>=7 par switch. Position count nahi
v19 = v18 + 2 features	diff: hysteresis block + busy_until gate/assignment hata diye. Baaki sab comment hai
❌ GALAT / UNVERIFIED (4 cheezein)
1. "Live bot ke 6/6 params alag hain" — GALAT (3 alag hain, 6 nahi).
Other bot ne V18 spot base ya verify_parity.py ke hardcoded args compare kiye. Live asal me live_loop.py:85 → get_v18_params(v18_instrument) use karta hai. BTCUSDT_BYBIT par:
param	live (Bybit)	champion
sl_buf_atr	0.01	0.01
chop_thresh	58.0	58.0
max_consecutive_losses	3	3
mode	b2_vs_flip_chop	atr_high
ext_stop_r	1.5	3.0
cooldown_bars	10	8
Nahi: live_loop.py:1396 fine_ltf=[] pass karta hai (coarse 15m fill), backtest fine_ltf=d["fine"] (1m fill) → 4th difference.
2. "P91 proves next-open fill" — ARM HI GALAT HAI (aur kisi ne pakda nahi).
- v18:730 → entry_ts = candles_ltf[i]["ts"] = signal bar ka START
- exp_entry_fill.py:125,130 → j = bisect_left(ts, entry_ts) = i, px = op[j] = signal bar ka OPEN
- v18:585 → shipped entry = candles_ltf[i]["close"]
Matlab P90/P91 ka "next 15m open" arm signal bar ke OPEN par bhara gaya = ek bar PEHLE (signal ke 15 min pehle). Yeh anti-causal hai. P91 ne number retract kiya par wajah "denominator" batayi — yeh wajah check hi nahi hui.
Asal "next open" = open[i+1] = close[i] (contiguous candles) → test trivially zero hota. Toh aapka next-open idea kabhi sahi test hua hi nahi, aur code already wahi kar raha hai.
3. "HTF gate me lookahead, koi nahi khola" — PHELE SE KHULA HUA HAI.
method/new bugs.md:17-29: C12 / C14 / C15 sab FIXED, conclusion = "no backtest lookahead bug remains." Aur 7292a14 (P101) ne v19 me dobara source-verify kiya + ek residual measure kiya (C14-narrow: 500→503t, +1.4R). Yeh "naya #1" already closed hai.
4. nemotron ke 2 claim galat (method/reality of champion.md:171,179): verify_parity.py 500/325.8 nahi deta (spot params → 356t/+277.1R gross, method/CHAMPION_FLOOR_REJECTED.md:44-46); aur exp_* flags v7_timecap.py me nahi, harness patch me hain.
5. Side note: v19 file mojibake hai (—→â€”, ×→Ã—, →→â†’) — galat encoding se copy hui. Comments/docstrings me hai, logic ko chhua nahi, par file dobara UTF-8 se banani chahiye. Aur "4 lines" claim loose hai: ~12 functional + 76 comment lines.
🎯 ASLI KHULA SAWAAL — kisi ne abhi tak nahi chalaya
backtest champion = v18 + exp_mltf + exp_persist + mode=atr_high/ext=3.0/cd=8  → +325.8R / +70.1R
arm A             = champion params, flags hataye                              → +137.7R / −13.3R
LIVE BOT          = v18 + get_v18_params(symbol) + fine_ltf=[] + single-position → ??? UNKNOWN
Arm A live config nahi hai (mode/ext/cooldown alag). "Mere live bot me kitna paisa hai" — woh number repo me hai hi nahi. Aur port karne par bhi gap close nahi hota: live_loop.py:1778-1801 apna single-position in_trade guard chalata hai → v19 ka 6-deep book live me tab bhi nahi banega.
PLAN (priority order, har ek ka falsifier)
Run 1 — LIVE-CONFIG BACKTEST (sabse pehle, yehi missing number hai)
- Engine: v18_streak_halt.py as-is, params exactly get_v18_params(<live symbol>) + V18_ENGINE, fine_ltf=[] (jaise live_loop.py:1394-1403 pass karta hai)
- 2 arms: (a) shipped v18 = aaj ka live bot · (b) v19 (champion features) + live params
- Report: n, net, PF, maxconc × 4 cells (2 lanes × IS/OOS)
- Falsifier: (a) ka IS net ≤ 0 ya OOS ≤ 0 → shipping decision badal jaata hai, baaki sab irrelevant
- Prereq: --symbol confirm karo (BTCUSDT ya BTCUSDT_BYBIT) — live params uspar depend karti hain
Run 2 — ENTRY-FILL TRUTH (aapka next-open sawaal + P90/P91 dono settle)
- Print all trades: close[i], open[i], open[i+1], close[i]==open[i+1]?
- Phir P90 arm dobara chalao px = op[j+1] (asal next open) vs P90 ka op[j]
- Falsifier: close[i]==open[i+1] hamesha true → P90/P91 dono ke arm ek bar early the, dono docs correct karne hain, aur next-open test trivially 0 hai (matlab aapka idea implement hi hai)
Run 3 — LIVE/BACKTEST SLOT PARITY
- v19 (6-deep) vs live ka in_trade guard → count karo live kitne trades refuse karta ("in-trade"/stale_skip), report dNet
- Falsifier: |dNet| < 193.4R → concurrency live ke liye matter nahi karti; ≥ 193.4R → exp_mltf port akele kaafi nahi, live_loop ka guard + capital model bhi chahiye
Chores (bina run): v19 dobara UTF-8 se banao · method/reality of champion.md ke nemotron block + "6/6 params" claim correct karo · P99 arm A ka label "production-as-is" → "as-shipped champion config (NOT live)".
Order: Run 1 → Run 2 → Run 3. HTF-gate audit already done (P101), usse aage mat badho.
Do cheezein chahiye plan lock karne ke liye:
1. Live bot ka --symbol kya hai — BTCUSDT ya BTCUSDT_BYBIT? (live params isi par depend karti hain)
2. Plan mode exit karke Run 1 chalau? (exp_* ke bina, sirf print + data cache read — production file nahi badalti)


---
spance:
I have what I need. Let me lay out the plan.
What I verified
The other bot's central claim is right, and I confirm it independently:
v19_champion.py is a genuine copy of v18_streak_halt.py (782 → 814 lines) with exactly two behavioural changes hard-coded: busy_until never set/checked (line 598), and regime hysteresis PERSIST=7 (lines 525–533). The C14/C15 gates are present at 6 + 2 sites. So "same engine, two flags" is accurate — my earlier concern was overstated and I retract it.
But the proof is not reproducible, and this matters
exp_v19_proof.py:11 and exp_v19_oos.py:15 both read backtest/tests/_v19_src.py. That file does not exist and has never been committed (git log --all -- "*_v19_src.py" → empty).
So the two harnesses that produced "V19: 500t/+325.78R" and "OOS 279t/+70.15R" cannot be re-run by anyone, including the other bot. Those numbers are unverifiable assertions right now.
And there is a real risk they are wrong. The committed v19_champion.py may not be what was tested. Two specific concerns:
1. The docstring is corrupted. Line 17 of the file reads """"""v11_conditional_htf... — six consecutive quote characters. The v19 header docstring was prepended without closing it. This file has never been through a syntax check by anything that would have caught it, because the proof never imported it.
2. Encoding damage is visible throughout (A��,��??, â€? in the regime comments). Cosmetic for execution, but it means the file was written by a tool that mangled non-ASCII.
The honest position: "v19 reproduces the pin" is plausible and probably true, but it is currently unproven, and the artefact that would prove it was never committed.
One substantive finding the other bot's framing obscures
It says arm A is "an artificial build, not a real strategy." That's wrong, and it's the same class of error the round has been retracting all week.
exp_shipped_direct.py calls v18_streak_halt.simulate_htf_ltf_streak_halt directly, no harness, with champion params minus the three harness-only kwargs. Result: 395t / +137.7R, maxconc 1 — identical to the harness arm A.
That is production code producing a deployable number. Not artificial. Arm A is "the champion strategy, run on the shipped engine, without multi-position." That is a real, tradeable, one-position book.
And the comparison that actually matters:
Book	OOS	maxconc	live-executable today?
Arm A (shipped, serial)	−13.3R	1	yes, as-is
Arm B (+persist=7)	−1.8R	1	yes, after porting 7 lines
Arm C (champion)	+70.1R	6	no — needs multi-position + capital model
Both single-position books are negative out of sample. So exp_mltf isn't a nice-to-have; it is the only thing carrying OOS. That is a much sharper statement than "features daalne hain" — it means the profitable version cannot be run by the current live bot, and the version the live bot can run loses money OOS.
Plan
Step 1 — make the proof real (blocks everything else).
Commit backtest/tests/_v19_src.py, or better: rewrite both proof harnesses to import v19_champion.py directly as a module — the same way exp_shipped_direct.py already does for v18. Then fix the six-quote docstring, run python -m py_compile, and re-run IS + OOS.
Falsifier: if the committed v19 does not print 500t/+325.78R and 279t/+70.15R, the port is wrong and the whole "4 lines" claim collapses. This is one command and it settles it.
Step 2 — reconcile the two P99 framings in the docs. Arm A must be described as a real production book that is OOS-negative, not an "artificial build." Right now method/CHAMPION_DEPLOYABILITY_P99.md says the opposite, and that will mislead the next round.
Step 3 — the question that actually decides shipping. Not "port the flags." It's:
Arm A is OOS −13.3R. Arm B is OOS −1.8R. Arm C is OOS +70.1R but needs 6 concurrent positions and a capital model that does not exist.
So the decision is: build the multi-position capital model, or accept that the only live-runnable version of this strategy loses money out of sample. That is a risk decision for you, not a backtest result — same framing P84 used. But it has to be stated plainly, because right now the repo contains two books that are OOS-negative and one that isn't deployable, and no document says so in one place.
Step 4 — only then, the HTF gate audit P101 already did (champion is clean; the one residual is a measured +1.4R). I'd treat P101 as done rather than reopening it.
Two things I want your call on before I proceed:
1. Do you want me to run Step 1? It's read-only in effect (compile + import + one sim run) but it does write a harness file, so I need plan mode lifted. It's the single highest-value thing outstanding — everything else is downstream of whether v19 is real.
2. On Step 3 — do you want the multi-position capital model built, or is the OOS-negative single-position result a signal to stop here? I'd want your read before spending effort there, because if the answer is "stop," Steps 1–2 are just documentation hygiene and I should say so rather than build toward a deployable +70R.