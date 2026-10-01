// One dropdown, two books. Each option is a complete config sent to the backend.
//
// The only difference between them is the initial stop source, which the backend
// maps to exp_causal_sl:
//   RETRO  - stop at the swing's true origin. That origin is only knowable after
//            the leg completes, so placing a stop there at the entry bar is
//            lookahead. This is what the champion has always been run as, and it
//            is where +325.78R comes from.
//   CAUSAL - stop at the running extreme as of the entry bar. Knowable live.
//            IS 494t/+247.96R, OOS 282t/+80.01R.
//
// Both sets of numbers are measured on the committed engine by
// live_stuff/tests/exp_v19_causal.py. They are not projections.
// live_stuff/tests/exp_v19_tradediff.py lists every trade the two disagree on.

export type SlMode = "retro" | "causal";

export interface EnginePreset {
  id: string;
  label: string;
  shortLabel: string;
  slMode: SlMode;
  /** Measured on the committed engine, IS and OOS. */
  measured: { isN: number; isNet: number; oosN: number; oosNet: number };
  /** Sent to the backend with every request. */
  config: {
    version: string;
    tf: string;
    mode: string;
    symbol: string;
    htf_ltf: string;
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

const SHARED = {
  tf: "15m",
  mode: "continuous",
  symbol: "BTCUSDT_BYBIT",
  htf_ltf: "off",
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

export const ENGINE_PRESETS: EnginePreset[] = [
  {
    id: "v19_retro",
    label: "v19 RETRO stop â€” lookahead, higher IS",
    shortLabel: "RETRO",
    slMode: "retro",
    measured: { isN: 500, isNet: 325.78, oosN: 279, oosNet: 70.15 },
    config: { ...SHARED, version: "v19_champion" },
  },
  {
    id: "v19_causal",
    label: "v19 CAUSAL stop â€” live-honest, better OOS",
    shortLabel: "CAUSAL",
    slMode: "causal",
    measured: { isN: 494, isNet: 247.96, oosN: 282, oosNet: 80.01 },
    config: { ...SHARED, version: "v19_causal" },
  },
];

export function getPreset(id: string): EnginePreset | undefined {
  return ENGINE_PRESETS.find((p) => p.id === id);
}
