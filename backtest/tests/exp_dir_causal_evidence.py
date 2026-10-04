"""DIRMATCH LOOKAHEAD - CONCRETE TRADES WITH DATES. Not theory, evidence.

THE CLAIM BEING PROVEN
    `exp_require_dir_match` decides whether to take a trade by reading the
    direction of the swing it thinks contains the entry bar. That selector picks
    any swing whose `seg.start_idx <= i`. But a swing that has STARTED is not a
    swing yet: its direction is only final when it CONFIRMS, at
    `confirmed_at_idx`. If `confirmed_at_idx > i`, the entry bar could not have
    known which way that swing would resolve.

    So for any taken trade where `confirmed_at_idx > i`, the filter that let it
    through had read a label from the future.

WHAT THIS FILE PRINTS, PER TRADE
    entry_ts / entry_px      - the bar the book entered on
    swing start_ts           - when the picked swing began
    swing confirmed_at_ts    - when that swing actually resolved
    LOOKAHEAD GAP            - hours between entry and confirmation
    dir_as_pinned            - the label the filter read
    dir_at_entry             - the label recomputed from candles up to the
                               entry bar only (what a live process would have)

    If LOOKAHEAD GAP > 0 and dir_as_pinned != dir_at_entry, the filter used
    information that did not exist at the entry bar.

READ-ONLY. Nothing is written except the JSON evidence file.
"""
import sys, json, pathlib, bisect
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _compute_swings
from src.walker import FlowCandle
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_dir_causal_evidence.json"
KEY = "dirmatch_multi_sw10"


def chain_at(c15, i):
    """Swings computed only on c15[:i+1] - what was knowable at bar i."""
    sub = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                      low=c["low"], close=c["close"]) for c in c15[:i + 1]]
    return _compute_swings(sub, "continuous", min_bars=50)


def iso(ts):
    import datetime as dt
    return dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")


_PROG=[0]


def main():
    cfg = reg.EXPERIMENTS[KEY]
    d = EQ.load_scope("is")
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    c15, sw15 = d["c15"], d["sw15"]
    tr = sim(d["c1h"], sw, c15, sw15, fine_ltf=d["fine"], **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)

    ts15 = [int(c["ts"]) for c in c15]
    full = sw15
    rows = []
    for t in tr:
        if t.get("outcome") == "open":
            continue
        ets = int(t["entry_ts"])
        i = bisect.bisect_right(ts15, ets) - 1
        if i < 0:
            continue
        picked = None
        for s in full:
            si = int((s.get("seg") or {}).get("start_idx", -1))
            if 0 <= si <= i:
                picked = s           # last match wins, same as the harness loop
        if picked is None:
            continue
        conf = int(picked.get("confirmed_at_idx", -1))
        if conf < 0:
            continue
        start_i = int(picked["seg"]["start_idx"])
        dir_pinned = 1 if picked.get("dir") == "up" else -1
        dir_known = 0
        if _PROG[0] % 25 == 0:
            print("    ...%d trades examined" % _PROG[0], flush=True)
        _PROG[0] += 1
        for s2 in chain_at(c15, i):
            ci = int(s2.get("confirmed_at_idx", -1))
            si2 = int((s2.get("seg") or {}).get("start_idx", -1))
            if ci >= 0 and ci <= i and 0 <= si2 <= i:
                dir_known = 1 if s2.get("dir") == "up" else -1
        rows.append({
            "entry_ts": ets, "entry_date": iso(ets),
            "entry_px": float(t["entry_price"]), "side": t.get("dir"),
            "swing_start_date": iso(ts15[start_i]),
            "swing_confirmed_date": iso(ts15[conf]) if conf < len(ts15) else "beyond",
            "lookahead_h": round((ts15[conf] - ets) / 3600.0, 2) if conf < len(ts15) else None,
            "dir_as_pinned": dir_pinned, "dir_at_entry": dir_known,
            "moved_wrong": bool(dir_known and dir_known != dir_pinned),
        })

    look = [r for r in rows if (r["lookahead_h"] or 0) > 0]
    moved = [r for r in rows if r["moved_wrong"]]
    print("=" * 98)
    print("DIRMATCH LOOKAHEAD - %s, in sample" % KEY)
    print("=" * 98)
    print("  trades examined                      : %d" % len(rows))
    print("  picks whose swing CONFIRMS after entry: %d  (%.1f%%)"
          % (len(look), 100.0 * len(look) / max(len(rows), 1)))
    print("  dir label DIFFERS from entry-bar truth: %d  (%.1f%%)"
          % (len(moved), 100.0 * len(moved) / max(len(rows), 1)))
    gaps = sorted(r["lookahead_h"] for r in look if r["lookahead_h"] is not None)
    if gaps:
        q = lambda p: gaps[int(p * (len(gaps) - 1))]
        print("  lookahead gap hours: p05 %+.0f  p50 %+.0f  p95 %+.0f"
              % (q(.05), q(.50), q(.95)))
    print()
    print("=" * 98)
    print("THE TWELVE WORST - largest confirmation delay")
    print("=" * 98)
    print("%-17s %-6s %-17s %-17s %7s %6s %6s"
          % ("entry", "side", "swing started", "swing confirmed", "gap h", "pin", "known"))
    for r in sorted(rows, key=lambda x: -(x["lookahead_h"] or 0))[:12]:
        print("%-17s %-6s %-17s %-17s %7.1f %6d %6d%s"
              % (r["entry_date"], r["side"], r["swing_start_date"],
                 r["swing_confirmed_date"], r["lookahead_h"] or 0,
                 r["dir_as_pinned"], r["dir_at_entry"],
                 "  <-- LABEL MOVED" if r["moved_wrong"] else ""))
    OUT.write_text(json.dumps({"key": KEY,
        "summary": {"examined": len(rows), "confirms_after_entry": len(look),
                    "dir_moved": len(moved)}, "all": rows}, indent=1),
        encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()


def chain_at(c15, i):
    """Swings computed only on c15[:i+1] - what was knowable at bar i."""
    sub = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                      low=c["low"], close=c["close"]) for c in c15[:i + 1]]
    return _compute_swings(sub, "continuous", min_bars=50)
