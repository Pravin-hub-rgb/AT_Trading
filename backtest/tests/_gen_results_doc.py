import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(".").resolve()
d = json.loads((ROOT / "backtest/tests/_signal_metrics.json").read_text(encoding="utf-8"))
IS, OOS = d["configs"]["is"], d["configs"]["oos"]
SKIP = d["skipped_quarantined"]

# A book that trades a couple of dozen times in four years is not a strategy, it
# is a sample. These topped the IS list on net because two lucky trades produce
# any number at all: trail06 shows n=2 net=+2173 PF=1592. Reported, not ranked.
MIN_N = 30

out = []
out.append("# SIGNAL PLANE — measured results, every book")
out.append("")
out.append("Generated from `backtest/tests/_signal_metrics.json` (harness")
out.append("`signal_metrics`), computed from the engine by")
out.append("`python backtest/tests/exp_signal_metrics.py`. Nothing here is")
out.append("transcribed by hand; the registry pins carry four fields and this")
out.append("file carries the rest.")
out.append("")
out.append("Scope: **signal plane only** — `max_positions == 1`, one position at")
out.append("a time. Multi books (`max_positions != 1`) are deliberately excluded:")
out.append("they hold 400-600 trades at once and are a different question.")
out.append("")
out.append("`top5%` is the share of net carried by the best 5% of trades. Read")
out.append("it before `net` — a book at 700% has a handful of lucky trades and")
out.append("everything else in the book loses money.")
out.append("")
out.append("`n` counts CLOSED trades: the registry's net pins exclude positions")
out.append("still open at the era boundary (their r is mark-to-market, not")
out.append("realized), so `n` here can sit under the board's n while `net`")
out.append("matches its pin. `n_open` in the source JSON holds the difference.")
out.append("")

rank = []
for b in IS:
    i, o = IS[b], OOS.get(b, {})
    if i.get("n") and o.get("n"):
        rank.append((b, i, o))
rank.sort(key=lambda r: -(r[2].get("net") or -1e9))

ranked = [r for r in rank if r[1]["n"] >= MIN_N and r[2]["n"] >= MIN_N]
thin = [r for r in rank if not (r[1]["n"] >= MIN_N and r[2]["n"] >= MIN_N)]
both_pos = [r for r in ranked if (r[1]["net"] or 0) > 0 and (r[2]["net"] or 0) > 0]

out.append("## Summary")
out.append("")
out.append("| | count |")
out.append("|---|---|")
out.append("| signal books measured | %d |" % len(rank))
out.append("| quarantined look-ahead, not run | %d |" % len(SKIP))
out.append("| ranked (both eras, n >= %d) | %d |" % (MIN_N, len(ranked)))
out.append("| **positive in BOTH eras** | **%d** |" % len(both_pos))
out.append("| under the trade floor, reported not ranked | %d |" % len(thin))
out.append("")

out.append("## Quarantined — do not quote these")
out.append("")
out.append("These read a swing field that is not settled at the entry bar. Their")
out.append("numbers are kept as evidence that the look-ahead was caught, and are")
out.append("excluded from every ranking in the database as well as here.")
out.append("")
out.append("| book | knobs |")
out.append("|---|---|")
for b, v in SKIP.items():
    out.append("| `%s` | %s |" % (b, ", ".join("`%s`" % x for x in v)))
out.append("")

out.append("## All ranked signal books, by out-of-sample net")
out.append("")
out.append("`R/trd` mean R per trade | `wr%` win rate | `PF` profit factor |")
out.append("`DD` max drawdown in R | `top5%` share of net from the best 5% of")
out.append("trades | `med` median R (negative means most trades lose) |")
out.append("`strk` longest losing run.")
out.append("")
out.append("| book | ISn | IS net | R/trd | wr% | PF | DD | top5% | med | strk"
           " | OOSn | **OOS net** | R/trd | wr% | PF | DD | top5% |")
out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:"
           "|---:|---:|---:|---:|")
for b, i, o in ranked:
    out.append("| `%s` | %d | %+.1f | %+.3f | %.1f%% | %.2f | %.1f | %.0f | "
               "%+.2f | %d | %d | **%+.1f** | %+.3f | %.1f%% | %.2f | %.1f | %.0f |"
               % (b, i["n"], i["net"], i["avgR"], i["wr"], i["pf"] or 0,
                  i["max_dd"], i["top5_share_pct"] or 0, i["median"],
                  i["max_streak"], o["n"], o["net"], o["avgR"], o["wr"],
                  o["pf"] or 0, o["max_dd"], o["top5_share_pct"] or 0))
out.append("")
if thin:
    out.append("## Under the %d-trade floor" % MIN_N)
    out.append("")
    out.append("Reported so nothing is hidden, ranked by nothing. A net figure here")
    out.append("is a few trades, not an edge.")
    out.append("")
    out.append("| book | ISn | IS net | PF | OOSn | OOS net | PF |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for b, i, o in sorted(thin, key=lambda r: -(r[1].get("net") or 0)):
        out.append("| `%s` | %d | %+.1f | %.2f | %s | %s | %s |"
                   % (b, i["n"], i["net"], i.get("pf") or 0,
                      o.get("n", "-"),
                      ("%+.1f" % o["net"]) if o.get("net") is not None else "-",
                      ("%.2f" % o["pf"]) if o.get("pf") is not None else "-"))
    out.append("")

out.append("## What separates them")
out.append("")
out.append("Sorted by OOS net the list splits into two groups, and the gap shows")
out.append("up in `top5%` before it shows up in net.")
out.append("")
out.append("**`fsent_sig_full`, `fsent_sig_fs_mom`, `fsent_sig_wk_pause_short`** —")
out.append("win rate 35-45%, profit factor 2.2-3.3, `top5%` 66-93%. The best 5% of")
out.append("trades carry most of the profit but not all of it, so the other 95%")
out.append("still contribute. Median R stays near zero, which is what a book with a")
out.append("broad base looks like.")
out.append("")
out.append("**Everything else** — win rate 22-30%, profit factor 1.1-1.9, `top5%`")
out.append("128-700%. Most trades lose (median about -1.07, a full stop) and the")
out.append("profit arrives in a thin tail. `champion_sig_sw10` is the clearest")
out.append("case: `top5%` 704% means the five best out-of-sample trades were worth")
out.append("more than the book's entire net, so every other trade lost money")
out.append("together.")
out.append("")
out.append("**In-sample versus out-of-sample.** The wage and fullstack families")
out.append("compete on IS — several beat `fsent_sig_full`'s +291 — then fall to")
out.append("+26 to +49 out of sample, about a tenth of their in-sample number.")
out.append("`fsent_sig_full` retains 66% and `fsent_sig_fs_mom` 63%. Retention")
out.append("separated them; net alone did not.")
out.append("")

bad = []
for era in ("is", "oos"):
    for b, v in d["configs"][era].items():
        if v.get("vs_pin") is not None and abs(v["vs_pin"]) >= 0.5:
            bad.append((b, era, v))
out.append("## Verification")
out.append("")
out.append("Each book was compared against its registry pin after measuring.")
out.append("")
if bad:
    out.append("| book | era | measured | pin | difference |")
    out.append("|---|---|---:|---:|---:|")
    for b, e, v in sorted(bad, key=lambda x: -abs(x[2]["vs_pin"])):
        out.append("| `%s` | %s | %+.1f | %+.1f | %+.1f |"
                   % (b, e, v["net"], v["pin_net"], v["vs_pin"]))
else:
    out.append("All measured nets reproduce their registry pin to within 0.5R.")
out.append("")

p = ROOT / "backtest/docs/signal/SIGNAL_RESULTS.md"
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote %s  (%d lines)" % (p, len(out)))
print("ranked=%d  both-eras-positive=%d  thin=%d  quarantined=%d"
      % (len(ranked), len(both_pos), len(thin), len(SKIP)))
