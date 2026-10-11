// ONE dropdown. Every book the chart can show, in one list.
//
// This file replaced six separate dropdowns (symbol, version, v19 stop source,
// HTF-LTF, HTF-LTF version, master strategy). Each entry below carries the
// complete config for its book, so picking one sets everything at once and there
// is no second control that can get out of sync with it.
//
// There are four champion books here. They all run the same engine and differ
// in at most two knobs: where the initial stop goes, and whether UTC Saturdays
// are skipped.
//
//   CAUSAL       leg extreme incl. entry bar
//   ENTRY-1      leg extreme excl. entry bar
//   CAUSAT-SAT   CAUSAL + skip UTC Saturdays
//   ENTRY1-SAT   ENTRY-1  + skip UTC Saturdays
//
//   CAUSAL  (leg stop)         the leg extreme up to and including the entry
//                               bar. 499 trades / +239.12R net.
//   ENTRY-1 (leg minus entry)  the same extreme but the entry bar itself is
//                               excluded, so the entry's own high or low can
//                               never set the stop. 500 / +325.75R net.
//
// Both are causal. The stop on each reads only bars that closed before the
// entry. They differ on the bars where the entry itself extended the extreme.
//
// Figures here are NET R after costs (55bp fee/side, 2x, 5bp slippage, 1bp
// funding, 1bp cost), re-measured on 2026-10-02 through run_experiment.py.
// Earlier revisions of this file quoted gross R; the two are not comparable
// and the gross numbers read roughly 120R higher.
//
// These four are not the highest-net books in the registry. dirmatch_multi_sw10
// measures +444.21R net and age10_dirmatch_multi_sw10 +417.68R, both above the
// champion. They are not offered here because champion is the book that has
// been walked forward and audited; a higher in-sample net is not a reason to
// change what ships. See backtest/docs/REGISTRY_BOARD.md for the full board.
//
// A third book, CHAMPION RETRO, used to be listed here. It placed the stop on
// the swing's declared origin. It was described as lookahead and retired on
// that basis; that turned out to be wrong. exp_origin_lookahead.py rebuilds the
// swing chain from candles truncated at each swing's own confirmation and finds
// seg.start_px identical every time - the origin price was knowable at the
// entry bar. The two books also collapse to one another the moment the SL rule
// is equalised: the RETRO engine with pivot_rule="leg" is trade-for-trade
// identical to the causal engine.
//
// So RETRO is not deleted and not broken. It is just not offered, because
// CAUSAL and ENTRY-1 place the stop better and the origin rule adds a third
// answer to a question those two already answer. It stays reachable as
// version=v19_champion and pinned in the registry as champion_multi_sw10 if
// the comparison is ever needed again.
//
// VENUE. Every figure in this file, and every figure in the experiment registry,
// is Bybit PERP (symbol BTCUSDT_BYBIT). "BTCUSDT" is Binance spot and is not
// traded on this project. Measuring with that symbol silently moves the data
// window and the trade set and produces numbers that look plausible and match
// nothing - it produced a fake "3 day data gap" and a fake "+5.2 point win rate
// jump" on v18 during the C16 audit. The backtest endpoint defaults to spot, so
// a request that omits symbol= is measuring the wrong market.
//
// The v19 CAUSAL and POST-C16 entries are the same book. Both resolve to
// pivot_rule="leg", which is why they return byte-identical trades. They differ
// only in that POST-C16 spells the rule out at the engine and CAUSAL sets the
// engine's older exp_causal_sl flag, which the leg rule has since made inert.
// They are kept separate so the pre/post C16 diff stays visible in the dropdown,
// not because they measure different things.

export type BookId = string;

export interface BookOption {
  id: BookId;
  label: string;
  shortLabel?: string;
  /** "causal" = a rule a live trader could place. "retro" = the origin pivot. */
  slMode?: "causal" | "retro";
  /** Shown next to the dropdown. */
  hint?: string;
  /** Measured on the committed engine. oos 0 means not yet measured. */
  measured?: { isN: number; isNet: number; oosN: number; oosNet: number };
  config: {
    version: string;
    tf: string;
    /** signal timeframe — the LTF leg */
    mode: string;
    symbol: string;
    /** swing minBars for the LTF leg. Champion = 50. */
    ltf_min_bars: number;
    /** higher timeframe for the window gate. Champion = 1h. */
    htf_tf: string;
    /** swing minBars for the HTF leg. Champion = 10. */
    htf_min_bars: number;
    htf_ltf: string;
    htf_ltf_ver: string;
    min_bars: number;
    fee_pct: number;
    slippage_pts: number;
    entry_slip_pct: number;
    exit_slip_pct: number;
    fill_tf: string;
    sl_buf_atr: number;
    ext_stop_r: number;
    chop_thresh: number;
    cooldown_bars: number;
    max_consecutive_losses: number;
    atr_low_thresh: number;
    atr_high_thresh: number;
    htf_rr: number;
    window_end: string;
  };
}

const V19 = {
  tf: "15m",
  mode: "continuous",
  symbol: "BTCUSDT_BYBIT",
  // the champion harness: sw15 at min_bars=50, sw10 at min_bars=10. These are
  // two different values on two different timeframes and neither is the API
  // default of 14.
  ltf_min_bars: 50,
  htf_tf: "1h",
  htf_min_bars: 10,
  htf_ltf: "off",
  htf_ltf_ver: "v18",
  min_bars: 50,
  fee_pct: 0.055,
  slippage_pts: 2,
  entry_slip_pct: 0.005,
  exit_slip_pct: 0.01,
  fill_tf: "1m",
  sl_buf_atr: 0.01,
  ext_stop_r: 3.0,
  chop_thresh: 58.0,
  cooldown_bars: 8,
  max_consecutive_losses: 3,
  atr_low_thresh: 0.35,
  atr_high_thresh: 0.65,
  htf_rr: 3.0,
  window_end: "exit",
};

// ---------------------------------------------------------------------------
// THE FSENT PAIR - prepended 2026-10-08 so they sit at the TOP of the dropdown.
//
// These two are ONE knob apart and nothing else:
//     fsent_champ_long          mode="atr_high"
//     fsent_champ_long_atr_low  mode="atr_low"
// Every other config value, both books, comes from V19 and is shared with the
// rest of the list. That is what makes them worth comparing side by side on one
// chart: same risk model, same costs, same swing definition, opposite sign on the
// regime selector.
//
// Neither is a drop-in for the old shipping entry. "unified" is
// champion_multi_sw10_leg, 499t / +239.12R, and it has NO directional FS entry -
// it trades the FS print on neither side. These two set
// exp_fs_entry_side="long": longs enter at the swing FS print, shorts still enter
// at the break. That single change is why the trade count moves from 499 to 528.
//
// The registry pins are the numbers in `measured` and the reason the dropdown
// label repeats them: this list is hand-maintained and independent of the Python
// registry, so the figures are quoted here rather than fetched.
//
// OWNER'S DRAWDOWN BUDGET IS 29R (set 2026-10-08). Both books fit: the base at
// 13.42R IS / 11.88R OOS, atr_low at 28.90R IS / 14.60R OOS. Neither is promoted -
// see method/OWNER_SCORECARD_MODES.md and method/MODE_DURATION_CALENDAR.md.
// ---------------------------------------------------------------------------

export const BOOK_OPTIONS: BookOption[] = [
  {
    id: "fsent_champ_long",
    label: "1. FSENT CHAMP LONG  —  OLD ENGINE (UNPATCHED) - IS 528t +533.4R dd13.4 | OOS 311t +239.6R dd11.9",
    shortLabel: "OLD ENGINE",
    slMode: "causal",
    hint: "UNPATCHED - the shipping engine, unchanged. Its swing marks come from firstswing.py exactly as it ships today. Compare this against entry 2 below.",
    measured: { isN: 528, isNet: 533.37, oosN: 311, oosNet: 239.59 },
    config: { ...V19, version: "fsent_champ_long", ext_stop_r: 0.0 },
  },
  {
    // ---- THE PAIRED SECOND HALF. Entry 1 above vs entry 2 below is the whole
    // ---- comparison: same candles, same strategy, same parameters. ONE thing
    // ---- differs - which engine built the swing chain.
    id: "fsent_champ_long_B1PATCH",
    label: "2. FSENT CHAMP LONG  —  NEW ENGINE (B1 ARMING PATCHED) - IS 542t +649.4R dd15.6 | OOS 311t +266.7R dd14.9",
    shortLabel: "NEW ENGINE",
    slMode: "causal",
    hint: "PATCHED - only the B1 arming rule in the swing chain is different. firstswing.py is NOT modified; the patched engine is built alongside it. A break that used to be suppressed while arming was deferred is now accepted when the pivot it broke was sealed on an earlier bar. Open this in one window and OLD ENGINE in the other and compare the B1 marks directly.",
    measured: { isN: 542, isNet: 649.41, oosN: 311, oosNet: 266.70 },
    config: { ...V19, version: "fsent_champ_long_B1PATCH", ext_stop_r: 0.0 },
  },
  {
    id: "fsent_champ_long_atr_low",
    label: "FSENT CHAMP LONG + atr_low (regime sign flipped) - IS 641t +721.3R dd28.9 | OOS 315t +280.7R dd14.6",
    shortLabel: "FSENT-ATRLOW",
    slMode: "causal",
    hint: "one knob from the book above: atr_high -> atr_low, so decisive windows are taken when 15m bars are QUIET instead of big - more trades, more R, deeper drawdown",
    measured: { isN: 641, isNet: 721.30, oosN: 315, oosNet: 280.70 },
    config: { ...V19, version: "fsent_champ_long_atr_low", ext_stop_r: 0.0 },
  },
  {
    id: "fsent_champ_long_mcloff",
    label: "FSENT CHAMP LONG MCL-OFF (loss-run cutoff OFF) - IS 573t +566.2R dd15.1 | OOS 334t +274.4R dd14.2",
    shortLabel: "MCL-OFF",
    slMode: "causal",
    hint: "the base book with ONE integer changed: max_consecutive_losses 3 -> 0, so the 3-loss halt stops cutting the recovery trade that follows every streak. This is the ONLY book in the family that clears a null in BOTH eras - paired permutation p = 0.0312 in sample and 0.0117 out of sample (exp_null_audit.py, 4000 draws) - and the only one whose period control is POWERED in both eras, b = +1.21 at t = 3.37 and b = +1.86 at t = 3.97. Zero negative half-years out of 12. Earns LESS than the base in sample by design (-32.8R IS) and MORE out of sample (+34.6R). Its out-of-sample era is 2021-22, reused old data, NOT a holdout - see method/OOS_IS_NOT_A_HOLDOUT.md",
    measured: { isN: 573, isNet: 566.20, oosN: 334, oosNet: 274.36 },
    config: { ...V19, version: "fsent_champ_long_mcloff", ext_stop_r: 3.0, max_consecutive_losses: 0 },
  },
    {
      id: "fsent_sig_multi",
      label: "SIG MULTI (serial, FS on shorts) - IS 329t +484.6R dd13.4 | OOS 195t +219.8R dd7.6",
      shortLabel: "SIG-MULTI",
      slMode: "causal",
      hint: "RANKED #1 of 35 on the rolling-weighted score, and the most DIFFERENT book here. Every one of its rolling 50-trade windows was profitable - the worst 50-trade stretch in the whole sample is still +10.0R. Zero negative half-years, zero negative years, and zero startup drawdown, meaning it has never once gone below where it started. Median drawdown from ANY start date over one year is 8.95% against 12.48% for FSENT-LONG. Its paired permutation is p 0.9283 / 0.9138, i.e. no edge distinguishable from reshuffling the parent, so it is a candidate on BEHAVIOUR and not on evidence of an edge.",
      measured: { isN: 329, isNet: 484.59, oosN: 195, oosNet: 219.82 },
      config: { ...V19, version: "fsent_sig_multi", ext_stop_r: 3.0 },
    },
    {
      id: "fsent_sig_multi_htffs",
      label: "SIG MULTI + HTF-FS (flip bucket on FS) - IS 434t +666.3R dd17.8 | OOS 221t +234.5R dd8.0",
      shortLabel: "SIG-MULTI+HTFFS",
      slMode: "causal",
      hint: "RANKED #3 of 35 and the NEWEST arm in this family - one parameter (exp_htf_fs_entry='flip') added to SIG MULTI. Zero negative half-years, zero negative years, every rolling 50 and rolling 100 window profitable, zero startup drawdown, and it is one of only five books in the family that survives deleting its best 10% of trades (+85.3R). Its bad-luck tail is the shallowest of any large book: from ANY start date the worst 1-year drawdown is 17.82% but the 10th percentile is 6.85%. The honest caveat: p 0.5091 / 0.9708 - behaves beautifully, and shows no edge.",
      measured: { isN: 434, isNet: 666.32, oosN: 221, oosNet: 234.48 },
      config: { ...V19, version: "fsent_sig_multi_htffs", ext_stop_r: 3.0 },
    },
    {
      id: "fsent_champ_long_htffs",
      label: "FSENT CHAMP LONG HTF-FS (flip bucket on FS) - IS 770t +897.9R dd19.8 | OOS 415t +300.4R dd14.4",
      shortLabel: "HTF-FS",
      slMode: "causal",
      hint: "The HTF-FS entry on the champion book, and the strongest single arm in the family on return-to-drawdown: 45.4 net per unit of drawdown, better than anything else here including MCL-OFF at 37.4. Five parameters, the same complexity as MCL-OFF. All eight in-sample half-years positive. But it recovers its own worst drawdown in TWO TRADES and its out-of-sample permutation is 0.5956, and it is the one book whose tail dependence degrades out of sample - top 10% of trades contribute 116.9% there. Look at it on the chart; do not read the net as a verdict.",
      measured: { isN: 770, isNet: 897.94, oosN: 415, oosNet: 300.43 },
      config: { ...V19, version: "fsent_champ_long_htffs", ext_stop_r: 3.0 },
    },
    {
      id: "fsent_champ_long_mcloff_htf15",
      label: "MCL-OFF + HTF15 swing rule - IS 520t +616.2R dd17.3 | OOS 280t +254.9R dd16.9",
      shortLabel: "MCL-OFF+HTF15",
      slMode: "causal",
      hint: "MCL-OFF (the loss-run cutoff turned off) combined with the tighter htf15 swing rule. Ranked #9 of 35. Zero negative half-years and zero negative years, median 1-year drawdown from any start date 13.14%, and the strongest in-sample permutation of any book that has zero negative half-years: p 0.0115. Out of sample it is 0.1445 - the best p any zero-negative-half-year book has on the far side, though still short of 0.05. Worth watching rather than adopting.",
      measured: { isN: 520, isNet: 616.17, oosN: 280, oosNet: 254.88 },
      config: { ...V19, version: "fsent_champ_long_mcloff_htf15", ext_stop_r: 3.0, htf_min_bars: 15 },
    },
    {
      id: "fsent_champ_long_htfesmcl4",
    label: "FSENT CHAMP LONG HTF-FS + MCL4 - IS 793t +917.8R dd27.7 | OOS 437t +326.2R dd14.2",
    shortLabel: "HTF-FS+MCL4",
    slMode: "causal",
    hint: "the highest-net book here - but read this: it trades 1.47x more than FSENT-LONG at only 1.10x the R per trade, and that 1.10x has a t of 0.46, so nearly all the extra return is MORE BETS rather than a better bet. It also collapses the HTF flip/decisive/b2 regime buckets into one set, so the book stops telling regimes apart. Drawdown nearly doubles to 27.7R. Look at it on the chart, not as a winner.",
    measured: { isN: 793, isNet: 917.80, oosN: 437, oosNet: 326.22 },
    config: {
      ...V19,
      version: "fsent_champ_long_htfesmcl4",
      ext_stop_r: 3.0,          // matches the registry pin for THIS book
      max_consecutive_losses: 4,
    },
  },
  {
    id: "fsent_sig_full",
    label: "FSENT SIG FULL (serial, FS entry on shorts) - IS 234t +295.8R dd10.8 | OOS 152t +194.4R dd7.0",
    shortLabel: "FSENT-SIG",
    slMode: "causal",
    hint: "one position at a time, never overlapping - the lowest drawdown in the set; shorts enter at the FS print but the LONGS carry the P&L",
    measured: { isN: 234, isNet: 295.83, oosN: 152, oosNet: 194.44 },
    config: {
      ...V19,
      version: "fsent_sig_full",
      ext_stop_r: 3.0,        // NOT 0.0 - this is a different book from the pair above
      max_consecutive_losses: 3,
    },
  },
  {
    id: "fsent_champ_short",
    label: "FSENT CHAMP SHORT (FS entry on SHORT side - the mirror) - IS 533t +600.6R dd17.6 | OOS 312t +239.5R dd23.9",
    shortLabel: "FSENT-SHORT",
    slMode: "causal",
    hint: "the fsent_champ_long mirror - shorts enter at the FS print and longs at the break; same knob count, opposite side",
    measured: { isN: 533, isNet: 600.60, oosN: 312, oosNet: 239.53 },
    config: { ...V19, version: "fsent_champ_short", ext_stop_r: 0.0 },
  },
  {
    id: "fsent_sig_trail_delay1",
    label: "FSENT SIG TRAIL DELAY1 (half profit + trail after +1R) - IS 199t +418.5R dd13.3 | OOS 123t +182.0R dd7.5",
    shortLabel: "SIG-TRAIL",
    slMode: "causal",
    hint: "sig_full plus two knobs only - bank half at the midpoint, then trail the rest after +1R - fewer trades, more R, same serial one-position behaviour",
    measured: { isN: 199, isNet: 418.51, oosN: 123, oosNet: 182.01 },
    config: {
      ...V19,
      version: "fsent_sig_trail_delay1",
      ext_stop_r: 3.0,
      max_consecutive_losses: 3,
    },
  },
  {
    id: "champion_causal",
    label: "CHAMPION CAUSAL (leg stop) - ships - IS 499t +239.1R",
    shortLabel: "CAUSAL",
    slMode: "causal",
    hint: "stop at the leg extreme up to the entry bar - knowable live - the pinned shipping book",
    measured: { isN: 499, isNet: 239.12, oosN: 280, oosNet: 72.8 },
    config: { ...V19, version: "unified" },
  },
  {
    id: "utcsat_causal",
    label: "CHAMPION CAUSAL + skip UTC-Saturday - 453t +279.5R",
    shortLabel: "CAUSAT-SAT",
    slMode: "causal",
    hint: "causal stop, UTC Saturdays skipped - 57 of the 86 removed entries were Saturday and losing",
    measured: { isN: 453, isNet: 279.47, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "utcsat_causal" },
  },
  {
    id: "utcsat_entry_minus_1",
    label: "CHAMPION ENTRY-1 + skip UTC-Saturday - 454t +358.9R",
    shortLabel: "ENTRY1-SAT",
    slMode: "causal",
    hint: "entry-bar excluded stop, UTC Saturdays skipped - both settled at the entry bar",
    measured: { isN: 454, isNet: 358.92, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "utcsat_entry_minus_1" },
  },
  {
    id: "champion_entry_minus_1",
    label: "CHAMPION ENTRY-1 (leg extreme, entry bar excluded) - 500t +325.8R net",
    shortLabel: "ENTRY-1",
    slMode: "causal",
    hint: "same as CAUSAL but the stop ignores the entry bar's own extreme - sits beside the RETRO book, not beside CAUSAL",
    measured: { isN: 500, isNet: 325.75, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "entry_minus_1" },
  },
  {
    id: "v1",
    label: "v1 Honest — 1h Flip cap 16d",
    hint: "baseline · 1h flip, fixed 3R, cap 16d",
    config: {
      ...V19,
      version: "v1",
      tf: "1h",
      htf_tf: "1h",
      htf_ltf_ver: "v1",
      ltf_min_bars: 20,
      htf_min_bars: 20,
      min_bars: 20,
      fee_pct: 0.05,
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 20,
      max_consecutive_losses: 5,
    },
  },
  {
    id: "v7",
    label: "v7 TimeCap 16d — 1h Flip, no cooldown",
    hint: "v1 with the cooldown removed",
    config: {
      ...V19,
      version: "v7",
      tf: "1h",
      htf_tf: "1h",
      htf_ltf_ver: "v1",
      ltf_min_bars: 20,
      htf_min_bars: 20,
      min_bars: 20,
      fee_pct: 0.05,
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 0,
      max_consecutive_losses: 5,
    },
  },
];

// The book the chart opens on. Was "v19_retro", which was the 500t origin-pivot
// book - the wrong default to ship, and an id that no longer exists here.
//
// Unchanged deliberately on 2026-10-08 when the fsent pair was prepended: the
// dropdown opening on the pair is the point of adding it, but silently moving
// everyone's landing book is not. Note that getBook() below falls back to
// BOOK_OPTIONS[0], which is now "fsent_champ_long" - so an id that no longer
// resolves lands on the fsent base rather than on champion_causal. That is the
// intended fallback, but it is a behaviour change and it is stated here.
export const DEFAULT_BOOK = "champion_causal";

export function getBook(id: string): BookOption {
  return BOOK_OPTIONS.find((b) => b.id === id) ?? BOOK_OPTIONS[0];
}
