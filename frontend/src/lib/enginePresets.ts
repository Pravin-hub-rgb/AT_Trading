export interface EnginePreset {
  id: string;
  label: string;
  description: string;
  // Complete config sent to backend
  config: {
    version: string;
    tf: string;
    mode: string;
    entry_break: string;
    sl_mode: string;
    sl_pct: number;
    rr_target: number;
    trailing: string;
    trail_distance_r: number;
    breakeven_r: number;
    bias: string;
    min_bars: number;
    regime: string;
    fee_pct: number;
    slippage_pts: number;
    entry_slip_pct: number;
    exit_slip_pct: number;
    funding_rate_pct: number;
    fill_tf: string;
    entry_selection: string;
    htf_ltf: string;
    htf_ltf_ver: string;
    // Engine-specific params
    sl_buf_atr?: number;
    ext_stop_r?: number;
    chop_thresh?: number;
    cooldown_bars?: number;
    max_consecutive_losses?: number;
    atr_low_thresh?: number;
    atr_high_thresh?: number;
    htf_rr?: number;
    window_end?: string;
    exp_mltf?: boolean;
    exp_persist?: number;
    exp_partial_r?: number;
    // v19 specific
    mode?: string; // for v19: "atr_high"
    chop_thresh?: number;
    cooldown_bars?: number;
    max_consecutive_losses?: number;
    exp_mltf?: boolean;
    exp_persist?: number;
    exp_partial_r?: number;
    window_end?: string;
  };
}

export const ENGINE_PRESETS: EnginePreset[] = [
  {
    id: "v19_champion",
    label: "v19 Champion — Retroactive SL (+325.8R IS, +70.1R OOS)",
    description: "Multi-position, retroactive SL, ATR_HIGH regime, 1h→15m",
    config: {
      version: "v19_champion",
      tf: "15m",
      mode: "continuous",
      entry_break: "decisive",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 50,
      regime: "off",
      fee_pct: 0.055,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "off",
      htf_ltf_ver: "v18",
      sl_buf_atr: 0.01,
      ext_stop_r: 3.0,
      chop_thresh: 58.0,
      cooldown_bars: 8,
      max_consecutive_losses: 3,
      atr_low_thresh: 0.35,
      atr_high_thresh: 0.65,
      htf_rr: 3.0,
      window_end: "exit",
      mode: "atr_high",
      exp_mltf: true,
      exp_persist: 7,
      exp_partial_r: 0,
    },
  },
  {
    id: "v19_causal",
    label: "v19 Causal SL — Live-Honest (+248R IS, +80R OOS)",
    description: "Multi-position, causal SL, ATR_HIGH regime, 1h→15m",
    config: {
      version: "v19_causal",
      tf: "15m",
      mode: "continuous",
      entry_break: "decisive",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 50,
      regime: "off",
      fee_pct: 0.055,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "off",
      htf_ltf_ver: "v18",
      sl_buf_atr: 0.01,
      ext_stop_r: 3.0,
      chop_thresh: 58.0,
      cooldown_bars: 8,
      max_consecutive_losses: 3,
      atr_low_thresh: 0.35,
      atr_high_thresh: 0.65,
      htf_rr: 3.0,
      window_end: "exit",
      mode: "atr_high",
      exp_mltf: true,
      exp_persist: 7,
      exp_partial_r: 0,
    },
  },
  {
    id: "v18_bybit",
    label: "v18 Bybit — Streak Halt 5L (+365.7R)",
    description: "HTF-LTF 1h Flip + 15m Decisive, streak halt",
    config: {
      version: "v18",
      tf: "15m",
      mode: "continuous",
      entry_break: "decisive",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 50,
      regime: "off",
      fee_pct: 0.055,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "15m",
      htf_ltf_ver: "v18",
      sl_buf_atr: 0.01,
      ext_stop_r: 1.5,
      chop_thresh: 58.0,
      cooldown_bars: 10,
      max_consecutive_losses: 3,
      atr_low_thresh: 0.35,
      atr_high_thresh: 0.65,
      htf_rr: 3.0,
      window_end: "exit",
    },
  },
  {
    id: "v18_spot",
    label: "v18 Spot — Streak Halt 5L (+331.1R)",
    description: "HTF-LTF 1h Flip + 15m Decisive, streak halt",
    config: {
      version: "v18",
      tf: "15m",
      mode: "continuous",
      entry_break: "decisive",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 50,
      regime: "off",
      fee_pct: 0.05,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "15m",
      htf_ltf_ver: "v18",
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 20,
      max_consecutive_losses: 5,
      atr_low_thresh: 0.35,
      atr_high_thresh: 0.65,
      htf_rr: 3.0,
      window_end: "exit",
    },
  },
  {
    id: "v1_flip",
    label: "v1 Honest — 1h Flip Cap 16d (+57.8R)",
    description: "Baseline 1h Flip fixed 3R, cap 16d",
    config: {
      version: "v1",
      tf: "1h",
      mode: "continuous",
      entry_break: "flip",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 20,
      regime: "off",
      fee_pct: 0.05,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "off",
      htf_ltf_ver: "v1",
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 20,
      max_consecutive_losses: 5,
    },
  },
  {
    id: "v7_timecap",
    label: "v7 TimeCap 16d — 1h Flip (+57.8R)",
    description: "1h Flip with time cap 16d, no cooldown",
    config: {
      version: "v7",
      tf: "1h",
      mode: "continuous",
      entry_break: "flip",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 20,
      regime: "off",
      fee_pct: 0.05,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "off",
      htf_ltf_ver: "v1",
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 0,
      max_consecutive_losses: 5,
    },
  },
  {
    id: "v12_baseline",
    label: "v12 Baseline — 1h Flip + Cooldown 20 (+265.3R)",
    description: "FROZEN BASELINE — HTF-LTF v12, cd20, all years positive",
    config: {
      version: "v12",
      tf: "15m",
      mode: "continuous",
      entry_break: "decisive",
      sl_mode: "swing",
      sl_pct: 0.5,
      rr_target: 3,
      trailing: "off",
      trail_distance_r: 1,
      breakeven_r: 0,
      bias: "off",
      min_bars: 50,
      regime: "off",
      fee_pct: 0.055,
      slippage_pts: 2,
      entry_slip_pct: 0.005,
      exit_slip_pct: 0.01,
      funding_rate_pct: 0,
      fill_tf: "1m",
      entry_selection: "stream",
      htf_ltf: "15m",
      htf_ltf_ver: "v12",
      sl_buf_atr: 0.25,
      ext_stop_r: 1.5,
      chop_thresh: 61.8,
      cooldown_bars: 20,
      max_consecutive_losses: 5,
    },
  },
];

export function getPreset(id: string): EnginePreset | undefined {
  return ENGINE_PRESETS.find(p => p.id === id);
}