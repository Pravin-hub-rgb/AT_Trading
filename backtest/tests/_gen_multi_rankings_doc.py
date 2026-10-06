"""Two rankings of the MULTI plane: by total net R, and by R per trade.

Mirror of _gen_rankings_doc.py, on the other plane. They answer different
questions and they disagree:

  by net    - how much R the book made. Favours books that run many slots and
              trade often. On this plane that is a real advantage and also a
              real trap: more concurrent positions is more R without being more
              edge.
  by R/trd  - how much each trade was worth. Favours books that trade little
              but well, which a total hides completely.

The two lists are kept apart from the signal plane on purpose. A multi book at
500 trades and a signal book at 150 are not comparable by total R, so this file
ranks only multi books and SIGNAL_RANKINGS.md ranks only signal books.

Both lists carry n, DD, win rate and top5% because R per trade without the
trade count is its own trap: a book trading 30 times at 3R each beats one
trading 300 times at 0.5R each, and neither is right without the drawdown.

Writes backtest/docs/multi/MULTI_RANKINGS.md.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u _gen_multi_rankings_doc.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backtest/tests/_multi_metrics.json"
DST = ROOT / "backtest/docs/multi/MULTI_RANKINGS.md"

MIN_N = 30


def main() -> int:
    if not SRC.exists():
        print("missing %s - run exp_multi_metrics.py first" % SRC)
        return 1
    d = json.loads(SRC.read_text(encoding="utf-8"))
    IS, OOS = d["configs"]["is"], d["configs"]["oos"]

    both = []
    for b in IS:
        i, o = IS[b], OOS.get(b, {})
        if i.get("n") and o.get("n") and i["n"] >= MIN_N and o["n"] >= MIN_N:
            both.append((b, i, o))
    if not both:
        print("no book has %d+ trades in both eras - lower MIN_N" % MIN_N)
        return 1

    by_net = sorted(both, key=lambda r: -(r[2].get("net") or -1e9))
    by_r = sorted(both, key=lambda r: -(r[2].get("avgR") or -1e9))
    pos = [r for r in both if (r[1]["net"] or 0) > 0 and (r[2]["net"] or 0) > 0]
    drifted = [r for r in both
               if abs(r[2].get("vs_pin") or 0) >= 0.5
               or abs(r[1].get("vs_pin") or 0) >= 0.5]

    L = []
    A = L.append
    A("# MULTI PLANE - two rankings")
    A("")
    A("Generated from `backtest/tests/_multi_metrics.json` by")
    A("`backtest/tests/_gen_multi_rankings_doc.py`. Multi plane only")
    A("(`max_positions != 1`), both eras, quarantined look-ahead books excluded,")
    A("books under %d trades in either era excluded." % MIN_N)
    A("")
    A("`n` counts CLOSED trades. The registry's net pins exclude positions still")
    A("open at the era boundary (their r is mark-to-market, not realized), so a")
    A("book's `n` here can sit under the board's n while `net` matches its pin -")
    A("`n_open` in the source JSON holds that difference.")
    A("")
    A("## Why two lists")
    A("")
    A("| ranking | favours | hides |")
    A("|---|---|---|")
    A("| **by total net R** | books that run many slots and trade often | how "
      "good each trade was |")
    A("| **by R per trade** | books whose trades are worth more | how many "
      "there were |")
    A("")
    A("Both are correct and they disagree, which is the point. On this plane the")
    A("total is partly bought with concurrency: `max_positions` is not 1, so a")
    A("book can raise total R by overlapping trades without any trade being")
    A("better. R per trade is the only one of the two that cannot be raised")
    A("that way.")
    A("")
    A("| | count |")
    A("|---|---|")
    A("| books in both eras, n >= %d | %d |" % (MIN_N, len(both)))
    A("| positive in both eras | %d |" % len(pos))
    A("| past the registry pin by >= 0.5R | %d |" % len(drifted))
    A("")

    A("## 1. Ranked by out-of-sample total net R")
    A("")
    A("`t5%` share of net from the best 5% of trades. `med` median R. ")
    A("`strk` longest losing run.")
    A("")
    A("| # | book | OOSn | **OOS net** | R/trd | wr% | PF | DD | t5% | med | ")
    A("strk | ISn | IS net | IS R/trd |")
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
    A("than the book above it and still be worth more - it just needs fewer")
    A("trades to earn it.")
    A("")
    A("| # | book | OOSn | **OOS R/trd** | OOS net | wr% | PF | DD | t5% | ")
    A("med | strk | ISn | IS R/trd |")
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

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s (%d lines, %d books)" % (DST, len(L), len(both)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
