// ONE dropdown. Every book the chart can show, in one list.
//
// This file replaced six separate dropdowns (symbol, version, v19 stop source,
// HTF-LTF, HTF-LTF version, master strategy). Each entry below carries the
// complete config for its book, so picking one sets everything at once and there
// is no second control that can get out of sync with it.
//
// There are two champion books and they differ in ONE thing - where the initial
// stop goes. That one thing is the entire difference between 500 trades and 499.
//
//   RETRO  (origin stop) - stop at the swing's declared origin. That origin is
//           only knowable once the whole leg has completed, so it is FUTURE DATA
//           at the entry bar. Lookahead. 500t / +325.78R. Research baseline.
//   CAUSAL (leg stop)    - stop at the swing's own extreme up to and including
//           the entry bar. Knowable at that bar. 499t / +239.12R. This ships.
//
// They are the same signal generator, the same gates, the same fills. The two
// books differ on 19 of ~500 trades. Measured 2026-10-02 on unified.py with
// pivot_rule "origin" vs "leg"; both pins reproduce.
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

export const BOOK_OPTIONS: BookOption[] = [
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
    id: "champion_retro",
    label: "CHAMPION RETRO (origin stop) - LOOKAHEAD, research only - IS 500t +325.8R",
    shortLabel: "RETRO",
    slMode: "retro",
    hint: "stop at the swing's true origin - only knowable after the leg completes - do not ship",
    measured: { isN: 500, isNet: 325.78, oosN: 279, oosNet: 70.15 },
    config: { ...V19, version: "v19_champion" },
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

// The shipping book. Was "v19_retro", which was the 500t origin-pivot book -
// the wrong default to ship, and an id that no longer exists here.
export const DEFAULT_BOOK = "champion_causal";

export function getBook(id: string): BookOption {
  return BOOK_OPTIONS.find((b) => b.id === id) ?? BOOK_OPTIONS[0];
}
