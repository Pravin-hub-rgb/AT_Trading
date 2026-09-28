"""PIN THE OUTLIER - which trade produced +2942R, and did it respect the
max_hold cap?

The autopsy showed is/decisive: n=16, net=+2947.5R, MEDIAN r = -0.105,
max_r = 2942.7. So a single trade carries the entire result.

This prints the top trades with bars_held, so we can see whether the
hold cap was honoured. If bars_held >> max_hold_min, the exit was taken at
the wrong bar and the R is an artefact of the harness, not the strategy.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

import scalp_1m_engine as E  # noqa: E402

E.install_b1_key()
from src.btc.btc_routes import _compute_swings  # noqa: E402
from src.walker import FlowCandle  # noqa: E402
from exp_5m_confirm import load_book  # noqa: E402

MAX_HOLD = 240  # must match the engine default


def main():
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c1m = data["fine"]
        flow = [FlowCandle(date=c["date"], open=float(c["open"]),
                           high=float(c["high"]), low=float(c["low"]),
                           close=float(c["close"])) for c in c1m]
        sw = _compute_swings(flow, "continuous", min_bars=10)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        tr = E.simulate_1m_scalp(c1m, sw, wins, entry_break="decisive",
                                 target_r=2.0, sl_buf_atr=0.01,
                                 max_concurrent=1)
        tr.sort(key=lambda t: -float(t["r_multiple"]))
        over = [t for t in tr if int(t["bars_held"]) > MAX_HOLD]
        print(f"\n{'=' * 78}\n{scope.upper()}  n={len(tr)}  "
              f"net={sum(float(t['r_multiple']) for t in tr):+.1f}R  "
              f"trades exceeding the {MAX_HOLD}-bar hold cap: {len(over)}")
        print(f"{'R':>11} {'bars_held':>11} {'outcome':>10} {'entry':>10} "
              f"{'exit':>10} {'risk':>9}")
        for t in tr[:6]:
            flag = "  <-- EXCEEDS CAP" if int(t["bars_held"]) > MAX_HOLD else ""
            print(f"{float(t['r_multiple']):>11.1f} {t['bars_held']:>11} "
                  f"{t['outcome']:>10} {t['entry_price']:>10} "
                  f"{t['exit_price']:>10} {t['risk']:>9}{flag}")


if __name__ == "__main__":
    main()
