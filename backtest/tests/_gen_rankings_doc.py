"""Two rankings of the signal plane: by total R, and by R per trade.

They answer different questions and they disagree.

  by net    - how much R did the book make. Favours books that trade a lot.
  by R/trd  - how much each trade was worth. Favours books that trade little
              but well, which a total hides completely.

A book can top one list and sink the other. wage10_swingpause_wskip_sig_sw10
makes +270.8R in sample on 262 trades and +35.6R out of sample on 158; a book
with half the trades and half the net but twice the R per trade is a different
bet, and only the per-trade ranking shows it.

Both lists carry n, DD, win rate and top5% because R per trade without the
trade count is its own trap: a book trading 30 times at 3R each beats one
trading 300 times at 0.5R each, and neither is right without the drawdown.

Writes backtest/docs/signal/SIGNAL_RANKINGS.md.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u _gen_rankings_doc.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backtest/tests/_signal_metrics.json"
DST = ROOT / "backtest/docs/signal/SIGNAL_RANKINGS.md"

MIN_N = 30


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    IS, OOS = d["configs"]["is"], d["configs"]["oos"]

    both = []
    for b in IS:
        i, o = IS[b], OOS.get(b, {})
        if i.get("n") and o.get("n") and i["n"] >= MIN_N and o["n"] >= MIN_N:
            both.append((b, i, o))

    by_net = sorted(both, key=lambda r: -(r[2].get("net") or -1e9))
    by_r = sorted(both, key=lambda r: -(r[2].get("avgR") or -1e9))
    pos = [r for r in both if (r[1]["net"] or 0) > 0 and (r[2]["net"] or 0) > 0]

    L = []
    A = L.append
    A("# SIGNAL PLANE — two rankings")
    A("")
    A("Generated from `backtest/tests/_signal_metrics.json` by")
    A("`backtest/tests/_gen_rankings_doc.py`. Signal plane only")
    A("(`max_positions == 1`), both eras, quarantined look-ahead books excluded,")
    A("books under %d trades in either era excluded." % MIN_N)
    A("")
    A("`n` counts CLOSED trades: the registry's net pins exclude positions still")
    A("open at the era boundary (mark-to-market r), so `n` here can sit under the")
    A("board's n while `net` matches its pin. `n_open` in the source JSON holds")
    A("the difference.")
    A("")
    A("## Why two lists")
    A("")
    A("| ranking | favours | hides |")
    A("|---|---|---|")
    A("| **by total net R** | books that trade often | how good each trade was |")
    A("| **by R per trade** | books whose trades are worth more | how many there "
      "were |")
    A("")
    A("Both are correct and they disagree, which is the point. Total R rewards")
    A("frequency; R per trade rewards quality.")
    A("")
    A("| | count |")
    A("|---|---|")
    A("| books in both eras, n >= %d | %d |" % (MIN_N, len(both)))
    A("| positive in both eras | %d |" % len(pos))
    A("")

    A("## 1. Ranked by out-of-sample total net R")
    A("")
    A("`t5%` share of net from the best 5% of trades. `med` median R. "
      "`strk` longest losing run.")
    A("")
    A("| # | book | OOSn | **OOS net** | R/trd | wr% | PF | DD | t5% | med | "
      "strk | ISn | IS net | IS R/trd |")
    A("|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n, (b, i, o) in enumerate(by_net, 1):
        A("| %d | `%s` | %d | **%+.1f** | %+.3f | %.1f%% | %.2f | %.1f | %.0f | "
          "%+.2f | %d | %d | %+.1f | %+.3f |"
          % (n, b, o["n"], o["net"], o["avgR"], o["wr"], o["pf"] or 0,
             o["max_dd"], o["top5_share_pct"] or 0, o["median"],
             o["max_streak"], i["n"], i["net"], i["avgR"]))
    A("")

    A("## 2. Ranked by out-of-sample R per trade")
    A("")
    A("Same books, same eras, re-sorted. A book here may have far less total R")
    A("than the book above it and still be worth more — it just needs fewer")
    A("trades to earn it.")
    A("")
    A("| # | book | OOSn | **OOS R/trd** | OOS net | wr% | PF | DD | t5% | "
      "med | strk | ISn | IS R/trd |")
    A("|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n, (b, i, o) in enumerate(by_r, 1):
        A("| %d | `%s` | %d | **%+.3f** | %+.1f | %.1f%% | %.2f | %.1f | %.0f "
          "| %+.2f | %d | %d | %+.3f |"
          % (n, b, o["n"], o["avgR"], o["net"], o["wr"], o["pf"] or 0,
             o["max_dd"], o["top5_share_pct"] or 0, o["median"],
             o["max_streak"], i["n"], i["avgR"]))
    A("")
    # ---- where the two disagree
    top_net = [b for b, _, _ in by_net[:10]]
    top_r = [b for b, _, _ in by_r[:10]]
    only_r = [b for b in top_r if b not in top_net]
    only_net = [b for b in top_net if b not in top_r]
    A("## Where the two rankings disagree")
    A("")
    A("| | books |")
    A("|---|---|")
    A("| top 10 by net only | %s |"
      % (", ".join("`%s`" % b for b in only_net) or "-"))
    A("| top 10 by R/trade only | %s |"
      % (", ".join("`%s`" % b for b in only_r) or "-"))
    A("| in both | %s |"
      % (", ".join("`%s`" % b for b in top_net if b in top_r) or "-"))
    A("")
    A("Anything in the second row earns its R with far less trading. Anything in")
    A("the first earns its R by trading more, at a lower rate per trade.")
    A("")

    rn = {b: k for k, (b, _, _) in enumerate(by_net, 1)}
    rr = {b: k for k, (b, _, _) in enumerate(by_r, 1)}
    moved = sorted(both, key=lambda r: -(rn[r[0]] - rr[r[0]]))
    A("## Rank movement, total net to R per trade")
    A("")
    A("| book | rank by net | rank by R/trd | move |")
    A("|---|--:|--:|--:|")
    for b, i, o in moved[:12]:
        A("| `%s` | %d | %d | %s%d |"
          % (b, rn[b], rr[b], "+" if rr[b] < rn[b] else "", rn[b] - rr[b]))
    A("")
    A("A positive move means the book looks better when you ask what each trade")
    A("is worth than when you ask what the book made in total.")
    A("")

    DST.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s (%d lines)" % (DST, len(L)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())