// BTC Master — one swing one trade, repaint-fixed, touchable SL
// Verified 2026-09-06 via _rerun_master_sweep.py — ONE SWING ONE TRADE: after B2 at 17:30, 19:00/21:30 FLIPs from same swing ignored.
// Method: stream + opposite-dir touchable (max high since prev_end) + 1m fills + 0.05%+2pt FULL window, OWN TF.
import type { BtcBacktestParams, BtcTf } from "./btcApi";

export interface BtcMasterMode {
  value: string;
  label: string;
  hint: string;
  desc: string[];
  ref: string;
  bestTf: BtcTf;
  preset: Partial<BtcBacktestParams>;
}

export const BTC_MASTER_MODES: BtcMasterMode[] = [
  {
    value: "flip1h20",
    label: "#1 Flip Fixed 3R (1h) — Cap 16d",
    hint: "BEST 1h IS — 151tr 39.7% +74.0 → +57.8 net (cap16) | FULL 2023-26: 355tr 31.5% +25.2 net +0.07/tr fragile",
    desc: [
      "RANK #1 on IS (2025-26). 1h FLIP mb20 fixed 3R BE0 + time cap 16d — v1 is now cap 16 default (old cap 0 101tr +51.2 removed). IS: 151 tr / 39.7% win / +74.0 base → +57.8 net, PF 0.78 maxDD 10.0, cap 16d: 27 Jan 114d -1R → 16d +0.289R, trades 101→151.",
      "FULL 2023-26 (live 1.93M x1m, 32259 x1h): 355 tr / 31.5% win / +25.2 net +0.07/tr — fragile, -35R in 2023 chop. Keep as regime gate for HTF-LTF, not standalone profit engine.",
      "Stream + touchable SL + one-swing-one-trade + 1m fills, fees 0.05%+2pt. Old snapshot in backup_pre2023/.",
    ],
    ref: "1h IS: 151 tr / 39.7% +74.0→+57.8 net | FULL 2023-26: 355 tr / 31.5% +25.2 net (one swing one trade, cap16)",
    bestTf: "1h",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "off", breakevenR: 0, minBars: 20, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip1h30",
    label: "#2 Flip Trail 30 (1h)",
    hint: "1h flip mb30 — 132tr 28.8% +43.1 → +28.6 net.",
    desc: ["RANK #2. 1h FLIP mb30 swing-trail BE0.", "FULL window: 132 tr / 28.8% win / +43.1 → +28.6 net."],
    ref: "1h: 132 tr / 28.8% win / +43.1 base → +28.6 net",
    bestTf: "1h",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 30, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "decisive1h30",
    label: "#3 Decisive Trail 30 (1h)",
    hint: "1h decisive mb30 — 159tr 23.9% +39.1 → +22.1 net.",
    desc: ["RANK #3. 1h decisive mb30 swing-trail BE0.", "FULL window: 159 tr / 23.9% win / +39.1 → +22.1 net."],
    ref: "1h: 159 tr / 23.9% win / +39.1 base → +22.1 net",
    bestTf: "1h",
    preset: { entryBreak: "decisive", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 30, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip1h20t",
    label: "#4 Flip Trail 20 (1h)",
    hint: "1h trail mb20 — 152tr 27.0% +28.0 → +11.0 net.",
    desc: ["RANK #4. 1h FLIP mb20 swing-trail BE0.", "FULL window: 152 tr / 27.0% win / +28.0 → +11.0 net."],
    ref: "1h: 152 tr / 27.0% win / +28.0 base → +11.0 net",
    bestTf: "1h",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 20, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip50",
    label: "#5 Flip Trail 50 (15m)",
    hint: "15m FLIP mb50 — 390tr 22.1% +90.5 → +8.8 net.",
    desc: ["RANK #5. 15m FLIP mb50 swing-trail BE0.", "FULL window: 390 tr / 22.1% win / +90.5 → +8.8 net."],
    ref: "15m: 390 tr / 22.1% win / +90.5 base → +8.8 net",
    bestTf: "15m",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 50, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "decisive50",
    label: "#6 Decisive Trail 50 (15m)",
    hint: "15m decisive mb50 — 446tr 21.7% +91.0 → +5.3 net.",
    desc: ["RANK #6. 15m decisive mb50 swing-trail BE0.", "FULL window: 446 tr / 21.7% win / +91.0 → +5.3 net."],
    ref: "15m: 446 tr / 21.7% win / +91.0 base → +5.3 net",
    bestTf: "15m",
    preset: { entryBreak: "decisive", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 50, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "sniper",
    label: "#7 Sniper 3R (15m)",
    hint: "Sniper — 327tr 19.0% +22.9 → -55.5 net.",
    desc: ["RANK #7. 15m FLIP mb20 fixed 3R BE1 + bias+streak.", "FULL window: 327 tr / 19.0% win / +22.9 → -55.5 net."],
    ref: "15m: 327 tr / 19.0% win / +22.9 base → -55.5 net",
    bestTf: "15m",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "off", breakevenR: 1, minBars: 20, bias: "15m", regime: "streak_311", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "decisive30",
    label: "#8 Decisive Trail 30 (15m)",
    hint: "15m decisive mb30 — 610tr 23.8% +31.9 → -78.1 net.",
    desc: ["RANK #8. 15m decisive mb30 swing-trail BE0.", "FULL window: 610 tr / 23.8% win / +31.9 → -78.1 net."],
    ref: "15m: 610 tr / 23.8% win / +31.9 base → -78.1 net",
    bestTf: "15m",
    preset: { entryBreak: "decisive", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 30, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip30",
    label: "#9 Flip Trail 30 (15m)",
    hint: "15m flip mb30 — 513tr 22.2% +39.3 → -76.1 net (actually #8 better).",
    desc: ["RANK #9. 15m FLIP mb30 swing-trail BE0.", "FULL window: 513 tr / 22.2% win / +39.3 → -76.1 net."],
    ref: "15m: 513 tr / 22.2% win / +39.3 base → -76.1 net",
    bestTf: "15m",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 0, minBars: 30, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "baseline",
    label: "#10 Baseline (ship) (15m)",
    hint: "Baseline — 467tr 16.5% -11.2 → -87.9 net.",
    desc: ["RANK #10. Ship baseline decisive mb14 fixed 3R BE1.", "FULL window: 467 tr / 16.5% win / -11.2 → -87.9 net."],
    ref: "15m: 467 tr / 16.5% win / -11.2 base → -87.9 net",
    bestTf: "15m",
    preset: { entryBreak: "decisive", slMode: "swing", rrTarget: 3, trailing: "off", breakevenR: 1, minBars: 14, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "trail_max_r",
    label: "#11 Trailing Max R (15m)",
    hint: "Dead — 806tr +18.2 → -138.9 net.",
    desc: ["RANK #11. Decisive mb20 trail BE1.", "FULL window: 806 tr / 20.1% win / +18.2 → -138.9 net."],
    ref: "15m: 806 tr / 20.1% win / +18.2 base → -138.9 net",
    bestTf: "15m",
    preset: { entryBreak: "decisive", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 1, minBars: 20, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip_bias",
    label: "#12 FLIP + 15m Bias (15m)",
    hint: "Dead — 643tr -8.2 → -154.4 net.",
    desc: ["RANK #12. FLIP mb14 bias.", "FULL window: 643 tr / 16.2% win / -8.2 → -154.4 net."],
    ref: "15m: 643 tr / 16.2% win / -8.2 base → -154.4 net",
    bestTf: "15m",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "off", breakevenR: 1, minBars: 14, bias: "15m", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
  {
    value: "flip_quality",
    label: "#13 FLIP Quality (15m)",
    hint: "Dead — 767tr -17.8 → -208.8 net.",
    desc: ["RANK #13. FLIP mb14 trail BE1.", "FULL window: 767 tr / 18.4% win / -17.8 → -208.8 net."],
    ref: "15m: 767 tr / 18.4% win / -17.8 base → -208.8 net",
    bestTf: "15m",
    preset: { entryBreak: "flip", slMode: "swing", rrTarget: 3, trailing: "swing", breakevenR: 1, minBars: 14, bias: "off", regime: "off", feePct: 0.05, slippagePts: 2 },
  },
];

export const BTC_MASTER_DEFAULT = "flip1h20";
