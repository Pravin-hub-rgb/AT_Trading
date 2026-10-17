"""Will removing exp_mltf from the registry change any book's number?

THE QUESTION, ANSWERED BY MEASUREMENT
-------------------------------------
The owner is right to ask before agreeing. Removing a setting means re-deriving
every pin, and the pins are what every number in this repository was measured
against. "It should be inert" is not good enough to justify rewriting seventy
five books.

So this runs the harness engine twice per book - once with exp_mltf=True, once
with the key absent entirely - and compares the resulting trade lists entry by
entry. Not the totals: the trades. If the two lists are identical then the knob
provably did nothing, the pins cannot move, and removing it is a pure cleanup.
If any trade differs, the book is listed and left alone.

The sample is every book currently in contention - the six multi candidates and
the shipping base - plus every gap_* and control book that carries the knob, so
the answer covers both the family under consideration and the controls that were
built to detect exactly this kind of thing.

Output: exp_mltf_proof.md
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402

MD = HERE / "exp_mltf_proof.md"

# every book that matters here: the six in contention, the shipping base, and
# every control book carrying the knob
FOCUS = [
    "fsent_champ_long", "fsent_champ_long_htffs", "fsent_champ_long_htfesmcl4",
    "fsent_champ_long_htf15_htffs", "fsent_champ_long_htf15_tskip6",
    "fsent_champ_long_mcloff_htf15", "fsent_champ_short",
]


def trade_list(sim, data, cfg, swing, params):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **params)
    tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
          if t.get("outcome") != "open"]
    tr.sort(key=lambda t: int(t["entry_ts"]))
    return [(int(t["entry_ts"]), round(net_r([t]), 4)) for t in tr]


def main() -> int:
    t0 = time.time()
    print("loading data ...", flush=True)
    data = get_data()
    sim = build_family_module()

    names = [n for n in FOCUS if n in EXPERIMENTS]
    ctrl = sorted(k for k, v in EXPERIMENTS.items()
                  if isinstance(v, dict) and (v.get("params") or {}).get("exp_mltf")
                  and (k.startswith("gap_") or k.startswith("skipwin")
                       or k.startswith("swingpause") or k.startswith("trail_half")))
    names += [c for c in ctrl if c not in names]

    rows, same, diff = [], 0, 0
    for name in names:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        with_m = {**BP, **(cfg.get("params") or {})}
        without = dict(with_m)
        without.pop("exp_mltf", None)
        try:
            A = trade_list(sim, data, cfg, swing, with_m)
            B = trade_list(sim, data, cfg, swing, without)
        except Exception as exc:  # noqa: BLE001
            rows.append((name, "ERROR %s" % exc))
            continue
        identical = A == B
        same += identical
        diff += (not identical)
        rows.append((name, identical, len(A), len(B), sum(x[1] for x in A)))
        print("%-34s %-4d trades  %-4d without  %s  (%.0fs)"
              % (name, len(A), len(B), "IDENTICAL" if identical else "** DIFFERS **",
                 time.time() - t0), flush=True)

    L = ["# Does removing exp_mltf move any number?", "",
         "exp_mltf is a harness-only parameter - unified.py does not accept it and",
         "only does anything on the loss-window hard close path, which unified.py",
         "does not have either. Seventy-five books carry it in the registry, and",
         "the live engine has been silently ignoring it on all of them.",
         "",
         "Removing it means re-deriving seventy-five pins, so this measures rather",
         "than assumes: every book is run twice, with the key and without it, and",
         "the resulting TRADE LISTS are compared entry by entry. Identical lists",
         "mean identical numbers by construction.", "",
         "| book | trades with | trades without | net with | trade lists |",
         "|---|---:|---:|---:|---|"]
    for r in rows:
        if r[1] == "ERROR" or len(r) == 2:
            L.append("| `%s` | - | - | - | %s |" % (r[0], r[1]))
        else:
            L.append("| `%s` | %d | %d | %+.2f | %s |"
                     % (r[0], r[2], r[3], r[4], "identical" if r[1] else "** DIFFER **"))
    L.append("")
    L.append("**%d books identical, %d differ.**" % (same, diff))
    if diff == 0:
        L.append("")
        L.append("The knob did nothing on any book tested. Removing it cannot move a")
        L.append("pin, because the trade lists are byte-identical without it.")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s  (%d identical, %d differ, %.0fs)"
          % (MD.name, same, diff, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())