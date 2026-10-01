// ONE dropdown. Every book the chart can show, in one list.
//
// This file replaced six separate dropdowns (symbol, version, v19 stop source,
// HTF-LTF, HTF-LTF version, master strategy). Each entry below carries the
// complete config for its book, so picking one sets everything at once and there
// is no second control that can get out of sync with it.
//
// The v19 entries differ by the initial stop source only, which the backend maps
// to exp_causal_sl:
//   RETRO  - stop at the swing's true origin, knowable only after the leg
//            completes. Lookahead. This is what the champion always was.
//   CAUSAL - stop at the running extreme as of the entry bar. Knowable live.
// Both measured on the committed engine by backtest/tests/exp_v19_causal.py.
// backtest/tests/exp_v19_tradediff.py lists every trade they disagree on.

export type BookId = string;
export type SlMode = "causal" | "retro";

export interface BookOption {
  id: BookId;
  label: string;
  shortLabel: string;
  /** "causal" = the shippable rule. "retro" = the retired lookahead rule. */
  slMode?: SlMode;
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
    id: "v19",
    label: "v19 - running-extreme SL (live-implementable)",
    shortLabel: "v19",
    slMode: "causal",
    measured: { isN: 500, isNet: 314.52, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "v19_causal" },
  },
  {
    id: "v19_retired",
    label: "v19 RETIRED rule - reproduces the retracted +325.8R, DO NOT SHIP",
    shortLabel: "RETIRED",
    slMode: "retro",
    measured: { isN: 500, isNet: 325.78, oosN: 279, oosNet: 70.15 },
    config: { ...V19, version: "v19_champion" },
  },
  {
    id: "v19_htf",
    label: "v19 - running-extreme SL + HTF-LTF (1h to 15m)",
    shortLabel: "v19+HTF",
    slMode: "causal",
    measured: { isN: 500, isNet: 314.52, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "v19_causal", htf_ltf: "15m" },
  },
  {
    id: "v19_retired_htf",
    label: "v19 RETIRED + HTF-LTF (1h to 15m) - DO NOT SHIP",
    shortLabel: "RETIRED+HTF",
    slMode: "retro",
    measured: { isN: 500, isNet: 325.78, oosN: 0, oosNet: 0 },
    config: { ...V19, version: "v19_champion", htf_ltf: "15m" },
  },
  {
    id: "v1",
    shortLabel: "v1",
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
    shortLabel: "v7",
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

export const DEFAULT_BOOK = "v19_retro";

export function getBook(id: string): BookOption {
  return BOOK_OPTIONS.find((b) => b.id === id) ?? BOOK_OPTIONS[0];
}
