"""What exactly does max_consecutive_losses=0 buy, and what does it cost?

THE OWNER'S CORRECTION
----------------------
The first answer gave the out-of-sample net. The owner asked the right follow-up
and it is the one that actually matters: a losing streak going 13 -> 14 and a
drawdown going 22.5 -> 24.4 are not automatically bad when the net rises by 52R
and the trade count rises by 49. Those two moves have to be weighed against each
other, and quoting one side of the ledger is how a +52R improvement gets
described as a risk regression.

It also asked for NEW metrics rather than a re-run of the old set. The one that
decides this:

    THE MARGINAL TRADES

Turning the halt off does not change the trades the book already had. It ADDS
trades - 753 -> 802 on 106 - trades that the three-loss cutoff had been
suppressing. Those 49 extra trades are the whole question. If they earn at the
same rate as the existing ones, the book genuinely got better and the extra
risk is being paid for with real profit. If they lose money and the net still
rose, then something else moved and the improvement is not attributable to the
change at all.

That is measurable directly, because the trade lists can be differenced by entry
timestamp. It is the metric the old set did not have and the one that settles
it.

ALSO REPORTED, because they are the denominators that matter:
  R per trade before and after        - did quality move, or only volume
  net % change vs drawdown % change   - were they paid for, and in what units
  the marginal trades' own stats      - n, net, win rate, payoff

Output: mcl_marginal.md
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
from exp_signal_metrics import load_era  # noqa: E402

MD = HERE / "mcl_marginal.md"

BOOKS = [
    ("fsent_champ_long_htffs", "106"),
    ("fsent_champ_long_htfesmcl4", "108"),
    ("fsent_champ_long_htf15_htffs", "109"),
    ("fsent_champ_long_htf15_tskip6", "110"),
]


def trades_of(sim, data, cfg, swing):
    p = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
          if t.get("outcome") != "open"]
    return {int(t["entry_ts"]): net_r([t]) for t in tr}


def stat(rs):
    if not rs:
        return None
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    gp, gl = sum(w), -sum(l)
    return {"n": len(rs), "net": round(sum(rs), 2),
            "rpt": round(sum(rs) / len(rs), 4),
            "wr": round(100.0 * len(w) / len(rs), 1),
            "pf": round(gp / gl, 2) if gl else 0.0}


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    L = ["# What max_consecutive_losses=0 buys, and what it costs", "",
         "Turning the halt off does not alter the trades the book already had.",
         " It adds trades the cutoff had been suppressing. Those extra trades are",
         " the whole question - do they earn like the rest, or does the net rise",
         " for some other reason while they do not?", ""]

    for name, code in BOOKS:
        base = EXPERIMENTS[name]
        swing = base.get("swing") or "sw10"
        alt = dict(base)
        alt["params"] = dict(base.get("params") or {})
        alt["params"]["max_consecutive_losses"] = 0

        L.append("## %s `%s`" % (code, name))
        L.append("")
        L.append("| era | trades | net | R/trade | net % | max DD | DD % | streak |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for era in ("is", "oos"):
            A = trades_of(sim, ERA[era], base, swing)
            B = trades_of(sim, ERA[era], alt, swing)
            extra = {k: v for k, v in B.items() if k not in A}
            dropped = {k: v for k, v in A.items() if k not in B}
            sa, sb = stat(list(A.values())), stat(list(B.values()))
            def dd(rs):
                cum = pk = d = 0.0
                for r in rs:
                    cum += r
                    pk = max(pk, cum)
                    d = max(d, pk - cum)
                return d
            dda, ddb = dd(list(A.values())), dd(list(B.values()))
            st = lambda rs: _streak(rs)
            L.append("| %s registered | %d | %+.1f | %+.4f | - | %.2f | - | %d |" % (
                era.upper(), sa["n"], sa["net"], sa["rpt"], dda, st(list(A.values()))))
            L.append("| %s at 0 | %d | %+.1f | %+.4f | %+.1f%% | %.2f | %+.1f%% | %d |" % (
                era.upper(), sb["n"], sb["net"], sb["rpt"],
                100.0 * (sb["net"] - sa["net"]) / abs(sa["net"]),
                ddb, 100.0 * (ddb - dda) / dda, st(list(B.values()))))
        L.append("")

        # the decisive part
        for era in ("is", "oos"):
            A = trades_of(sim, ERA[era], base, swing)
            B = trades_of(sim, ERA[era], alt, swing)
            extra = {k: v for k, v in B.items() if k not in A}
            dropped = {k: v for k, v in A.items() if k not in B}
            se, sd = stat(list(extra.values())), stat(list(dropped.values()))
            sa = stat(list(A.values()))
            L.append("### %s - the extra trades the cutoff had been suppressing" % era.upper())
            L.append("")
            L.append("| group | n | net | R/trade | win rate | PF |")
            L.append("|---|---:|---:|---:|---:|---:|")
            if sa:
                L.append("| all trades as registered | %d | %+.1f | %+.4f | %.1f%% | %.2f |"
                         % (sa["n"], sa["net"], sa["rpt"], sa["wr"], sa["pf"]))
            if se:
                L.append("| **NEW trades added by turning the halt off** | %d | %+.1f | %+.4f | %.1f%% | %.2f |"
                         % (se["n"], se["net"], se["rpt"], se["wr"], se["pf"]))
            if sd:
                L.append("| trades removed by turning the halt off | %d | %+.1f | %+.4f | %.1f%% | %.2f |"
                         % (sd["n"], sd["net"], sd["rpt"], sd["wr"], sd["pf"]))
            verdict = ""
            if se:
                if se["rpt"] >= (sa["rpt"] or 0) * 0.8:
                    verdict = ("The new trades earn at close to the book's own rate, so the "
                               "higher net is attributable to this change.")
                else:
                    verdict = ("The new trades earn materially worse than the book's own "
                               "rate, so the net improvement is NOT coming from them.")
            L.append("")
            if verdict:
                L.append(verdict)
                L.append("")
        print("%s done (%.0fs)" % (code, time.time() - t0), flush=True)

    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s  (%.0fs)" % (MD.name, time.time() - t0))
    return 0


def _streak(rs):
    s = b = 0
    for r in rs:
        s = s + 1 if r < 0 else 0
        b = max(b, s)
    return b


if __name__ == "__main__":
    raise SystemExit(main())