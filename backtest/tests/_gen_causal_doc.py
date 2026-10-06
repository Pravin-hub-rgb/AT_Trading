"""Write SIGNAL_CAUSAL_DIRMATCH.md from _signal_causal_dirmatch.json.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u _gen_causal_doc.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backtest/tests/_signal_causal_dirmatch.json"
DST = ROOT / "backtest/docs/signal/SIGNAL_CAUSAL_DIRMATCH.md"


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    IS, OOS = d["configs"].get("is", {}), d["configs"].get("oos", {})

    both = []
    for b in IS:
        if b in OOS and IS[b]["base"].get("n"):
            both.append(b)

    def delta(era, b, k):
        return IS[b][k] if era == "is" else OOS[b][k]

    L = []
    A = L.append
    A("# SIGNAL PLANE — causal direction match")
    A("")
    A("Generated from `backtest/tests/_signal_causal_dirmatch.json` by")
    A("`backtest/tests/_gen_causal_doc.py`, computed by")
    A("`backtest/tests/exp_signal_causal_dirmatch.py`.")
    A("")
    A("## The question")
    A("")
    A("`exp_require_dir_match=1` takes a 15m signal only if the 15m swing")
    A("containing it points the same way. Read raw, that swing's direction is")
    A("only final at `confirmed_at_idx` — a median of 8 hours **after** the")
    A("entry — and it is the trade's own outcome. That is the look-ahead")
    A("already caught and quarantined.")
    A("")
    A("`exp_dir_causal=1` is the one line that makes it legal: ignore any swing")
    A("not yet confirmed at the entry bar.")
    A("")
    A("Everything here ran **with** the guard. The quarantined numbers were not")
    A("rerun and must not be quoted.")
    A("")
    A("This is the first time the causal filter has been measured on a")
    A("`max_positions == 1` book. Previously it was only ever run on multi books,")
    A("so the signal-plane answer did not exist.")
    A("")
    A("## The test")
    A("")
    A("Every clean signal book, run twice: once as-is, once with")
    A("`exp_require_dir_match=1, exp_dir_causal=1`. A filter that merely removes")
    A("trades leaves R per trade flat; one that finds something raises it. Both")
    A("are reported, and \"no\" is a permitted answer.")
    A("")

    A("| | books tested |")
    A("|---|---:|")
    A("| in both eras | %d |" % len(both))
    A("")

    for era, label in (("is", "In-sample"), ("oos", "Out-of-sample")):
        rows = [b for b in both if delta(era, b, "causal_dirmatch").get("n")]
        rows.sort(key=lambda b: -(IS[b]["delta_avgR"] if era == "is"
                                  else OOS[b]["delta_avgR"]))
        A("## %s — by change in R per trade" % label)
        A("")
        A("`base` is the book as pinned. `causal` adds the legal direction-match.")
        A("Positive `dR/t` means the filter made each surviving trade better.")
        A("")
        A("| book | base n | base net | base R/t | base wr% | causal n | causal "
          "net | causal R/t | causal wr% | dN | dNet | **dR/t** |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for b in rows:
            if era == "is":
                m0, m1, rec = IS[b]["base"], IS[b]["causal_dirmatch"], IS[b]
            else:
                m0, m1, rec = OOS[b]["base"], OOS[b]["causal_dirmatch"], OOS[b]
            A("| `%s` | %d | %+.1f | %+.3f | %.1f%% | %d | %+.1f | %+.3f | "
              "%.1f%% | %+d | %+.1f | **%+.3f** |"
              % (b, m0["n"], m0["net"], m0["avgR"], m0["wr"], m1["n"],
                 m1["net"], m1["avgR"], m1["wr"], rec["delta_n"],
                 rec["delta_net"], rec["delta_avgR"]))
        A("")

    # summary
    imp_is = sorted(both, key=lambda b: -IS[b]["delta_avgR"])
    both_pos = [b for b in both
                if IS[b]["delta_avgR"] > 0 and OOS[b]["delta_avgR"] > 0]
    both_neg = [b for b in both
                if IS[b]["delta_avgR"] < 0 and OOS[b]["delta_avgR"] < 0]
    flipped = [b for b in both
               if (IS[b]["delta_avgR"] > 0) != (OOS[b]["delta_avgR"] > 0)]

    A("## What it does across the plane")
    A("")
    A("| | count |")
    A("|---|---:|")
    A("| R/trade up in **both** eras | %d |" % len(both_pos))
    A("| R/trade down in **both** eras | %d |" % len(both_neg))
    A("| eras disagree on the sign | %d |" % len(flipped))
    A("| books tested | %d |" % len(both))
    A("")
    A("A book counts as improved only if the sign holds in both eras. The ones")
    A("where it does not are the ones that would have looked good on whichever")
    A("era was checked first.")
    A("")
    if both_pos:
        A("Improved in both eras:")
        A("")
        for b in sorted(both_pos, key=lambda x: -(IS[x]["delta_avgR"]
                                                  + OOS[x]["delta_avgR"])):
            A("- `%s` — IS %+.3f, OOS %+.3f R/t"
              % (b, IS[b]["delta_avgR"], OOS[b]["delta_avgR"]))
        A("")
    if both_neg:
        A("Worse in both eras:")
        A("")
        for b in sorted(both_neg, key=lambda x: (IS[x]["delta_avgR"]
                                                 + OOS[x]["delta_avgR"])):
            A("- `%s` — IS %+.3f, OOS %+.3f R/t"
              % (b, IS[b]["delta_avgR"], OOS[b]["delta_avgR"]))
        A("")

    DST.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s (%d lines)" % (DST, len(L)))
    print("tested=%d  up-both=%d  down-both=%d  sign-flips=%d"
          % (len(both), len(both_pos), len(both_neg), len(flipped)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())