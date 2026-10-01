Nemotron 3 :
Research Proposals
P1. Swing-Label Redesign: P1/P2 Wave Notation + ZigZag Hybrid
THESIS: Replacing the B1/B2/FLIP/FS mark set with a P1/P2 Elliott-style wave labelling (impulse/corrective) plus a ZigZag filter on swing extremes will produce a differently-conditioned trigger set that separates winners from losers at the structure level, not the trade level.  
MECHANISM: The current marks (B1/B2/FLIP) describe breaks, not wave role. A P1/P2 labelling forces every swing into an impulse or corrective role, which is a structural property knowable at FS. The graveyard shows per-trade entry filters are exhausted because they measure calendar/regime, not structure. Changing the alphabet the engine sees changes the trade population before any filter.  
NEW DATA: None needed — uses existing 15m swings (data["c15"], sw15 from btc_swing.compute_btc_swings). The swing chain already has seg.dir, breaks, fs_at_idx, kind (FS/SUS), source (chop/sustain). We only need a relabelling pass.  
FALSIFIER: After relabelling, the new mark set yields ≤ 51% of trades with positive trimmed-mean R in both eras, or the new trigger set's ex-best-5 is negative in either era.  
HIT BAR: New trigger set (same engine, new marks) must beat champion IS net +325.8R and OOS net +70.2R on trimmed mean, with same-sign in both eras, ex-best-5 ≥ 0 in both.  
MY CONFIDENCE: HIGH — This is the only proposal that changes the information set (what the system sees) rather than filtering an exhausted set. The prompt author called it their "strongest suggestion." The swing chain already carries all raw pivots; we are only reinterpreting them.
P2. FS-Only Book with Swing-Trail Exits (Not Fixed Target)
THESIS: The FS-only engine tested so far used a fixed 3R target; the champion book uses trailing="swing". FS entries with swing-trail exits will capture the full trend move on the 2,586 never-priced swings, producing a larger book with the same per-trade quality.  
MECHANISM: exp_fs_only_engine.py tested only target_r ∈ {2.0, 3.0} with trailing="off". The champion's edge comes from trailing="swing" + exp_trail_half=1 + exp_trail_delay_r=1.0 — it lets winners run. FS entries are structurally the swing's completion; trailing the subsequent confirmed pivots is the logical exit. The graveyard shows "exit when swing looks bad" fails, but swing-trail is not a discretionary exit — it's a mechanical ratchet on confirmed structure.  
NEW DATA: None — uses existing 15m swings and 1m fine data for exit precision. The exp_fs_only_engine.py harness already enumerates the 2,586 never-priced FS signals.  
FALSIFIER: FS-only with swing-trail has negative trimmed mean in either era, or ex-best-5 < 0 in either era, or net R < champion/2 in IS.  
HIT BAR: IS net ≥ +160R (≈50% of champion), OOS net ≥ +35R, both eras same sign, ex-best-5 ≥ 0 both eras, trimmed mean > 0 both eras.  
MY CONFIDENCE: HIGH — The FS cohort (314/179 swings) was already profitable with fixed target. Swing-trail is the champion's proven exit mechanism. The population is 10× larger. Only risk: the never-priced swings are "harder" (no B2/flip confirmation), but FS is the confirmation.
P3. Multi-Swing HTF Bias Confirmation (2-of-3 Rule)
THESIS: Requiring 2 consecutive same-direction 1h swings before opening a bias window will filter chop regimes where the 1h bias flips rapidly, reducing false bias windows without losing true trend windows.  
MECHANISM: The current 1h bias window opens on every 1h swing confirmation. In chop, 1h swings alternate rapidly, creating bias windows in both directions that the 15m layer trades into. A 2-of-3 rule (two of last three 1h swings same direction) is a structural regime filter — it operates on the HTF swing chain, not on per-trade features. The graveyard shows regime/chop filters failed because they were applied at the 15m trade level; this applies at the 1h bias generation level, changing which windows exist.  
NEW DATA: None — uses existing 1h swings (sw10 from data["c1h"]). The bias timeline (bias_timeline in btc_engine.py) is already built from 1h swing confirmations.  
FALSIFIER: The 2-of-3 rule reduces trade count by > 40% without improving trimmed mean, or net R drops in either era.  
HIT BAR: IS net ≥ +300R, OOS net ≥ +65R, trade count ≥ 300 (IS), same sign both eras, ex-best-3 ≥ 0 both eras.  
MY CONFIDENCE: MEDIUM-HIGH — This is a structural change to the HTF bias layer, not a trade filter. The 1h swing chain is the least-explored degree of freedom (4h was tested and closed, but 1h bias generation was not).
P4. Swing Geometry Filter at Bias Window Open
THESIS: Only open a 1h bias window when the confirming swing exhibits "clean" geometry: (a) swing magnitude ≥ 1.5× ATR, (b) duration 10–60 bars, (c) no internal chop crosses (single-source confirmation).  
MECHANISM: The graveyard shows "regime/chop/wick/swing-churn filters" failed at the 15m trade level. But the 1h swing itself carries geometry knowable at its confirmation instant — magnitude, duration, confirmation source (chop vs sustain), internal structure. Filtering which 1h swings generate bias windows is a different intervention than filtering 15m trades. It changes the bias timeline before the 15m layer sees it.  
NEW DATA: None — all swing geometry is in sw10 dicts: seg.start_px, seg.end_px, seg.start_idx, seg.end_idx, confirm_source, fs_at_idx, breaks.  
FALSIFIER: The filtered bias timeline produces < 200 trades IS, or net R < champion in either era, or the filter removes > 50% of the 17 ≥ +10R trades.  
HIT BAR: IS net ≥ +300R, OOS net ≥ +65R, trade count 250–400 IS, retains ≥ 12 of the 17 ≥ +10R trades, same sign both eras.  
MY CONFIDENCE: MEDIUM — The geometry features are causal (known at swing confirmation). Risk: the "chop" swings that confirm via sustain may be the ones that lead to trends; need to test chop vs sustain separately.
P5. Position Resize Engine (Simulated via Cohort Lifecycle)
THESIS: When a new 15m signal fires while a position is open, instead of ignoring it (current) or adding a new position (pyramid, closed), resize the existing position toward the new signal's direction using a fixed fraction (e.g., 0.5× current size).  
MECHANISM: The graveyard closed "pyramid/scale-in" and "revenge re-entry" as separate positions. But the engine currently has exp_mltf=True which allows concurrent 1m entries while a position is open — it already has multi-position state, just no sizing logic. A resize policy (reduce/flip/increase) is a position lifecycle decision, not a new entry. It can be simulated by tracking a single position with variable size, applying the champion's stop/trail logic to the blended entry. This needs no new data, only a simulation harness.  
NEW DATA: None — uses existing signals and 1m fine data. The v18_streak_halt.py engine has no size channel, but a simulation can compute blended entry/exit R for a resized position.  
FALSIFIER: Any resize policy (reduce/flip/increase on new signal) fails to beat static 1.0 size on trimmed mean in both eras, or increases maxDD > 1.5×.  
HIT BAR: At least one resize policy beats static size on trimmed mean in both eras, with maxDD ≤ 1.2× champion, ex-best-5 ≥ 0 both eras.  
MY CONFIDENCE: MEDIUM — This is engineering-heavy (needs a simulation harness) but attacks the only untouched lever: sizing with a live execution channel. The graveyard shows static sizing failed; the engine already supports concurrent entries via exp_mltf.
P6. Scheduled-Event Bias Override (Not Gate)
THESIS: Instead of gating trades off during scheduled events (tested and closed), override the 1h bias direction for a fixed window around high-impact events (FOMC, CPI, Employment) using the event's historical directional bias.  
MECHANISM: exp_event_pathtrue.py tested event-driven trades (enter at event, exit at fixed window) and they failed the kill table. But the event data (data/scheduled_events/official_us_events_2021_2026.json) has 382 exact-UTC events with known_in_advance=true. The champion system has a 1h bias window that directs 15m trades. Overriding the bias direction for ±4h around FOMC/CPI (where historical drift exists) changes the 15m trade population without adding/removing trades — it flips direction on existing signals. This is a bias-layer intervention, not a trade filter.  
NEW DATA: Exists on disk — data/scheduled_events/official_us_events_2021_2026.json (382 events, exact UTC, known_in_advance). The Fed speech archive exists but lacks exact times (excluded).  
FALSIFIER: Bias override on FOMC/CPI/Employment ±4h reduces net R in either era, or flips < 10% of trades in the window.  
HIT BAR: IS net ≥ +330R, OOS net ≥ +75R, same sign both eras, ≥ 15% of trades in event windows have flipped direction, ex-best-3 ≥ 0 both eras.  
MY CONFIDENCE: MEDIUM-LOW — Event-driven trades failed, but bias override is untested. The event data is high-quality (official schedules, exact UTC). Risk: the drift may not persist in the IS era (2023-2026).
P7. 30m Intermediate Timeframe (Built from 15m)
THESIS: Construct 30m bars by merging pairs of 15m bars, compute 30m swings, and use 30m swing breaks as the entry trigger (replacing 15m) while keeping 1h bias and 1m exits.  
MECHANISM: The graveyard closed 4h (too slow) and 5m (too noisy, 1m arithmetic). 30m is the only intermediate timeframe not tested. 30m swings will have fewer, cleaner breaks than 15m (lower frequency, higher magnitude), potentially reducing the trade count while keeping the trend-capture property. The barrier: bar-counted parameters (cooldown=8, max_losses=3, etc.) must be re-scaled to duration (e.g., cooldown=4h, not 8 bars). This is a re-parameterisation, not a flag flip.  
NEW DATA: 15m bars exist (data/bybit/15m). 30m bars must be synthesized (merge pairs: O=first.open, H=max, L=min, C=last.close, V=sum). No refetch needed.  
FALSIFIER: 30m swing count < 50% of 15m, or net R < 0 in either era, or the re-parameterised params cannot be set to match 15m trade frequency.  
HIT BAR: IS net ≥ +250R, OOS net ≥ +50R, trade count 200–350 IS, same sign both eras, ex-best-5 ≥ 0 both eras.  
MY CONFIDENCE: LOW-MEDIUM — Genuinely new timeframe, but inherits the bar-counted parameter problem. The prompt notes this explicitly. Only worth doing if the parameter re-scaling is pre-registered and tested as a duration-based system.
P8. Swing-Chain Cross-Asset Correlation as Regime Filter
THESIS: The cross-asset sweep showed 7/13 alts positive both eras with mean pairwise correlation +0.072 IS / −0.053 OOS. Use the real-time correlation of BTC's 1h swing R with the alt sleeve's 1h swing R as a regime filter: only open bias windows when the sleeve is in drawdown (negative correlation regime).  
MECHANISM: The alt transfer was screened retrospectively (13→7→6 funnel). But the correlation structure is a market property: when BTC trends, alts often don't (and vice versa). The 1h swing R series for BTC and the alt sleeve can be computed in real-time (1h lag). Using the sleeve's rolling 20-swing correlation with BTC as a bias-gate is a portfolio-level regime signal, not a single-asset trade filter. It uses the diversification insight (1.25–1.79× DD vs 6×) as a live signal.  
NEW DATA: data/scan-fut/ has 16 alts with 15m/1h data. Need to compute 1h swings for each alt (same btc_swing engine) and their R series. This is compute, not new fetch.  
FALSIFIER: The rolling correlation has < 0.2 magnitude in both eras, or gating on it reduces net R in either era.  
HIT BAR: IS net ≥ +300R, OOS net ≥ +65R, trade count ≥ 250 IS, same sign both eras, correlation gate active ≤ 30% of time.  
MY CONFIDENCE: LOW — The alt data exists but the correlation signal is noisy at 1h swing frequency. The retrospective screen (13→7→6) contaminates the sleeve selection. Would need forward data to validate.
P9. 1m Swing Structure as Setup Filter (Not Trigger)
THESIS: Compute 1m swings (already proven feasible: 90k swings in 18s, 177 MB peak) and use 1m swing geometry at the 15m entry bar as a setup filter — only take the 15m B2/FLIP if the 1m swing structure agrees (e.g., 1m swing direction = 15m signal direction, 1m swing magnitude > threshold).  
MECHANISM: The graveyard closed 1m as trigger (0/196 cells, cost arithmetic). But 1m swing structure at the 15m entry instant is a different information set: it describes the micro-trend leading into the break. The 1m swing engine (firstswing.SwingEngine) runs on 1m candles and produces B1/B2/FLIP/FS at 1m resolution. Using it as a confluence filter (not a trigger) avoids the 0.79R/RT cost because trades still execute on 15m bars.  
NEW DATA: 1m candles exist (data["fine"], 1.95M bars). 1m swings are NOT computed anywhere in the repo — this is the compute step. phase0_1m_swing_diag.py proves it's feasible (18.5s, 177 MB).  
FALSIFIER: No 1m geometry filter (direction agreement, magnitude, FS proximity) improves trimmed mean in both eras, or the filter removes > 50% of the ≥ +10R trades.  
HIT BAR: IS net ≥ +330R, OOS net ≥ +72R, trade count ≥ 350 IS, retains ≥ 12 of 17 ≥ +10R trades, same sign both eras.  
MY CONFIDENCE: LOW-MEDIUM — The 1m trigger family is dead (arithmetic). But 1m structure as filter is untested. The compute is solved; the question is whether 1m swing direction at 15m entry adds information.
P10. Time-Weighted Stop Buffer (Vol-Adaptive sl_buf_atr)
THESIS: Replace the fixed sl_buf_atr=0.01 with a time-weighted buffer: sl_buf_atr = 0.01 × (1 + hours_since_swing_start / 24), widening the stop as the swing ages to avoid noise stops on mature swings.  
MECHANISM: The graveyard shows stop has been attacked from both directions (tighter/wider) and every variant loses. But all variants were static. The swing-pivot stop's risk denominator grows as price moves away from the pivot (entry-to-SL distance increases with swing age). A time-weighted buffer keeps the initial risk constant in R-terms by widening the buffer as the swing extends. This is a risk-normalisation fix, not a stop-tightening/widening. The confound in FS_ENTRY_RISK_CONTROL.md (comparing across buckets without constant denominator) suggests this could matter.  
NEW DATA: None — hours_since_swing_start is computable at entry from sig["swing_no"] and the swing's start_time (in swing dict).  
FALSIFIER: Any time-weighted formula fails to beat fixed 0.01 on trimmed mean in both eras, or increases maxDD.  
HIT BAR: IS net ≥ +330R, OOS net ≥ +72R, maxDD ≤ 27.7 (champion IS), same sign both eras, ex-best-5 ≥ 0 both eras.  
MY CONFIDENCE: LOW — The stop is the most thoroughly attacked component (60+ variants). But none were time-adaptive. This addresses the risk-denominator confound directly.
Ranked by Confidence
Rank	Proposal	Confidence
1	P1: Swing-Label Redesign (P1/P2 + ZigZag)	HIGH
2	P2: FS-Only with Swing-Trail	HIGH
3	P3: Multi-Swing HTF Bias (2-of-3)	MEDIUM-HIGH
4	P4: Swing Geometry at Bias Open	MEDIUM
5	P5: Position Resize Engine	MEDIUM
6	P6: Scheduled-Event Bias Override	MEDIUM-LOW
7	P7: 30m Intermediate Timeframe	LOW-MEDIUM
8	P9: 1m Swing Structure as Setup Filter	LOW-MEDIUM
9	P8: Cross-Asset Correlation Regime Filter	LOW
10	P10: Time-Weighted Stop Buffer	LOW
Which to Run First & What I Need
Run P1 first (Swing-Label Redesign). It is the only proposal that changes the alphabet the system sees, and the prompt author explicitly called it their "strongest suggestion." It requires no new data, no new timeframes, no new infrastructure — only a relabelling pass on the existing swing chain.
What I need from you:
1. Confirmation on the label set — Should I implement P1/P2 (impulse/corrective) only, or P1/P2/P3/P4/P5 (full Elliott), or ZigZag-filtered extremes as a separate mark layer? The prompt mentions "P1/P2 wave labelling, or a ZigZag + Elliott hybrid" — which variant do you want first?
2. FS definition for the new labels — In the current system, fs_at_idx is the opposing pivot-break that completes the swing. In a P1/P2 system, the "FS equivalent" for a corrective wave (P2) would be the end of the correction (start of next impulse). Need your rule for this.
3. Whether to keep B1/B2/FLIP as a parallel mark set — For ablation: run the engine with only new marks, only old marks, and both to isolate the effect.
Once you confirm the label specification, I'll build the in-memory patch (following exp_b1_entry.py pattern: rebuild btc_swing.py → relabel swings → feed to engine) and run the pre-registered 4-cell sweep (IS/OOS × champion/utcsat) with control asserts.

---
Link 3.0 
Now I have full context on the data, graveyard, and state of play. Here are my proposals as the second researcher.
PROPOSALS FOR A SECOND RESEARCHER
Context summary
Read all four primary docs, verified the data inventory on disk, and checked the 31-row graveyard. Key facts constraining everything: per-trade entry features are exhaustively closed (swing_no = calendar time, AUC collapses 0.83→0.62), the 1m layer is dead by arithmetic (0.79R cost), the stop is dead in both directions, sizing is dead (look-ahead retracted), and max_consecutive_losses=3 is a genuine optimum. The system sees ONLY OHLCV. The repo has four untouched data dimensions sitting in data/flow/ that have never been fed to the engine: L2 order-book snapshots, funding rates, futures premium, and derived metrics.
P1. Structural Decomposition Redesign — Different Wave Labels
THESIS: Change what the system SEES by relabeling the same price structure with a different wave notation (P1/P2 or ZigZag+Elliott), not filtering trades.
MECHANISM: The closed list is entirely about filters on the CURRENT four marks (B1/B2/FLIP/FS). Nobody has asked whether a different structural decomposition produces a better-conditioned trigger set. The current marks may be a suboptimal basis for the swing logic — like using the wrong coordinate system. This changes the input representation, not the decision function.
NEW DATA: None beyond what's on disk. Reprocess existing 15m OHLCV with an alternative peak/trough algorithm.
FALSIFIER: Any wave labelling that produces a net R below the reference ledger (500/+325.8, 454/+358.9) on both eras, or that requires forward-looking data in its construction.
HIT BAR: Same-sign in both eras on both lanes; trimmed mean positive; ex-best-5 positive; control asserts exact reference. Pre-registered: 3 wave-labelling schemes × 2 engines = 6 cells minimum.
MY CONFIDENCE: high — this is explicitly called the "strongest suggestion" by the prompt author, and it attacks the problem from a direction (representation, not filtering) that the graveyard does not cover.
P2. Funding Rate as a Regime Feature at the 1h Bias Layer
THESIS: Use the funding rate series — which exists in data/flow/funding/ from 2020-01 as monthly CSVs — as a regime signal at the 1h HTF bias layer, not as a per-trade filter.
MECHANISM: Funding rate encodes the aggregate positioning of leveraged traders. The system currently decides bias on 1h price structure alone. A persistent negative funding rate means shorts are paying longs — a different regime than persistent positive funding. This is not a per-trade entry feature (which is closed); it's a regime-level bias modifier that changes the direction of the 1h window before the 15m entry even fires. The funding data covers 2020-01→2026-08, spanning both eras fully.
NEW DATA: data/flow/funding/BTCUSDT-fundingRate-YYYY-MM.zip, 80 monthly files. Need to aggregate to 1h resolution. Does the funding series already exist at 1h resolution anywhere? If not, it needs resampling from monthly — which is coarse but sufficient for a bias-level regime signal.
FALSIFIER: Funding-rate-regime books show no same-sign improvement over the reference on both lanes; or the funding signal is redundant with a price-derived regime measure already implicit in chop_thresh.
HIT BAR: Same sign in both eras on both lanes. Pre-registered: 2 regimes (positive-dominant vs negative-dominant funding) × 2 lanes = 4 cells. Must assert the control ledgers first.
MY CONFIDENCE: medium — funding rate is genuinely new information, but it's a slow-moving series. The risk is that it's just proxying for trend, which the system already captures via swing structure. The check is whether it adds anything conditional on the current swing state.
P3. L2 Order-Book Depth as a Structural Coherence Signal
THESIS: Use the L2 book-depth snapshots in data/flow/bookDepth/ (2023-01→2026-09, daily) to measure structural coherence of the 1h swing environment — not to trigger trades, but to weight or gate the 1h bias window.
MECHANISM: The book-depth data starts 2023-01, exactly matching IS. A swing leg that forms while the order book is thin (low depth) vs thick (high depth) may represent fundamentally different market microstructure. Thick books produce cleaner swings; thin books produce noise that the current swing algorithm may misidentify. This is not a per-trade filter — it's a swing-quality pre-condition applied before the swing is even confirmed. The key question: does swing structural integrity correlate with book depth?
NEW DATA: data/flow/bookDepth/BTCUSDT-bookDepth-YYYY-MM-DD.zip, ~1361 daily files. Requires computing a depth metric per bar and aggregating to the 1h swing timeframe. This needs engineering (the data is daily, the engine runs on 1h/15m/1m).
FALSIFIER: Depth-weighted swings produce no same-sign improvement over the reference; or the depth metric is computable only retrospectively (violating the causality rule).
HIT BAR: Same sign both eras, both lanes. Trimmed mean positive. Ex-best-5 positive. Pre-registered: depth-quartile gates on swing confirmation, minimum 2 cells.
MY CONFIDENCE: low-medium — the daily granularity is a serious mismatch with the 1h engine. The data might not resolve at the right scale. Also, the book-depth zips may contain raw order book snapshots that need significant processing. But this is the most genuinely new information channel available.
P4. Futures Basis/Premium as a Trend-Strength Modulator
THESIS: The data/flow/premium1h/ directory contains hourly futures premium data (2020-01→2026-08). Use the basis between spot and perpetual futures as a trend-strength modulator at the 1h bias layer.
MECHANISM: When the futures premium is strongly positive, the market is in a leveraged-long regime; when negative, short-dominant. This is fundamentally different from price-derived regime measures because it encodes the cost of carry — what the marginal trader is willing to pay to hold leveraged exposure. A trend system that fires long during persistent positive premium is operating in a different market than one firing long during flat/negative premium. This is a bias-gate, not a per-trade filter.
NEW DATA: data/flow/premium1h/BTCUSDT-1h-YYYY-MM.zip, 80 monthly files. Already at 1h resolution — no resampling needed.
FALSIFIER: Premium-regime books fail same-sign on both lanes. Or the premium signal merely proxies for trend direction already captured by the swing structure.
HIT BAR: Same sign both eras, both lanes. Pre-registered: premium-signal regime split × 2 lanes = 4 cells minimum. Control asserts reference ledgers.
MY CONFIDENCE: medium — the premium is at the right timescale (1h) and covers the right period. The risk is redundancy with price-derived measures. The falsifier above is designed to catch that.
P5. Forward Data as the Sole Validation Path for Any New Direction
THESIS: Before running ANY of the above proposals on the mined data, validate the pipeline and candidate on data/forward/bybit/ (2026-09-13→present, never touched). This is the only non-retrospective data in the repo.
MECHANISM: The RETROSPECTIVE_AND_FORWARD.md documents the problem: the IS/OOS slices are the most-inspected data in the repo. The portfolio numbers are survivorship-selected. data/forward has accrued ~15 days / ~60-70 trades with zero runs. FORWARD_TEST_PLAN.md pre-registers the protocol: CHAMPION_N3 and CHAMPION_BASE as candidates, R1 parity, R2 edge survival (net R>0, R/trade>0.20, PF>1.20), R3 no degradation, R4 drawdown containment, n>=50 provisional, n>=150 verdict.
NEW DATA: data/forward/bybit/ — 1203×15m, 301×1h, 18049×1m bars from 2026-09-13. Already on disk, never used.
FALSIFIER: Forward net R ≤ 0, or PF ≤ 1.20, or n < 50 before verdict. Also: forward parity failure (R1) voids the test.
HIT BAR: Pre-registered in FORWARD_TEST_PLAN.md. R2 requires net R > 0 AND R/trade > 0.20 AND PF > 1.20 on accumulated forward data. n >= 150 for a real verdict.
MY CONFIDENCE: high — this is the single most important methodological action. It's not a research direction per se, but it's the validation gate that every other proposal must pass through. At ~12 trades/month at current rates, n=150 needs ~12.5 months. Worth starting now.
P6. Cross-Asset Breadth as a BTC Regime Signal
THESIS: Use the 16 alt coins in data/scan-fut/ to compute a breadth indicator (fraction of alts in uptrend) as a regime signal at the 1h BTC bias layer. NOT "cross-sectional alt rotation" (closed) — a breadth indicator for BTC only.
MECHANISM: The closed list killed "cross-sectional alt rotation" (rotating capital among alts). This is conceptually different: instead of rotating, we read the alt market's aggregate health as a regime signal for BTC. When 12/16 alts are in confirmed uptrends on 1h, the BTC regime is "risk-on alt season"; when 2/16, it's "risk-off." The breadth indicator is computed from data that exists on disk and covers the IS/OOS period. This changes the bias layer input, not the trade-level decision.
NEW DATA: data/scan-fut/ — 16 alt coins × 15m/1h. Need to compute a trend state per alt per bar, then aggregate to a breadth ratio.
FALSIFIER: Breadth-regime books fail same-sign on both lanes. Or breadth is redundant with the existing chop_thresh / regime channel.
HIT BAR: Same sign both eras, both lanes. Pre-registered: breadth-quintile gates × 2 lanes = 10 cells minimum. Must assert controls first.
MY CONFIDENCE: low-medium — this is close to the closed "cross-sectional alt rotation" direction, and the prompt author explicitly warns against it. The distinction (indicator vs rotation) is subtle and might not survive scrutiny. The data is also heavy (33 CSV files × 2 timeframes).
P7. The B1 Entry — Properly Engineered with In-Memory Patching
THESIS: The B1 mark exists in the swing structure but no kwarg fires the entry on it. Engineer a proper B1-triggered engine using the in-memory patching pattern (exp_b1_entry.py) and run it with exact controls.
MECHANISM: The closed list lists B1 as "still open (not closed)" and notes that exp_b1_b2_mode is a blocking filter on the B2 trigger, not a different trigger. The previous B1 attempt failed catastrophically (IS 221t −34.9R, WR 27.8%→17.2%). But that attempt used the wrong engineering approach. The prompt says "Needs a signal-selection patch plus a full path-true run." This is the one direction explicitly listed as open and unknown. If B1 entry can be engineered correctly (not as a filter on B2, but as the primary trigger), it could open a fundamentally different book.
NEW DATA: None. Reprocess existing 15m OHLCV.
FALSIFIER: Era-flip (IS positive, OOS negative or vice versa). Or IS catastrophic again. Or any of the standard failure modes.
HIT BAR: Same sign in both eras on both lanes. Pre-registered: B1-only engine × 2 lanes = 2 cells minimum, plus the standard control assertions.
MY CONFIDENCE: low — every B1 number produced so far has been an artefact. The previous attempt was catastrophic. But it's the one "unknown" direction, and if it works it would be genuinely novel. Worth a carefully-engineered attempt.
P8. The data/flow/metrics Dimension — What Are These Derived Metrics?
THESIS: The data/flow/metrics/ directory contains 2094 daily zip files of BTCUSDT metrics from 2021-01→2026-06. Audit what these metrics actually contain before deciding whether they're usable — they may encode information channels we don't know about.
MECHANISM: This is the most mysterious data dimension. 2094 daily zips covering the full IS/OOS period. The name "metrics" suggests derived/computed values, possibly including things like realized volatility, volume-weighted metrics, or other derived features that the system doesn't currently compute. If the metrics contain, say, realized volatility or volume imbalance at 1h resolution, they could feed into a regime measure that's currently invisible. The audit itself is a research step: catalog what each zip contains, determine if any metric is computable at the decision instant, and identify whether any could plausibly modify the bias layer.
NEW DATA: data/flow/metrics/BTCUSDT-metrics-YYYY-MM-DD.zip, 2094 files.
FALSIFIER: The metrics are redundant with already-measured quantities, or they're not computable at the decision instant, or they don't produce same-sign improvement on any regime-modified book.
HIT BAR: This is a preliminary audit, not an arm. No pre-registered hit bar yet — the audit must happen first, then proposals emerge from it.
MY CONFIDENCE: medium — it's an audit, not a hypothesis. The data exists, covers the right period, and is completely unexamined. Even if nothing is usable, knowing what's in there is worth the time.
WHICH ONE WOULD I RUN FIRST?
P5 (Forward Validation) first, because it's the only proposal that addresses the fundamental methodological problem. Every other proposal's results on mined data are worthless until a forward validation path exists. The FORWARD_TEST_PLAN.md is pre-registered, the data is on disk, and the pipeline is already built. It can kill a candidate at n=50 and confirm at n=150. Start it now; it runs in parallel with everything else.
P1 (Wave/Label Redesign) second, because it's the only proposal that attacks the problem from the representation direction rather than the filter direction. The graveyard is entirely about filters; P1 changes the coordinate system. And it's explicitly flagged as the prompt author's "strongest suggestion." It requires no new data, only engineering.
What I'd need from you:
1. Confirmation that P1's wave-labelling approach is acceptable (it's the one direction I'm most confident about)
2. Access to data/flow/ to determine what the funding rate, premium, and metrics files actually contain at the row level (not just directory listings — I need to read one file from each)
3. Whether you want me to attempt P7 (B1 entry) at all, given that every prior attempt has been catastrophic — I'd want to see the exp_b1_entry.py pattern first to understand what went wrong
Note: I have not proposed anything involving scheduled events (P10 in the seed list). The audit in official_fed_speech_archive_audit_2021_2026.json shows exact_time_available: false and advance_publication_timestamp_available: false for the majority of entries — meaning this data cannot support a path-true event gate. It's only archive-dated, so at the decision instant you cannot know a Fed speech is about to happen. This direction is dead on arrival due to data limitations, not worth proposing.
---
LongCat 2.5
RESEARCH PROPOSALS — Second Researcher
Ranked by my belief in the mechanism after reading the graveyard.
P1. FS-only engine
THESIS: Entering on the FS (final swing confirmation) mark rather than only on B2/FLIP breaks would open a much larger trade book from the same swing structure.
MECHANISM: The graveyard closes B2/FLIP entries and 1m entries, but CLOSED_DO_NOT_REPEAT.md explicitly lists "True FS-only engine" as still open: 2900 IS / 1634 OOS confirmed swings exist, but only 314/179 ever produced a B2/FLIP entry that was priced. That is a 9× larger candidate pool that has never been simulated. The closed list attacked B2/FLIP filters (range position, ADX, regime) and 1m entries — nobody has asked whether the FS mark itself, which is the completion of the same swing the system already trades, is a better entry point than the B2/FLIP break that precedes it. The mechanism is different from every closed row: it changes which mark in the existing swing structure fires the entry, not whether to take a trade the system already fires.
NEW DATA: None. All data exists on disk (data/bybit/ 15m/1h/1m). The FS mark is already computed in the swing dicts (fs_at_idx, fs_at_time).
FALSIFIER: If the FS-only book's net R is negative in either era, or if the win rate drops below ~20% (meaning the FS mark is a lagging confirmation with no edge), the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign (positive net R) in both IS and OOS on both lanes (champion + utcsat)
- Net R per trade ≥ 0.3× the B2/FLIP book's net R per trade (the FS book will have more trades, so per-trade expectancy can be lower, but not zero)
- Ex-best-5 not worse than control in both eras
- Win rate ≥ 22% (FS is a confirming mark, so WR should be higher than B2/FLIP's 27.8% if the confirmation has value; if WR collapses, the mark is lagging)
MY CONFIDENCE: High. This is the most concrete open direction: explicitly listed as open, large unpriced pool, clear mechanism, no new data needed, and the harnesses to test it already exist.
P2. Label/notation redesign — ZigZag + Elliott hybrid wave labelling
THESIS: A different labelling of the same 15m price structure (e.g., ZigZag legs + Elliott wave degrees, or P1/P2/P3 wave marks) would produce a better-conditioned trigger set than the current B1/B2/FLIP/FS four-mark system.
MECHANISM: The graveyard is 31 rows of filters on trades the system already fires. This proposal changes what the system sees — the upstream trigger set itself. The current B1/B2/FLIP/FS marks come from a single swing engine with fixed parameters (minBars=14, sustainBars=7). Nobody has examined whether a different decomposition of the same price action — say, a ZigZag with ATR-scaled thresholds plus a wave-degree overlay — produces marks that separate winners from losers better. The entry-time autopsy showed that no entry-legal feature separates the tail beyond time — but that autopsy was run on the current mark set. A different mark set is a different feature space. This is the one direction that is upstream of every closed filter: if the trigger set is better-conditioned, all downstream filters have more to work with.
NEW DATA: None. All data exists. The change is to the swing computation and signal collection logic, not to the data.
FALSIFIER: If the new mark set produces a book with net R ≤ 0 in either era, or if the mark-level AUC for separating top-decile from bottom-decile trades is ≤ 0.55 in both eras (no better than the current marks), the redesign is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R ≥ 0.8× the champion book's net R (the new book can have fewer trades, but must not be catastrophic)
- Mark-level AUC for top-vs-bottom decile separation ≥ 0.60 in both eras (the current marks achieve ~0.5; the new marks must beat this)
- Ex-best-5 not worse than control
MY CONFIDENCE: Medium-high. The mechanism is sound (upstream change, different feature space) and the prompt calls it the strongest suggestion. But it is speculative: there is no guarantee a different labelling is better, and the space of possible labellings is large (risk of retrospective selection). The hit bar must be written before choosing the labelling scheme.
P3. B1 entry — proper signal-selection patch
THESIS: A true B1 entry (firing on the first break mark, not as a blocking filter on B2) might produce a viable book — every B1 number so far has been an artefact of testing it wrong.
MECHANISM: CLOSED_DO_NOT_REPEAT.md explicitly says: "B1 entry. No kwarg fires the entry on B1 — exp_b1_b2_mode is a blocking filter on the B2 trigger, not a different trigger. Needs a signal-selection patch plus a full path-true run. Honestly unknown; every B1 number produced so far has been an artefact." The one live lead from the 1m book (1m B1 is OOS-positive on trimmed mean where 15m B1 failed 4/4) suggests B1 might have era-dependent behaviour that was never properly tested. This is explicitly open, not closed.
NEW DATA: None. The patch is to _collect_signals in btc_engine.py (in-memory, per the repo's rules).
FALSIFIER: If the properly patched B1 book has negative net R in both eras, or if the win rate is below 18% (the B1 mark is a early break with no confirmation, so a very low WR would confirm it has no edge), the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R > 0 in both eras (B1 is a speculative entry; it needs to at least break even)
- Win rate ≥ 20% (B1 fires before confirmation, so WR should be lower than B2/FLIP's 27.8%, but not catastrophically so)
- Ex-best-5 not worse than control
MY CONFIDENCE: Low-medium. Explicitly open and unknown, but the prior B1 results were catastrophic when tested as a filter (IS −34.9R, WR 17.2%). The proper patch might fix the artefact, but the prior is weak.
P4. 30m timeframe as LTF
THESIS: A 30m LTF (built from 15m data) would produce a trade book with a different noise-to-signal ratio than 15m, potentially better-conditioned for the 1h HTF cascade.
MECHANISM: The graveyard closes 4h HTF confirmation and 5m confirmation, but 30m is explicitly noted as not tested anywhere in the repo. The barrier is real: 30m would need building from 15m (resampling), and bar-counted parameters (cooldown_bars=8, max_consecutive_losses=3, sustainBars=7, minBars=10) would need rescaling. But the mechanism is different from the closed 4h/5m tests: 4h was a confirmation filter on existing 15m trades, and 5m was a faster confirmation. 30m is a slower LTF that would fire fewer, potentially higher-quality signals. The 1m closure was about cost arithmetic (0.79R/round trip); 30m has 1/30th the bar count of 1m, so cost is not the barrier. The question is whether 30m swing structure carries different information than 15m.
NEW DATA: None strictly — 30m can be built from existing 15m data by resampling. But the resampling must be pre-registered (aggregate 2×15m → 1×30m, or fetch from Bybit).
FALSIFIER: If the 30m book's net R is negative in either era, or if the trade count drops below 100 in either era (too few trades to be useful), the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R per trade ≥ 0.5× the 15m book's net R per trade (30m will have fewer trades, so per-trade expectancy must be higher)
- Trade count ≥ 100 in both eras
- Ex-best-5 not worse than control
MY CONFIDENCE: Medium. Explicitly untested, and the mechanism (slower LTF = fewer but better signals) is plausible. But the parameter rescaling barrier is real, and the 1m closure showed that finer timeframes don't add edge — 30m is coarser, which is the right direction, but it might just be a worse 15m.
P5. Position lifecycle as resize rather than close
THESIS: When a multi-position book has overlapping trades, resizing the older position (reducing its stop distance or partial profit-taking) rather than closing it outright would preserve more R in trending markets.
MECHANISM: The graveyard closes "exit at FS when the swing looks bad" and "pivot trail" — both are exit policies. The prompt explicitly notes: "Nobody has asked whether the right response to a multi-position book is to resize rather than close." The current system either holds a position to its stop/trail exit or closes it on a cohort policy. A resize policy would reduce the position's risk exposure (tighten the stop to lock in partial profit) without fully exiting, allowing the trade to continue with a smaller R denominator. This is a different mechanism from every closed exit row: it doesn't exit early to raise WR (the closed "exit at FS" row), it doesn't move the stop closer (the closed "tighter SL" row), it reduces the position's risk while keeping it alive.
NEW DATA: None. But this needs a size channel in the engine, which v18_streak_halt.py does not have. This is an engineering prerequisite, not a data prerequisite.
FALSIFIER: If the resize policy's net R is worse than the close policy in both eras, or if the max drawdown increases (meaning the resize is just delaying losses), the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R ≥ 1.1× the control book's net R (resize must beat close by a meaningful margin to justify the complexity)
- Max drawdown ≤ 1.0× the control book's max DD (resize must not increase risk)
- Ex-best-5 not worse than control
MY CONFIDENCE: Medium. Explicitly untouched, and the mechanism (preserve R in trends by reducing risk rather than exiting) is sound. But the engineering barrier (no size channel) is significant, and the closed exit rows suggest the exit space is hard to improve.
P6. Cross-sectional alt breadth as BTC timing signal
THESIS: The fraction of alt-coins (from data/scan-fut/) trending in the same direction at any moment is a regime indicator for BTC that can time entries.
MECHANISM: The graveyard closes "cross-sectional alt rotation" — but that was about rotating into alts. This proposal uses alt breadth as a timing signal for BTC entries, which is a different mechanism. The finding that alt books are near-uncorrelated with BTC (mean pairwise monthly-R +0.072 IS, −0.053 OOS) actually strengthens this proposal: if alts are near-uncorrelated, then alt breadth is an independent source of information about the broader crypto market regime, not just a proxy for BTC. When 12+ alts are simultaneously trending up, the crypto market is in a risk-on regime, and BTC trend entries are more likely to succeed. This is a feature computed from existing alt data, not a rotation strategy.
NEW DATA: None. data/scan-fut/ has 16 alts with 15m + 1h data. The feature is computable at the decision instant (count alts with 1h swing direction = up at the entry bar).
FALSIFIER: If the alt-breadth gate's net R is negative in either era, or if the feature's AUC for separating top-decile from bottom-decile BTC trades is ≤ 0.55 in both eras, the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R improvement > +10R vs control in both eras (the gate must add meaningful value)
- Feature AUC ≥ 0.60 in both eras
- Ex-best-5 not worse than control
MY CONFIDENCE: Low-medium. The mechanism is plausible (independent regime indicator), but the near-uncorrelation finding cuts both ways: it means alts are independent, but it also means alt breadth might not predict BTC. The graveyard's "cross-sectional alt rotation" closure creates tension — I acknowledge this and flag it as a risk.
P7. Order-book / microstructure data
THESIS: Order-book imbalance or trade-flow toxicity (VPIN) computed from Bybit would provide a genuinely new information set that the OHLCV-only system cannot access.
MECHANISM: Every closed row in the graveyard operates on OHLCV data. The prompt explicitly says: "If you want something genuinely outside the current information set, say so explicitly and name what would have to be fetched." Order-book data (top-of-book or 20-level depth) and trade-flow data (aggregated trades with taker buy/sell classification) are the two most obvious missing information sources. The mechanism: large limit-order imbalances at the bid/ask predict short-term price moves, and taker-flow toxicity predicts adverse selection — both are microstructure effects that OHLCV cannot see. This is not a filter on existing trades; it is a new feature space.
NEW DATA: Does not exist on disk. Would need to be fetched from Bybit's public API (/v5/market/orderbook for L2 depth, /v5/market/recent-trade for trades). Historical order-book data is not freely available; trade history is. This is a significant data-acquisition barrier.
FALSIFIER: If the fetched data covers < 1 year (too short to test both eras), or if the microstructure feature's AUC for separating top-decile from bottom-decile trades is ≤ 0.55 in both eras, the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R improvement > +15R vs control in both eras
- Feature AUC ≥ 0.60 in both eras
- Ex-best-5 not worse than control
MY CONFIDENCE: Low. Genuinely outside the current information set, which is the point. But the data-acquisition barrier is high, the cost structure might kill it (like 1m), and the feature might not survive the same-sign-in-both-eras bar. High risk, high potential reward.
P8. Swing magnitude asymmetry
THESIS: The magnitude of the 1h swing that opens a bias window (relative to ATR) predicts the quality of the 15m entry that fires inside it — large 1h swings produce better 15m entries.
MECHANISM: The current system opens a bias window for every 1h swing regardless of size. But a large 1h swing (say, > 2× ATR) represents a stronger trend impulse than a small one (< 0.5× ATR). The 15m entry that fires inside a large-impulse window is more likely to be riding a real trend. This is a structural feature of the HTF-LTF interaction, not a filter on existing trades. The graveyard closes "range position × width gating" — but that was about the 1h range position of price (where price sits in the 1h range), not the magnitude of the 1h swing that opened the window. Different mechanism: one is about location, the other is about force.
NEW DATA: None. The 1h swing magnitude is already computed in the swing dicts (seg.end_px - seg.start_px).
FALSIFIER: If the swing-magnitude gate's net R is negative in either era, or if the feature's AUC for separating top-decile from bottom-decile trades is ≤ 0.55 in both eras, the direction is dead.
HIT BAR: Pre-registered before any run:
- Same sign in both eras on both lanes
- Net R improvement > +10R vs control in both eras
- Feature AUC ≥ 0.60 in both eras
- Ex-best-5 not worse than control
MY CONFIDENCE: Low-medium. The mechanism is plausible (force of impulse predicts trend quality), and it is structurally different from the closed range-position filters. But it is close enough to "range width gating" that I flag the tension. The hit bar must be written before choosing the magnitude threshold.
Which one would I run first, and what would I need
I would run P1 (FS-only engine) first. It is the most concrete open direction: explicitly listed as open in CLOSED_DO_NOT_REPEAT.md, a 9× larger unpriced trade pool, no new data needed, and the harnesses to test it already exist. The mechanism is clear (the FS mark is the completion of the same swing the system already trades), and the falsifier is sharp (if FS-only trades are net negative, the direction is dead immediately).
What I would need from you:
1. Confirmation that the FS-only engine is genuinely open (not just listed as open but secretly tested) — a 30-second check of the experiment registry.
2. The go-ahead to build the in-memory engine patch (per the repo's rules: never edit btc_engine.py, patch in memory and install into sys.modules).
3. A decision on whether to test FS-only as a replacement for B2/FLIP entries or as an additional entry type (the latter would increase trade count, which the graveyard warns against — but the mechanism is different, so it might be justified).
If P1 fails, I would run P2 (label/notation redesign) next. It is the highest-upside direction because it is upstream of every filter — if the trigger set is better-conditioned, all downstream experiments have more to work with. But it is also the most speculative, so it should only be run after the concrete directions are exhausted.
Note on scheduled events: The graveyard lists "scheduled-event filters" as closed, so I have not proposed them. The seed list says "an audit exists; I do not know whether a pre-registered event gate was ever run path-true, or only audited." If it was only audited and never run path-true, a properly pre-registered path-true run might be genuinely new — but the graveyard's closure takes precedence, and I flag this as a question for you rather than a proposal.

---
Big Pickle
I've read the four required docs and then verified the seed list against the code and data. Here is what I found before proposing anything.
Corrections to the briefing (verified in code, not assumed)
1. The repo is not OHLCV-only — but the extra data is unusable. data/flow/bookDepth/ holds 39.8M rows of ±1–5% depth-band notional at ~30s resolution, 2023-01 → 2026-09-25. No experiment has ever read it. It is also unobtainable for 2021–2022 (the file starts 2023-01), so under your own rule 5 it can never pass a two-era bar. Don't spend time here.
2. Scheduled events are closed, path-true, with placebos — SCHEDULED_EVENTS_AUTOPSY.md ran 4 frozen policies + ±1-day shift placebos. Verdict: not supported. Powell is closed separately on advance-knowledge grounds. Nothing left there.
3. 30m and 2h are closed, not untouched. exp_tf_family.py resampled 30m and ran a 4-cell ladder factorial including duration-preserved min_bars. 2h was run four ways. Both lost.
4. Position-lifecycle-as-resize is unreachable. The only allocation knob the engine has is exp_max_concurrent (a cap on concurrent risk units), and it has been swept: cap=5 is free-to-better. The graveyard is right that this is engineering-blocked.
5. HANDOVER_SESSION.md line 90 is wrong. It says "sw10/sw15/sw20 are all built from the 15m stream." They are not — exp_5m_confirm.py:186-187 builds sw10/sw20 from the 1h stream; only sw15 is 15m.
6. chop_thresh=58.0 is inert on the shipped lane. In v18_streak_halt.py:415, mode="atr_high" reads only atr_high_thresh; chop is never consulted in that branch. The champion's documented parameter set contains a knob that does nothing.
The one observation that organises the whole graveyard
From v18_params.py:71-74 and exp_5m_confirm.py:186: the shipped lanes run the 1h chain at min_bars=10 (≥10h legs) and the 15m chain at min_bars=50 (≥12.5h legs) — built by the same SwingEngine, the same break-based detector, with a greedy sequential stitch (btc_swing.py:150, next_start_pos = end_pos + 1).
So the "three-timeframe cascade" is not nested scales. It is two decompositions of the same ~1-day object at two bar resolutions, and the 15m layer's only job is to catch the break earlier and price it finer. That single fact explains why 1m, 30m, 2h, 4h, 5m all failed (each moves the leg scale off ~1 day) and why every filter that worked removed a contiguous structural block while every per-bar indicator died. It also means the one structural knob anyone has ever swept is a single constant on a shared detector.
This is also why ENTRY_TIME_AUTOPSY's negative result does not bind anything below: it scored features at the entry instant on the existing book. It closed filtering, not re-observing.
P1. PRICE THE 15m LAYER — what does it actually buy?
THESIS:        Nobody has ever scored the 1h book that generates every bias
               window, so the repo has never measured whether the 15m layer
               adds anything, subtracts anything, or is decoration.

MECHANISM:     The 1h chain already produces a complete, tradeable book:
               simulate_btc_trades_v7(c1h, sw1h, entry_break=...) runs on
               every single call and its result is returned as
               htf_trades / htf_trades_b2. Those trades are consumed ONLY as
               intervals (to_intervals). `trade_stats` is never applied to
               them — I grepped every caller. Both chains use the same
               detector at the same ~1-day leg scale, so the clean contrast
               is: identical 1h entry rule, identical LTF exit rule, entry
               taken on 1h vs entry taken on the 15m break inside the window.
               That isolates timing-vs-selection in R units, which is the
               number no doc in this repo contains.

NEW DATA:      None. The trades already exist in the return dict of every run.
               Second arm needs nothing either: re-price each accepted LTF
               entry at the 1h-equivalent instant, keeping the 15m stop and
               trail.

FALSIFIER:     Not falsifiable in the usual sense — this is a measurement, so
               it cannot "fail." It is *actionable* only if it moves the
               number. The finding that would end the 15m layer's
               justification: the 1h book alone matches or beats the LTF book
               in both eras. The finding that would end the 15m layer's
               defence: the LTF book wins only on IS and era-flips.

HIT BAR:       Controls 500/+325.8, 454/+358.9, 279/+70.2, 253/+60.2 asserted
               exact before anything is scored. Arm A reports the 1h book on
               all three interval sets (flip/b2/decisive) in both eras with
               net R, trimmed mean, ex-best-3 and ex-best-5. Arm B reports
               dNet and dTrim for LTF-entries-repriced-at-1h. Pre-registered
               decision rule: the 15m layer is *justified* only if Arm B loses
               strictly more R than Arm A gains, in the same sign, in both
               eras, on trimmed mean. Report the whole table either way.

MY CONFIDENCE: high that it is runnable and informative; the coin-flip is on
               the outcome. The information is guaranteed and the cost is one
               run. This is the highest information-per-hour item available.
P2. REVISION-ALLOWED LABELLER — make leg length endogenous (your seed, sharpened)
THESIS:        The detector decides a leg is over at the FIRST extreme that
               clears the pivot after a constant 50-bar floor; a retracement-
               based labeller would decide it when price gives back a fixed
               FRACTION of the leg, making leg length a market property
               instead of a constant.

MECHANISM:     min_bars is a constant-duration filter, and MB20/30/40/50 swept
               it — that axis is mapped, and 50 won. What MB cannot reach is
               leg length that scales with the leg's own size. The current
               rule is also *greedy and non-revisable*: firstswing.py:588
               sets declared=True and process_bar returns immediately
               forever after, so a leg's terminal extreme is frozen at the
               first qualifying print even though more price has since
               arrived; and btc_swing.py:150 makes every subsequent leg start
               at that frozen point, so legs can never overlap. Two
               properties, neither ever varied, neither reachable by any
               per-trade filter. Concretely pre-registerable: (a) retrace
               fraction x in {0.382, 0.5, 0.618} as the leg terminator;
               (b) allow leg k+1 to start before leg k's end (nested tree,
               P1/P2-style) instead of strictly after it.
               This is the strongest surviving seed precisely because
               ENTRY_TIME_AUTOPSY closed filtering, not re-observation.

NEW DATA:      None. 15m and 1h both on disk for both eras.

FALSIFIER:     (i) Leg-count and leg-duration distributions come out
               materially the same as the current chain — i.e. the
               retracement rule reproduces the break rule, so there is nothing
               new to see. (ii) The new book's net R is negative or
               era-flipped in either era. (iii) The synthetic placebo in P4
               scores as well as the real labeller.

HIT BAR:       Controls exact. Pre-register the three x values BEFORE any run
               and report all three plus the control, unselected. Pass
               requires: same sign in both eras on BOTH lanes, positive
               trimmed mean in both eras, ex-best-5 positive in both eras,
               n >= 150 per era, AND a replication on ETH/SOL from
               data/alt-fut (a dataset never used to select a detector) with
               same sign. Any single miss closes it.

MY CONFIDENCE: medium-high on mechanism, low-medium on outcome. Highest
               upside in the list; the reason to believe it is structural
               (untouched object) not statistical. Argue with the retracement
               variant specifically — I think the nested-tree variant is
               weaker, because the current non-overlap may be load-bearing
               for the stop.
P3. PARENT-WINDOW EXIT — the entry is gated by the window, the exit is not
THESIS:        85 trades in the shipped book outlive the 1h window that
               authorised them; close a position when the higher-timeframe
               thesis that opened it is invalidated.

MECHANISM:     There is a structural asymmetry nobody has attacked. Entry is
               gated by `s + 2700 < bar_ts <= e + 2700` (v18:539) — the 1h
               window is the sole authority to open a position. Exit is the
               ratcheted 15m swing-pivot stop and nothing else: v18:626-649
               has no window term, and the LTF book has **no profit target
               and no time exit at all** (the 3R `target` at v18:592 is
               computed, stored, and never checked; CHECKLIST #36 confirms
               "LTF trades trail only"). backtest_checklist_v18.md:194-196
               states the window "does NOT close open LTF trades" as a
               documented property. So a trade can be held for weeks after
               the 1h position that justified it hit its stop. The reference
               event is the parent's death, not the trade's own swing.

NEW DATA:      None.

FALSIFIER:     R given up at parent-window-close is positive in all four
               cells against a permutation null. Prior is not zero but it is
               real: FS_TIME_DECISION measured +85.1R mean giveup at the LTF's
               own FS against a population worth +263.7R, so an early-exit
               family has a strong prior of giving money up. This proposal
               survives that prior only because the parent window closes on a
               *different and typically later* event than the LTF's own FS.

HIT BAR:       Descriptive first, per-trade, exactly mirroring FS_TIME_DECISION's
               method (200-draw permutation null on the feature, not an
               aggregate). Only if giveup is negative in >= 3 of 4 cells does
               a path-true arm get written, and then it must clear: same sign
               both eras, both lanes, trimmed mean and ex-best-5, and it must
               not be bought by cutting the tail (report the count of trades
               whose R exceeded +10R that the arm removes).

MY CONFIDENCE: low-medium. Weak prior from the FS null, but the object is
               genuinely untouched and the diagnostic is nearly free. Run the
               descriptive version even if you expect nothing.
P4. MATCHED PLACEBO UNDER THE SHIPPED EXIT MACHINERY
THESIS:       Run 3A's random/delay entry control again — but through the real
              trail instead of fixed targets — because the fixed-target
              control already scored 58-60% of the real R.

MECHANISM:     EXPERIMENT_LOG 3A: under fixed 3R targets, real entries
               +104/+118R versus random-entry +60/+62R and delay-4
               +60/+78R. That is a 40% attribution to *entry selection* — on
               a placebo nobody would defend. It was never re-run with the
               structural trail, which 2A/2B identifies as the dominant source
               of asymmetry (+445.2R gross vs +104R at fixed 3R). If the
               trail alone manufactures most of the payoff, the correct
               conclusion is that the detector contributes little and every
               label proposal above is attacking decoration.

NEW DATA:      None.

FALSIFIER:     n/a — a control, not a candidate. It cannot be adopted. It can
               only tell you to stop.

HIT BAR:       Pre-registered before the run: 200 matched-count shuffles of
               the entry signal set, same counts per era, same exit machinery,
               same costs, report the full distribution of net R and of
               trimmed mean. Decision rule fixed in advance: if the real
               ledger sits below the 90th percentile of the null, the
               entry-selection attribution is dead and P2 is not worth
               running. Do not report a percentile without the null mean and
               the count, and do not run a second placebo family afterwards.

MY CONFIDENCE: high that this must be done and that its result is
               informative in either direction. It is the cheapest thing on
               this list and the only item that can tell you to abandon the
               rest. Run it before P2, not after.
P5. ENTRY FILL-CONVENTION AUDIT — is the +325.8R partly a fill artefact?
THESIS:       The backtest fills at the close of the bar in which the break
              occurred; a live trader can only send after that close and fill
              at the next bar's open.

MECHANISM:     v18:585 sets `entry = candles_ltf[i]["close"]` where `i` is the
              bar of the break itself, and `_collect_signals` keys signals by
              the break bar's timestamp. The break is a high/low event
              *inside* that bar (firstswing.py:286-287), so for an up-break
              the fill is at or near the bar high — you are assumed to have
              transacted at the extreme of the very bar that signalled, at a
              price only knowable at that bar's close. The repo has done
              fill-basis audits on the EXIT side (ANCHOR_BASIS_AUDIT §1-§3,
              including the ratchet fix that cost 2 trades of optimism) and
              never on the entry side. This is a control, not an edge.

NEW DATA:      None.

FALSIFIER:     A next-bar-open re-fill reproduces the shipped ledger within
               the stated cost model, i.e. the convention is not load-bearing.

HIT BAR:       Controls asserted against the close-fill pin first (that is the
               control). Pre-register three fills, all reportable, none
               selected: (a) signal-bar close [shipped], (b) next 15m open,
               (c) next 15m open plus the existing 5bp entry slip on top.
               Report net R, WR, trimmed mean, ex-best-3, ex-best-5, and the
               per-trade delta distribution, in both eras on both lanes.
               A live expectancy bound is only valid if (b) and (c) are
               reported; publishing (a) alone is not a result.

MY CONFIDENCE: high that it must be measured, medium that it will be negative.
               I expect a real cost, concentrated in long entries, because a
               close-fill on a breakout bar systematically pays the bar's
               extension. Either way it bounds what you can deploy.
P6. WINDOW-CLOSE COMPOSITION, and the one window end never run
THESIS:       The window's right edge is the 1h shadow trade's exit, which is
              one of three events — stop, +3R, or the 16-day cap — and nobody
              has reported which one closes the windows that actually admit
              trades.

MECHANISM:     v18:242 sets `wend = t["exit_ts"]` where the 1h trade runs
              with `rr_target=htf_rr=3.0, cap_days=16, sl_mode="swing"`. So a
              window closed at +3R is a window whose higher-timeframe thesis
              is *finished* — and the LTF keeps opening trades inside it. That
              is a specific, checkable, structural hypothesis with a named
              mechanism, and it is a window-*definition* change rather than a
              per-trade filter. Two window ends are already closed —
              `r_touch` (earlier) and `bias_flip` (earlier). **A 3R close
              that does not close the window is later than shipped and has
              never been run.**

NEW DATA:      None.

FALSIFIER:     The composition table shows <10% of admitting windows close at
               3R, or the single later-window arm era-flips or is negative in
               IS. Note the structural risk and state it now: this arm ADDS
               trades, and "more trades" is closed (A5: +159 trades for
               -136R IS). It is defensible only if the added trades are
               structurally different from the relaxed-cooldown trades, so the
               report must include the added cohort's trimmed mean and its
               overlap with the existing book, not just dNet.

HIT BAR:       Composition table is descriptive and costs nothing: for every
               admitting window, the close reason and the count, both eras,
               both lanes, plus the trimmed mean of the LTF trades inside each
               close-reason cohort. One arm only, pre-registered:
               window_end="exit_ignore_target". Pass = same sign both eras,
               both lanes, positive trimmed mean, ex-best-5 positive, and the
               added cohort's trimmed mean strictly positive on its own.

MY CONFIDENCE: low on the arm, high on the diagnostic. Report the table
               whatever it says; it is the first time anyone will know how the
               window actually terminates.
P7. THE RATCHET LADDER — where the tail actually comes from
THESIS:       Nobody has looked at the sequence of stop ratchets that each
              winner walks up, which is the only mechanism producing the
              +48R trades.

MECHANISM:     Exit is `sl_cur` ratcheting to `seg.start_px` of each newly
              confirmed same-direction swing (v18:602-612, 626-631). So the
              payoff is a product over a ladder of pivot levels, and the tail
              question is sharp and unanswered: do the +40R trades get there
              via FEW ratchets that happen to be far away, or via MANY
              compounding ones? If few-and-far, the tail is luck and no exit
              work will ever help (consistent with TAIL_RISK and TRAIL_MECHANICS
              both concluding the tail is intrinsic). If many-and-compounding,
              the *spacing* of the ladder is the lever — and the spacing is set
              by min_bars_15m=50, which nobody has examined as a trail
              parameter rather than an entry parameter. Note the split-mb
              machinery in test_experiments_craze.py already provides a
              separate slower chain for trail events, so this is wiring.

NEW DATA:      None.

FALSIFIER:     Ratchet count per winner has no relationship to final R, or the
               +10R trades are concentrated at ratchet counts that are simply
               the most common counts.

HIT BAR:       Descriptive, zero arms. Per trade: n_ratchets, the R increment
               at each ratchet, and final R — reported for both eras, both
               lanes, split at 2R / 5R / 10R, plus a rank-transformed
               correlation (per the ACF_TAIL_CHECK precedent: a raw
               correlation here will be a tail artefact and must be reported
               rank-transformed alongside). Pre-register the one arm it
               licenses: trail events from a *different* min_bars chain
               (already supported by split_mb), which must clear the standard
               four-part bar.

MY CONFIDENCE: medium that the diagnostic is informative; low that the arm
               survives, since the exit family is heavily worked. But the
               diagnostic has never been run and it is the mechanism behind
               every number this repo reports.
P8. PREFIX-INVARIANCE GATE — a validity check on all of the above
THESIS:       PURE_V18_GEOMETRY_REPORT_CORRECTED states full-history swing
              chain is "not yet proven prefix/live-identical"; every delta in
              proposals P1-P7 is measured against a baseline that inherits
              that caveat.

MECHANISM:     The chain is greedy and non-revisable, so swing k's boundaries
              depend on all of bars 0..k. If the chain is not prefix-stable,
              then a 30-trade-per-block statistic is not a property of the
              strategy but of where the sample was cut, and IS/OOS "same
              sign" comparisons are partly comparing two different algorithms.
              §3g certified the batch numbers as live-identical on the
              *trades*; PURE_V18 says the *chain* is not certified. Those two
              are in tension and the tension is unresolved.

NEW DATA:      None.

FALSIFIER:     Chains and ledgers are byte-identical on truncated prefixes and
               the concatenation property holds to the stated tolerance.

HIT BAR:       Not a hit bar — a gate. Cut each era at 5 interior dates,
              recompute swings, trades and net R on each prefix, and report
              (n, net R) per prefix per era. Tolerance stated in advance at
               the level ANCHOR §2 used. If prefixes disagree by more than
               that, every comparison in this repo is conditional and that gets
               written at the top of the next handover.

MY CONFIDENCE: high that it is unresolved and cheap. Not an edge proposal.
               Run it in parallel with P1, not after, because its result
               changes how much P1-P7 are worth.
What I would run first, and what I need from you
P1, then P4 in the same session, with P8 running alongside. P1 costs one run and settles the only question the repo has never answered about its own architecture. P4 is the control that tells you whether P2 is worth a week. P8 is a gate, not a candidate.
What I need from you:
1. Permission to score htf_trades. Every harness returns them; nothing scores them. I want to add a trade_stats call on them. If you'd rather I not touch the reference pins, I'll report it in a standalone script with the four control asserts and no registry entry.
2. A ruling on _r_touch_end / the 3R window arm (P6). I think the diagnostic table is unambiguously worth running and the arm is not — it adds trades into a closed family. Confirm you want the arm written anyway, or I'll report the table and stop there.
3. The prefix-invariance verdict (P8). If someone already knows the answer, P8 is dead and I drop it. EXPERIMENT_LOG Stage 19 is referenced by both geometry reports but I could not find a result artifact for it — do you know if it was ever run to completion?
4. Confirmation that data/forward/bybit is still clean. It has been read once, for parity (_forward_eval.json, R1), which I would not call selection. It now ends 2026-09-25 and has ~3 days of unfetched data behind it. If you want, the right spend is to extend it, re-stamp _forward_manifest.json, and then spend the whole slice on one candidate — my vote is P1's Arm B, because a fill-convention and entry-timing verdict is exactly the kind of thing that a mined historical era cannot adjudicate and 60-70 forward trades can at least break.
Two things I am explicitly not proposing, with reasons: anything built on data/flow/bookDepth (no OOS coverage, so it cannot clear rule 5 and the source does not exist for 2021-2022), and anything on 30m/2h/4h/5h (all run, all lost — and exp_tf_family already controlled for duration).


---
kilo code
Now I have a complete understanding of the system, graveyard, and constraints. Let me formulate the research proposals.

---

## 6-10 Research Proposals (Ranked by Conviction)

### P1. P1/P2 Wave Labelling — Replacing B1/B2/FLIP/FS with Structural Wave Marks

**THESIS:** The current four marks (B1/B2/FLIP/FS) are break-level annotations; a P1/P2 wave labelling (first pullback, second pullback in a confirmed swing direction) exposes the *internal structure* of each 15m swing and may separate entries that the current marks conflate.

**MECHANISM:** B1/B2/FLIP/FS are flat — they don't encode *where in the swing* the break occurred. A P1/P2 labelling on the Walker/firstswing pivot chain would tag each 15m swing's internal retracements (wave-1 impulse → wave-2 pullback → wave-3 continuation). The hypothesis: entries on wave-2 retracements (P2) in the direction of the 1h bias window have different edge than breakout entries (B2/FLIP), and the current system buckets them together. This changes what the system *sees*, not a filter on what it already rejects.

**NEW DATA:** No new data needed. The WalkerEngine already emits sealed pivots (H/L alternating) per 15m bar. The swing engine (`btc_swing.py`) already produces `seg.start_idx/end_idx` and `break_marks`. A post-process pass over confirmed swings can compute P1/P2 labels from the pivot sequence — entirely from existing on-disk 15m OHLCV.

**FALSIFIER:** If P1/P2 labelling produces zero separation between trade outcomes (AUC ≤ 0.55 in both eras on any P1/P2 cohort), or if the best P1/P2 cohort fails the same-sign bar on forward data.

**HIT BAR:** Pre-registered: a P1/P2-gated cohort must deliver **net R ≥ control + 15R in IS AND same sign in OOS**, with ex-best-5 positive, on both champion and utcsat lanes. If either lane fails, the direction is closed.

**MY CONFIDENCE: High.** This is the strongest seed item. The graveyard shows every *filter* on existing marks failed; this changes the *vocabulary* of what a trade is. The pivot chain is already computed and causal.

---

### P2. Scheduled-Event Pre-Registered Gate — Fed/US Calendar as Regime Switch

**THESIS:** Official Fed speeches and high-impact US events (FOMC, CPI, NFP, ISM) create measurable regime shifts; a pre-registered gate that *widens* the stop and *reduces size* (or pauses entries) in a ±N-bar window around these events may preserve the tail while cutting the noise trades that cluster on event days.

**MECHANISM:** The graveyard closed "scheduled-event filters" but notes an audit exists — it's unclear if a path-true pre-registered gate was ever run. The mechanism is not "avoid events" (which kills winners) but "adapt risk parameters around events": wider SL buffer, smaller position, or mandatory cooldown. The 1h bias window already exists; the gate would modulate LTF entry parameters *inside* an open window when an event is imminent/active.

**NEW DATA:** Exists on disk: `data/scheduled_events/official_us_events_2021_2026.json` (190K) and `official_fed_speech_archive_audit_2021_2026.json` (36K). Both cover the full IS+OOS span. Need to verify event timestamps align to 15m bars causally (event time known before entry bar close).

**FALSIFIER:** If the event-adapted cohort (widened stop / reduced size / pause) does not improve net R vs control in both eras, or if the improvement comes entirely from <3 trades (ex-best-5 negative).

**HIT BAR:** Event-adapted parameters must yield **≥ +20R net vs control in IS (champion lane) AND same sign in OOS**, with maxDD not worse than control. Pre-register the exact ±N bar window (e.g., ±4 15m bars = ±1h) and the parameter deltas (e.g., `sl_buf_atr × 2`, `size × 0.5`, `cooldown_bars +4`).

**MY CONFIDENCE: Medium-High.** Data exists and is causal. The graveyard says "audit exists; I do not know whether a pre-registered event gate was ever run path-true." This is testable cleanly.

---

### P3. True FS-Only Engine — Entry at First Seal, Not Breakout

**THESIS:** The system only prices trades that produce a B2 or FLIP break (314/500 IS, 179/279 OOS). There are 2,900 confirmed swings in IS — an FS-only entry (enter at swing confirmation, stop at opposite pivot) could be a larger, differently-distributed book.

**MECHANISM:** Current entry requires a *breakout* (B2/FLIP) *inside* an HTF window. FS-only enters at `confirmed_at_time` (chop cross or sustain) with stop at the opposite sealed pivot. This is a *different trigger set*, not a filter. The graveyard lists this as "not simulated." The hypothesis: FS entries capture the *start* of the swing leg that B2/FLIP enters mid-leg, so they have wider initial risk but earlier participation — a different R-profile that may complement the breakout book.

**NEW DATA:** None needed. `btc_swing.py` already outputs `confirmed_at_idx/time`, `fs_at_idx/time`, `seg.start_px/end_px`, and the pivot chain from Walker. A new engine variant can simulate FS entries using the same 1m trail/exit logic.

**FALSIFIER:** If FS-only book has net R ≤ 0 in IS, or era-flips (IS positive, OOS negative or vice versa), or if combined (FS-only + breakout) doesn't improve Sharpe/Calmar vs breakout alone.

**HIT BAR:** FS-only must deliver **≥ +100R net in IS (champion params) AND same sign in OOS**, with WR ≥ 20%. Combined portfolio (FS-only + breakout, equal risk weight) must improve Calmar ≥ 15% vs breakout alone.

**MY CONFIDENCE: Medium.** Never simulated. The pivot data exists. Risk: FS entries may have degenerate stops (stop at opposite pivot = very close for small swings). Must enforce minimum stop distance (≥ 0.25 × ATR) as per the graveyard's degenerate-denominator rule.

---

### P4. 30m Timeframe as Independent LTF — Not a Rescaled 15m

**THESIS:** 30m candles (built from 15m or refetched) provide a *different* swing structure — fewer, larger swings with different B2/FLIP geometry. The graveyard closed 4h and 5m; 30m is untested. The barrier (bar-counted parameters collapsing 15×) is solvable by re-parameterising in *time* (minutes/hours), not bars.

**MECHANISM:** 30m swings have ~2× the duration and ~√2× the ATR of 15m swings. The hypothesis: 30m B2/FLIP breaks are *cleaner* (less noise) and the HTF (1h) bias window aligns 2:1 naturally. Re-parameterise all bar-counted params to durations: `cooldown_bars=8` (15m) → `cooldown_min=120`; `max_consecutive_losses=3` → `halt_after_losses=3` (count trades, not bars); `sustainBars=7` → `sustain_min=105`. This makes 30m a genuine alternative LTF, not a rescaled 15m.

**NEW DATA:** 30m not on disk. Must build from 15m (aggregate 2 bars) or refetch. 15m data exists for full span. Building from 15m is causal and exact.

**FALSIFIER:** If 30m book (with time-parameterised config) fails same-sign in both eras, or net R < 50% of 15m control, or ex-best-5 negative.

**HIT BAR:** 30m lane must deliver **≥ +150R IS / ≥ +30R OOS (champion params, time-scaled)** with same sign both eras. Combined 15m+30m portfolio must have pairwise monthly-R correlation ≤ +0.15 and combined DD ≤ 1.5× single-book DD.

**MY CONFIDENCE: Medium.** The barrier is real (bar-count collapse) but the time-parameterisation solution is clean. 4h confirmation failed; 5m confirmation failed; 30m is the untouched middle.

---

### P5. Position Lifecycle as Continuous Resize — Not Binary Close/Open

**THESIS:** The engine has zero size state (`v18_streak_halt.py` has no equity/size/notional/qty hits). When a new HTF bias window opens opposite to an existing position, the current choice is binary: close or hold. A resize response (scale down old, scale up new) may capture transition alpha that binary logic discards.

**MECHANISM:** Build a size channel into the engine (equity → notional → qty at entry). When a new HTF window opens opposite direction: instead of `close_all` or `hold`, compute target net exposure = (new_bias_strength × max_size) − (old_bias_strength × current_size). Resize gradually over N 15m bars. Requires: (a) size channel, (b) bias strength metric (chop/ATR/HMM), (c) resize schedule. The graveyard notes "cohort lifecycle policies tested at fixed thresholds; nobody asked whether resize is the right response."

**NEW DATA:** None new. Needs equity curve (computed from trades) and HTF bias strength (chop, ATR%, HMM regime) already computed per LTF bar in `v18_streak_halt.py`.

**FALSIFIER:** If any resize policy (tested across 5+ transition-speed configs) fails to beat binary close/hold on net R in both eras, or increases maxDD > 20% vs control.

**HIT BAR:** Best resize policy must deliver **≥ +40R net vs binary control in IS (champion) AND same sign in OOS**, with maxDD ≤ control × 1.2. Pre-register the resize function (e.g., linear over 4 bars, exponential half-life 2 bars) and bias-strength threshold.

**MY CONFIDENCE: Medium-Low.** Engineering-heavy (size channel needed). But the graveyard explicitly flags this as untouched and the alt-portfolio result (7/13 alts, near-zero correlation) suggests multi-position management is the natural next lever.

---

### P6. 1m Microstructure Features at 15m Entry — Not 1m Trades

**THESIS:** 1m *trades* are dead (0.79R cost/round-trip). But 1m *microstructure* at the 15m entry instant (bid-ask spread proxy, volume imbalance, tick rule flow) may carry signal that 15m OHLCV discards — without paying 1m trading costs.

**MECHANISM:** The graveyard tested 1m as *trigger, book, fill, add-on gate, feature* — all failed. But all used 1m *OHLCV* or 1m *swing breaks*. Order-book microstructure (if available) is a different information set. If not available, 1m *volume-weighted* features (VWAP distance, volume-at-price, buy/sell pressure from tick rule) at the 15m entry bar close are computable from 1m trade prints (if stored) or approximated from 1m OHLCV + volume. The hypothesis: 1m microstructure at entry instant separates the tail, not the 1m *subsequent* path.

**NEW DATA:** Current repo is OHLCV only. Would need 1m trade prints (tick data) or L2 snapshots. Bybit provides trade history via REST/WebSocket. Must fetch ~3.7 years × 1.95M 1m bars ≈ 2M trades — feasible but not on disk. **Explicitly requires new data fetch.**

**FALSIFIER:** If microstructure features at entry instant show AUC ≤ 0.55 on top/bottom decile separation in both eras (same test as ENTRY_TIME_AUTOPSY).

**HIT BAR:** Any microstructure feature with AUC ≥ 0.65 in both eras, gated cohort delivers **≥ +25R net vs control in IS AND same sign OOS**, ex-best-5 positive.

**MY CONFIDENCE: Low-Medium.** Requires new data fetch (explicitly flagged in seed list). But it's the only way to get *genuinely new information* — everything else re-uses OHLCV.

---

### P7. Alt-Coin Portfolio Construction — Forward-Validated Equal-Risk Sleeve

**THESIS:** The same frozen lane works on 7/13 alts with both eras positive and near-zero correlation (mean +0.072 IS, −0.053 OOS). The graveyard flags the 13→7→6 funnel as retrospective. A pre-registered portfolio construction on *forward* data (or a fresh alt universe) is the only way to validate this.

**MECHANISM:** Not a new strategy — a *portfolio method*. Take the champion lane params (frozen), run on a pre-registered alt universe (e.g., top 10 Bybit linear perps by volume, excluding BTC), equal-risk weight (1/N volatility-targeted per asset), rebalance monthly. Test on `data/forward/bybit/` (never used for selection) and/or a fresh alt fetch from 2023-2026.

**NEW DATA:** `data/scan-fut/` has 16 alts on Binance fapi. Need Bybit linear perp data for same symbols (for apples-to-apples). `data/forward/bybit/` is BTC only. Must fetch Bybit alt data for forward test.

**FALSIFIER:** If forward-tested portfolio (equal-risk, 7+ assets) has Sharpe ≤ 0.5 or maxDD ≥ 2× single-asset maxDD, or correlation to BTC book > +0.3.

**HIT BAR:** Forward portfolio (Jan 2026 → present, or `data/forward` slice) must deliver **Sharpe ≥ 1.0, maxDD ≤ 1.5× BTC maxDD, correlation to BTC ≤ +0.2**. Pre-register universe, weighting, rebalance freq.

**MY CONFIDENCE: Medium.** The diversification math is solid (1.25–1.79× DD for 6 assets vs 6×). The only issue is retrospective selection. Forward test fixes this.

---

### P8. HMM/GARCH Regime as Continuous Bias Modulator — Not Binary Gate

**THESIS:** The engine already computes HMM (P(range)) and GARCH (predicted vol) per 1h bar, mapped to LTF. They're used as *binary* routers (B2 vs FLIP). Using them as *continuous* modulators of position size, stop width, and cooldown inside the bias window may extract more regime alpha than a hard switch.

**MECHANISM:** Current `mode="hmm"` → `use="b2" if P(range)>thresh else "flip"`. Proposed: `size_mult = 0.5 + 0.5 × (1 − P(range))`, `sl_buf_mult = 1.0 + 0.5 × P(range)`, `cooldown_mult = 1.0 + 1.0 × P(range)`. Continuous, differentiable, no new thresholds to tune (uses existing `chop_thresh` as anchor). The HMM/GARCH are already trained on train-prefix only (path-true).

**NEW DATA:** None. Already computed in `v18_streak_halt.py` lines 382-397.

**FALSIFIER:** If continuous modulation (tested across 3 functional forms: linear, sigmoid, piecewise) fails to beat binary gate in both eras on net R, or ex-best-5 negative.

**HIT BAR:** Best continuous modulator must deliver **≥ +25R vs binary gate in IS (champion) AND same sign in OOS**, with maxDD ≤ binary gate.

**MY CONFIDENCE: Low-Medium.** The regime signals exist and are causal. But binary gate already tested many modes (chop, atr_high, hmm, garch, entropy, FD, session, etc.) — continuous may just be a smoother interpolation of the same losing space.

---

### P9. Kelly-Continuous Sizing with Drawdown Constraint — Not Fixed Flat Size

**THESIS:** The book is flat-sized. Kelly on the *empirical trade R distribution* (with drawdown constraint) may outperform flat sizing without the look-ahead trap of sMZX.

**MECHANISM:** Compute Kelly fraction `f* = μ/σ²` on the *rolling* trade R distribution (e.g., last 100 trades, min 30), capped at `f_max = 0.5` and floored at `f_min = 0.1`, with a drawdown brake: if current DD > 15%, multiply size by `(1 − DD/20)`. This is causal (uses only past trades), parameter-light (4 params), and respects the tail-concentrated nature (μ/σ² naturally small for low-WR high-tail).

**NEW DATA:** None. Trade R sequence from engine output.

**FALSIFIER:** If Kelly-sized book (tested across 5 cap/floor/brake configs) fails same-sign in both eras, or net R < flat control, or maxDD > flat control.

**HIT BAR:** Best Kelly config must deliver **≥ +50R net vs flat in IS (champion) AND same sign in OOS**, with maxDD ≤ flat control × 1.1. Report ex-best-5.

**MY CONFIDENCE: Low.** Vol-targeting failed (net up 6/6 but ulcer 3×). Kelly is vol-targeting's cousin. But Kelly uses *trade* vol not *price* vol — different denominator. The Kelly continuous doc exists (`KELLY_CONTINUOUS.md`) but unclear if tested path-true.

---

### P10. ZigZag + Elliott Hybrid Labelling — Algorithmic Wave Count

**THESIS:** A ZigZag (fixed % reversal) + simplified Elliott (impulse 1-2-3-4-5, corrective A-B-C) labelling on 1h swings may identify *where in the macro wave* the 15m bias window sits — e.g., only trade 15m pullbacks in wave-2 or wave-4 of a 1h impulse.

**MECHANISM:** Run ZigZag on 1h closes (reversal % = 2× ATR% or fixed 3%). Label waves: 5-wave impulse → 3-wave correction. Only allow 15m entries when 1h wave label ∈ {2, 4, B} (corrective/pullback phases). This is a *macro filter* on the HTF bias window, not an LTF entry filter. The graveyard closed "4h HTF confirmation" but this is *wave position*, not confirmation.

**NEW DATA:** None. 1h data exists. ZigZag is deterministic on closes.

**FALSIFIER:** If wave-position filter (tested across 3 reversal % settings) fails same-sign in both eras, or gated cohort net R < control, or ex-best-5 negative.

**HIT BAR:** Best wave filter must deliver **≥ +30R vs control in IS (champion) AND same sign in OOS**, with trade count ≥ 70% of control (not just cherry-picking).

**MY CONFIDENCE: Low.** Elliott wave is notoriously subjective. Algorithmic version may be noise. But it's a *different labelling* (like P1/P2) — changes what the system sees at HTF level.

---

## Ranked Order to Run

| Rank | Proposal | Why First |
|------|----------|-----------|
| 1 | **P1: P1/P2 Wave Labelling** | Strongest seed item; no new data; changes vocabulary not filter; pivot chain exists |
| 2 | **P2: Scheduled-Event Gate** | Data on disk; causal; pre-registered test cleanly addresses graveyard gap |
| 3 | **P3: True FS-Only Engine** | Never simulated; 2,900 swings vs 314 priced; different trigger set |
| 4 | **P4: 30m Timeframe** | Untouched middle; time-parameterisation solves bar-count barrier |
| 5 | **P7: Alt Portfolio Forward Test** | Highest leverage if valid; forward data exists; diversification math sound |
| 6 | **P5: Position Resize** | Engineering needed but graveyard explicitly flags as untouched |
| 7 | **P8: Continuous Regime Modulation** | Uses existing causal regime signals; low implementation cost |
| 8 | **P9: Kelly Sizing** | Causal, parameter-light; but vol-targeting failed |
| 9 | **P6: 1m Microstructure** | Requires new data fetch; only genuinely new info set |
| 10 | **P10: ZigZag/Elliott** | Most speculative; algorithmic wave counting is fragile |

---

## What I Need From You

**To run P1 first (highest conviction):**
1. Confirm the P1/P2 labelling spec: wave-1 = first leg after swing confirmation; wave-2 = first retracement ≥ 0.382 × wave-1; wave-3 = continuation past wave-1 extreme. Entry on wave-2 completion (chop cross of wave-2 pivot) in direction of 1h bias.
2. Pre-register the exact gate: which P1/P2 cohorts are tested (wave-2 only? wave-2 + wave-4? all?), and the hit bar (I proposed ≥ +15R IS, same sign OOS, ex-best-5 positive).
3. Confirm forward data usage: should P1/P2 also run on `data/forward/bybit/` as a kill check?

**Alternatively**, if you want P2 (scheduled events) first, I need the pre-registered event window (±N bars) and parameter deltas (SL buffer multiplier, size multiplier, cooldown adder).

Which one do you want to start with, and shall I lock the pre-registration details now?

---
Mimo-V2
I finished the required reading (all four prompt docs, the full graveyard, AGENT_COORDINATION.md, BREAK_KIND.md) and — per your instruction to verify rather than trust — checked the seed list against disk. Corrections first, then the proposals.
Seed-list corrections (this is the "verify" part):
- data/flow/bookDepth/ exists: 1,361 daily zips, 2023-01-01→2026-09-25, 30s snapshots, columns timestamp,percentage,depth,notional, bands ±1..5%. Never read by any harness (only scripts/fetch_binance_*.py and other bots proposal.md mention it). It is IS-only (no 2021-22), so the same-sign-both-eras rule cannot be met with it as-is.
- 30m is tested (HTF_2H_PLANE_TEST.md add.2: costs 84R IS / 55R OOS). Events tested path-true (exp_event_pathtrue.py, killed). flow/metrics, funding, premium1h tested path-true, killed. alt breadth and order-book were already proposed twice in other bots proposal.md.
- CLOSED_DO_NOT_REPEAT.md's "Still open" section is stale: B1 entry (HANDOVER §3: IS −34.9R, fails same-sign) and FS-only (FS_ONLY_ENGINE.md) are both closed. Do not propose them.
- other bots proposal.md contains three prior second-researcher sets (Nemotron P1–P10, Link3.0 P1–P8, LongCat P1–P8). I excluded everything they proposed unless I could specify it materially better.
P1. One forward slice, adjudicated once for every live candidate
THESIS: The forward gate (currently n=5 of 50) is the only uncontaminated measurement the repo owns, and it is being spent one candidate at a time — it should be converted into a single pre-registered, family-wise evaluation that rules on all unadopted survivors simultaneously.
MECHANISM: Every row of the graveyard is retrospective; RETROSPECTIVE_AND_FORWARD.md says so explicitly. Meanwhile the wick gate is on record as HOLD — sole blocker forward gate 5/50, and STACK, skip_decisive, Z-arm-C and exp_retest_fill=0.25 are all parked behind the same wall. Serial one-candidate testing burns the slice on the first arrival. A family-wise rule written now, before n=50 arrives, costs nothing and preserves the slice's status as "never used to choose anything". This is not an edge hypothesis — it is the instrument every other verdict depends on. Nothing in the 31-row graveyard is of this shape.
NEW DATA: data/forward/bybit/ (1,203×15m, 301×1h, 18,049×1m from 2026-09-13 10:03 IST) + _forward_manifest.json. Exists on disk, never used to choose anything. Needs a harness fix: _forward_eval.json's four candidates (CHAMPION_BASE, CHAMPION_N3, KING_BASE, KING_WN3) return identical 5-trade / −3.8275R ledgers, so today it cannot distinguish anything.
FALSIFIER: (a) The harness cannot be made to produce differing post-cutoff ledgers for candidates that differ — then it measures nothing and forward evidence stays a serial bottleneck; or (b) at n=50 the pre-registered rule has no power to separate candidates (only to kill), in which case the direction dies as an adjudicator and should be reported as "kill-only" honestly.
HIT BAR (written before any forward run): (1) all candidates reproduce their pre-cutoff ledgers exactly (500/+325.8, 454/+358.9, 279/+70.2, 253/+60.2); (2) candidates must differ on ≥1 post-cutoff trade or the harness is declared non-discriminating; (3) a candidate passes iff net R > 0 and PF > 1.20 and R/trade > 0.20 on the accumulated slice, with Holm–Bonferroni α=0.05 across the k candidates; (4) evaluated exactly twice — n=50 (kill-only, no adoption) and n=150 (verdict); (5) a candidate that fails is closed permanently.
MY CONFIDENCE: High. It cannot produce an edge, but it is the cheapest thing in this list and every other proposal's real-world value is gated behind it.
P2. Label redesign — spec'd properly, starting with the engine's own chop mark
THESIS: Change the alphabet the engine reads (which events exist at all) instead of filtering the trades it already fires; the first rung is the mark category the swing engine can already emit but the live path never asks for.
MECHANISM: The graveyard is 31 rows of filters on the current four marks. ENTRY_TIME_AUTOPSY then closed the filter search from the other end (nine entry-legal features, AUC ≈ 0.5 except swing_no, which is calendar time). Neither result says anything about a different decomposition: they are statements about a feature space nobody can improve because the trigger set itself is the bottleneck. BREAK_KIND.md:113-115 states the concrete, engine-native first rung: _compute_swings supports a b2_vs_flip_chop mode that emits chop as distinct from B2/FLIP, the live path uses continuous which does not separate it, and it is untested. Above that rung sits a real ZigZag/P1-P2 relabelling pass. Crucially, the three prior sets each proposed this vaguely — Nemotron even asked you to pick the variant after the fact, which is label-shopping. The labelling rule must be fixed in writing before any run, or this becomes the biggest retrospective trap in the repo.
NEW DATA: None. data/bybit/{15m,1h,1m} only; swing chain already carries dir, breaks, fs_at_idx, kind, source.
FALSIFIER: Any pre-registered labelling whose book has trimmed mean ≤ 0 in either era, or ex-best-5 < 0 in either era, or whose mark-level top-decile-vs-bottom-decile AUC does not exceed the current marks' ≈0.5 in both eras.
HIT BAR (written before choosing the labelling): same sign in both eras on both lanes; control ledgers asserted exact first; trimmed mean positive and ≥ 0.8× champion's trimmed mean; ex-best-5 ≥ 0 both eras; mark-level AUC ≥ 0.60 both eras (the current alphabet scores ~0.50, so this is the actual claim being tested); max 3 pre-registered labelling schemes, all reported, no best-of.
MY CONFIDENCE: Medium-high — it is the only representation-level direction, and it is upstream of every closed filter. Held back from high by the label space being large, which is exactly why the single-fix-upfront rule is part of the hit bar.
P3. Is the shipped book significant after the search that produced it?
THESIS: The repo's own two answers to "is this edge real?" disagree (Study 2's deflation says no, the WFO runs say yes), and neither used the actual search record sitting on disk.
MECHANISM: _thesis_deflated_stats*.json builds a synthetic null (n_variants_per_set=40, n_sets=400, estimated_trials=464 = 58 logged experiments × 8) and concludes IS net is unexceptional (p=0.16) while OOS is far below the selection null (p≈1.0, deflation ratio 0.32). Against that, exp_wfo_true and exp_stack_wfo report 104% and 94% walk-forward retention, i.e. not an artifact. Both cannot be the last word: the deflation null never read the 153 result JSONs actually produced by this programme, and trials in one repo are highly correlated, so the effective N is far below 464. Compiling the real trial ledger and computing a deflated Sharpe / White's Reality Check against actual results is a question nobody has asked, and it is the difference between "adopt" and "keep testing".
NEW DATA: None new — the ~150 backtest/tests/_*.json results, experiment_registry.py (112 configs), EXPERIMENT_LOG.md (58 rows). All on disk.
FALSIFIER: The compiled ledger turns out to be unusable (arms not comparable, missing net R, no recorded trial counts) — then the audit cannot be done and the existing crude Study 2 stands as the best available answer.
HIT BAR (written before compiling): (1) report every arm found and every arm excluded for missing data — exclusions can't be chosen by result; (2) compute trial correlation and the effective independent-trial count before computing any p-value; (3) verdict is pass only if deflated p < 0.05 for net R (not gross) on IS and the OOS number exceeds the null that IS-selection alone predicts; (4) report gross and net separately, since Study 2's IS gross passes (p=0.0125) while net does not (p=0.16) and that gap is the whole story.
MY CONFIDENCE: Medium-high on value, medium on outcome — the WFO evidence makes a clean failure unlikely, but the tension is real and resolving it is cheap.
P4. L2 book depth as a GRAY state on the 1h bias layer
THESIS: Liquidity supply — the one information set on disk that no experiment has ever read — tells you which 1h swings are formed in a book thin enough for the move to be noise, and those trades get grayed, not skipped.
MECHANISM: Every closed filter is price-derived, and ENTRY_TIME_AUTOPSY proved price-derived entry features are exhausted. Depth is not collinear with the swing structure the engine already sees: it is the supply side, not the path side. It is also applied at a different object — the 1h bias window at confirmation, not the 15m trade instant — so the autopsy's null does not reach it. And it is specified as GRAY (Rule 18: run to completion, r=0, slot held, loss streak advances), which is the form that measured +28.1R IS / +19.8R OOS for the wick gate while skip measured −39.0R. This is not "a better flow book": metrics/funding/premium are positioning/carry and were tested path-true and killed; depth has never been opened.
NEW DATA: data/flow/bookDepth/BTCUSDT-bookDepth-YYYY-MM-DD.zip, 1,361 files, 2023-01-01→2026-09-25, 30s snapshots, timestamp,percentage,depth,notional, ±1..5% bands, ~28,561 rows/day. On disk. But IS-only — 2021-22 has no bookDepth, so the same-sign-both-eras rule cannot be satisfied.
FALSIFIER: The grayed cohort is net-positive in either evaluation window (graying destroys R); or the depth metric at the 1h confirmation instant is not computable from ≤30s snapshots without reading past that instant (causality failure — this is the M2 trap, so audit inputs before running); or the effect only appears once you pick the band/threshold (then it is a fitted gate and is closed on sight).
HIT BAR (written before any run): because era-replication is impossible, substitute a pre-registered within-IS temporal split: threshold fixed on 2023-01→2024-12, evaluated once on 2025-01→2026-09, plus one independent cross-check on data/btc-fut-era price data with a depth proxy is not permitted (no depth there — so no substitute replication is claimed). Pass = grayed cohort trimmed mean < 0 in the held-out window, book net R improves, ex-best-5 ≥ 0, cascade ≈ 0, and the result must be labelled "single-era evidence, does not satisfy rule 5" regardless of outcome. If you won't accept a single-era result, this is dead on arrival and I should not run it.
MY CONFIDENCE: Medium-low. Genuinely new information and the correct (gray) form, but the era-replication rule — which exists because of seven documented era-flips — cannot be met. That is a real cost, stated up front rather than after the run.
P5. Walk-forward the alt-sleeve selection (the repo's weakest finding)
THESIS: The 13→7→6 alt portfolio is survivorship-selected on the same data that reported it; a past-only selector rolling through 2021→2026 turns it into an honest number without fetching a single bar.
MECHANISM: RETROSPECTIVE_AND_FORWARD.md grades "portfolio 5/6 kills-clean" as highest contamination: "two rounds of selection, all on data that did the selecting." The fix already exists in-repo and has been applied to the BTC config twice (exp_wfo_true.py 104% retention, exp_stack_wfo.py 94% retention) — it has never been applied to the alt screen, which is the claim most in need of it and the cheapest to run. At each step the screen rule (n≥30 both eras is impossible prospectively, so: trailing-12-month net > 0 and n ≥ 15) is fixed in advance, applied only to past data, then the chosen sleeve is scored on the next year. No new data, no new hypothesis — it is the same claim measured correctly.
NEW DATA: None. data/scan-fut/ (16 alts × 15m/1h, covers 2021-2026), existing age10/champion loaders.
FALSIFIER: The walk-forward sleeve's cumulative net ≤ 0, or it fails to beat a single fixed book (champion alone) on both net and drawdown — i.e. the diversification claim was selection.
HIT BAR (written before running): (1) the selection rule is one line, written into the harness docstring first, and is not modified after seeing any fold; (2) report every fold, including folds where the sleeve is empty; (3) pass = walk-forward sleeve net > 0 in both eras as wholes (2021-22 and 2023-2026), and maxDD ratio vs a single book ≤ 0.7 (the claim being tested is 1.25–1.79× improvement, i.e. DD ≤ 0.56–0.8×); (4) no re-tuning of the 6-member composition — the composition must emerge from the rule.
MY CONFIDENCE: Medium-high. The method is proven in-repo, the data is on disk, and the finding being tested is explicitly flagged as the least trustworthy thing produced — so both outcomes are informative.
P6. The B1→B2 unconfirmed window as an uncertainty state (size, don't filter)
THESIS: The engine already knows when it doesn't know; use that window to scale exposure instead of removing trades.
MECHANISM: BREAK_KIND.md:101-106 lists this first among the ideas that survive the label reversals, precisely because it "changes exposure during uncertainty rather than filtering — no trade removed, so Rule 18's slot-cascade does not apply." B1 locks with dir_confirmed=False and the engine then does nothing until B2/FLIP. That latency is engine-acknowledged state, not a price feature, so ENTRY_TIME_AUTOPSY's null (nine price/structural features, AUC≈0.5) does not cover it. The sizing exemption in AGENT_COORDINATION.md applies — sizing does not feed back into trade selection at v18_streak_halt.py, so a post-process size map is a valid measurement. Note this is not "trade B1", which is closed (IS −34.9R, era-flipped).
NEW DATA: None. dir_confirmed and the B1→B2 latency already exist in the swing dicts; the only prerequisite is the size channel v18_streak_halt.py currently lacks (zero hits for equity/size/notional).
FALSIFIER: Any pre-registered size map fails to beat flat 1.0 on trimmed mean in both eras, or raises maxDD above 1.0× the flat book's (then "uncertainty" is not risk), or the B1→B2 latency distribution is so short that almost no trade is ever in the unconfirmed state (the state has no mass).
HIT BAR (written before any run): (1) two maps only, pre-frozen: half while unconfirmed, and half until B1→B2 latency exceeds X× the era's median latency — X fixed from IS only, never re-tuned; (2) pass = trimmed mean improves in both eras on both lanes, maxDD ≤ flat, ex-best-5 ≥ 0, and the identity gate shows the trade sequence byte-identical (sizing exemption requires it); (3) report what fraction of trades actually changes size — if <20%, call it a null regardless of sign.
MY CONFIDENCE: Medium. It is the repo's own sanctioned open list, it is structurally immune to the cascade that killed every gate, but it is still a bet that engine state carries information, and it is blocked behind the size channel (engineering, not research).
P7. Does the second book exist already? Champion × age10 as an in-repo pair
THESIS: The registry holds a structurally different lane with both eras positive and a 53.8% win rate — nobody has measured whether it is actually uncorrelated with the champion, which is the only condition under which running both is worth anything.
MECHANISM: The one thing that transferred is diversification: six near-uncorrelated alt books draw down 1.25–1.79× a single book rather than 6× (mean pairwise monthly-R +0.072 IS / −0.053 OOS). That mechanism has never been applied inside this repo, where age10_dirmatch_swingpause_single_sw10 sits default-off at 130t/+435.7R IS and 76t/+43.2R OOS with seven differing parameters (dir-match, swingpause, no exp_mltf, single-book) — i.e. a genuinely different strategy, not a variant. The honest prior is that two books on one instrument with one shared 1h/15m cascade are probably highly correlated, which is exactly why this is worth 30 minutes rather than an assumption. Any third book (a reversion/fade book for the ~70% non-trending time) must clear the cost arithmetic first: at the champion's stop distances cost is ≈0.24R/trade (445.2 gross → 325.8 net over 500), so a new book needs gross ≥ 0.25R/trade — the 1m book failed at 0.79R/trade cost against 0.018R gross, and stat-arb failed on gross edge before cost (−39.6R gross).
NEW DATA: None for the pair. For any new second book: same data/bybit/ bars; no fetch.
FALSIFIER: Monthly-R correlation between the champion and age10 books ≥ 0.6 in both eras (then the pair adds nothing and the in-repo diversification idea dies); or the combined book's maxDD is not ≤ 0.9× the champion's.
HIT BAR (written before computing): (1) correlation measured on monthly net R of both books, both eras, no threshold chosen afterwards — pass iff |corr| ≤ 0.3 in both eras; (2) combined flat-size book must show maxDD ≤ 0.85× champion alone and net ≥ 1.15× champion alone in both eras; (3) ex-best-3/5 reported on the combined book; (4) for any new second book: pre-registered gross edge ≥ 0.30R/trade before any live-style cost is applied, killed on the desk if the gross number misses.
MY CONFIDENCE: Medium-low on the pair (same instrument, shared cascade — probably correlated), medium on the arithmetic pre-check (cheap, and it stops the next "second book" idea before it wastes a week, as it did for 1m and stat-arb).
P8. The actual-trials audit — no. P8. Joint arm: STACK × wick-gray
THESIS: Two unadopted, same-sign improvements have each been tested alone and never together, and the repo has measured three times that combining interventions does not add.
MECHANISM: exp_trail_half=1 + exp_trail_delay_r=1.0 + exp_skip_decisive=1 is worth IS +325.8→+429.6 / OOS +70.2→+110.5 (reproduced 24/24) and the 1h wick gate is worth +28.1/+19.8 as a gray. Both sit default-off in RESEARCH_POLICY_CORRECTION.md. Nothing in the graveyard covers composition of entry-gray with exit-stack, and the repo has direct evidence interactions are non-additive: gate cascades repeatedly flipped post-process numbers (exp_gate_size_pathtrue: champ OOS +3.6→−4.6), and the mltf_green_r result showed blocking trades hurt because of slot dynamics. So the joint arm could plausibly be better or worse than +132R + +28R, and nobody has looked.
NEW DATA: None. Both mechanisms are already implemented as default-off kwargs.
FALSIFIER: The joint arm is worse than STACK alone in either era (interaction is negative — report it, don't re-tune); or it is worse than the arithmetic sum by more than 20% in either era (interaction is non-additive in an unexplained way).
HIT BAR (written before any run): controls asserted first (500/+325.8, 454/+358.9, 279/+70.2, 253/+60.2); all four arms reported (control, STACK, wick-gray, STACK×wick) — no best-of; pass = joint ≥ STACK in both eras on both lanes AND joint ≥ control with ex-best-5 ≥ 0 in both eras AND cascade ≈ 0 with sequence identity where required; the wick threshold is 6.026 exactly as pinned in WICK_1H_GATE_ADOPTION_RECORD.md, not re-derived, and 6.1 is marked post-hoc as that doc does.
MY CONFIDENCE: Medium-high on it being worth running (30 minutes, two live candidates, interaction proven non-trivial in this repo), low that it is a large number — it is a composition check, not a discovery.
P9. Position lifecycle: resize instead of close (and what blocks it)
THESIS: With exp_mltf=True the book already holds overlapping positions; every lifecycle policy tested so far closed something, and nobody has asked whether reducing risk while keeping the position alive beats exiting.
MECHANISM: This is the seed-list item nobody has touched. Closed rows attack exits (exit-at-FS dead 4/4, pivot trail catastrophic, tighter/wider SL both lose) — but those all realise the loss or give up remaining R. A resize reduces the R denominator on a live position while letting the same swing run, which is a different object from any of them, and it is the only lever left that is not an entry predicate (the graveyard has exhausted those twice over). pyramid/scale-in is closed as adding positions; resize is shrinking an existing one. The blocker is honest and named: v18_streak_halt.py has zero hits for equity/size/notional, so this is engineering-first.
NEW DATA: None. Existing signals + 1m fine data; a standalone simulation harness can compute blended-entry R without touching the engine.
FALSIFIER: Every pre-registered resize policy fails to beat static 1.0 on trimmed mean in both eras, or maxDD rises above 1.0× (then resize only delays losses — the same failure that killed cohort sizing: champion elite-poison +31.0 IS / −12.0 OOS).
HIT BAR (written before any run): (1) two policies only, pre-frozen: halve on a new same-direction signal while ≥1R green, and halve when a same-window cohort reaches 3 positions; (2) pass = trimmed mean beats static 1.0 in both eras on both lanes, maxDD ≤ 1.0×, ex-best-5 ≥ 0, and the trade-key sequence is byte-identical (sizing exemption); (3) report the fraction of trades resized — <20% is a null; (4) this cannot ship until the size channel exists, so a "pass" is a measurement, not an adoption.
MY CONFIDENCE: Medium-low. Explicitly untouched and mechanistically distinct, but the cohort-sizing precedent already failed on the same axis and it is blocked behind engine work owned by the other agent.
Which I'd run first, and what I need from you
Run P1 first. It is roughly a day, it cannot lose money, and it converts the single largest bottleneck (forward gate 5/50, everything parked behind it) from a serial queue into one family-wise judgement — plus the current _forward_eval.json returns identical ledgers for all four candidates, which needs diagnosing regardless. Second, P2, since it is the only representation-level direction and the chop mark rung is engine-native and cheap.
What I need from you:
1. P4's single-era caveat is a policy decision, not a research one — bookDepth has no 2021-22 coverage, so it can never satisfy rule 5. Do you accept a pre-registered within-IS temporal split labelled "single-era, does not satisfy rule 5", or do I drop P4?
2. P2's labelling rule must be fixed before I run anything. Do you want (a) the engine-native chop mark only, (b) a single ZigZag-with-ATR-thresholds pass, or (c) both as the two pre-registered schemes? I will not let you pick after seeing results — that is how the prior three sets' proposals would have become label-shopping.
3. P9 and P6 need the size channel in v18_streak_halt.py, which is the other agent's file. Do you want me to leave them parked until that exists, or spec them as standalone post-process simulations (valid measurement, cannot ship)?
Nothing adopted, no code written, production untouched. Say the word and I'll write this up as backtest/docs/SECOND_RESEARCHER_PROPOSALS.md.

---
