"""CAUSAL DIRECTION-MATCH ON THE SIGNAL PLANE - does it survive being legal?

The gap this closes: exp_dirmatch_causality.py and exp_causal_dirmatch_path.py
only ever ran on multi books (champion_multi_sw10_leg, dirmatch_multi_sw10).
The causal replacement fsent_champ_long / fsent_champ_short is therefore also
multi. Nothing has ever tested the causal dirmatch filter on a
max_positions=1 book, which is the plane this work is about.

What the filter is, in engine terms (test_experiments_craze.py section 3g):

    exp_require_dir_match=1   take the LTF signal only if the containing 15m
                              swing points the same way
    exp_dir_causal=1          the one line that makes it legal - ignore any swing
                              whose confirmed_at_idx is after the entry bar

Without exp_dir_causal the filter reads the swing's FINAL direction, which is
settled a median of 8 hours after the entry, and that label is the trade's own
outcome. That is the look-ahead already caught and quarantined. With it, the
filter only reads labels that exist at the entry bar.

Question asked here, per book, both eras:

    does a legal direction-match ADD anything to a clean signal book?

A filter that only removes trades shrinks n and leaves R/trade flat; one that
finds something raises R/trade. Both are reported, and the honest answer is
allowed to be "no".

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_signal_causal_dirmatch.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_signal_causal_dirmatch.json"

from exp_full_metrics import compute  # noqa: E402
from exp_signal_metrics import (  # noqa: E402
    load_era, signal_books,
)

# The bases worth testing: every clean signal book with enough trades to say
# anything. The whole plane is included rather than a hand-picked shortlist,
# because picking the bases after seeing which one improved is how a null
# result gets manufactured.
MIN_N = 30


def main() -> int:
    t0 = time.time()
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from experiment_registry import EXPERIMENTS

    books, _skip = signal_books()
    print("signal books to test: %d" % len(books), flush=True)
    sim = build_family_module()

    payload = {
        "stage": "signal_causal_dirmatch",
        "question": ("does exp_require_dir_match=1 WITH exp_dir_causal=1 add "
                     "anything to a clean signal book?"),
        "note": ("the causal guard is what makes it legal; without it the same "
                 "knob is the quarantined look-ahead"),
        "configs": {},
    }

    for era in ("is", "oos"):
        print("\n=== bybit %s ===" % era.upper(), flush=True)
        data = load_era(era)
        for i, key in enumerate(books, 1):
            cfg = EXPERIMENTS[key]
            base = {**BP, **cfg["params"]}
            base.setdefault("exp_partial_r", 0.0)
            sw = get_swings(data, cfg.get("swing") or "sw10")
            args = (data["c1h"], sw, data["c15"], data["sw15"])
            kw = {"fine_ltf": data["fine"]}

            def run(extra):
                out = sim(*args, **kw, **{**base, **extra})
                tr = out["ltf_trades"] if isinstance(out, dict) else out
                rs = [net_r([t]) for t in tr]
                ds = [t.get("entry_date", "") for t in tr]
                return compute(rs, ds)

            try:
                m0 = run({})
                m1 = run({"exp_require_dir_match": 1, "exp_dir_causal": 1})
            except Exception as e:                        # noqa: BLE001
                print("  [%d/%d] %-38s ERROR %s" % (i, len(books), key, e),
                      flush=True)
                continue

            if not (m0.get("n", 0) >= MIN_N and m1.get("n", 0) >= 1):
                continue
            rec = {"base": m0, "causal_dirmatch": m1,
                   "delta_n": m1["n"] - m0["n"],
                   "delta_net": round(m1["net"] - m0["net"], 1),
                   "delta_avgR": round(m1["avgR"] - m0["avgR"], 4)}
            payload["configs"].setdefault(era, {})[key] = rec
            print("  [%d/%d] %-34s base n=%3d %+7.1f R/t=%+.3f WR=%4.1f%%"
                  "  ->  causal n=%3d %+7.1f R/t=%+.3f WR=%4.1f%%"
                  "   dN=%+4d dR/t=%+.3f"
                  % (i, len(books), key, m0["n"], m0["net"], m0["avgR"],
                     m0["wr"], m1["n"], m1["net"], m1["avgR"], m1["wr"],
                     rec["delta_n"], rec["delta_avgR"]), flush=True)

    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())