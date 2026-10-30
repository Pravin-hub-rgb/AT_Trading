"""B2-ONLY LTF ENTRIES (owner question, 2026-10-21): no flip-mark entries.

VERDICT - GRAVEYARD. DO NOT REPEAT.
==================================
Owner rule tested on fsent_champ_long_mcloff_htf15, both eras, net lens,
control pins reproduced (526/+537.13 IS, 295/+273.52 OOS). Dropping
flip-mark entries LOSES badly:

    IS   526 -> 508 trades, net +537.13R -> +425.49R  (-111.6R after cascade)
    OOS  295 -> 275 trades, net +273.52R -> +203.36R  ( -70.2R after cascade)

    dropped: 62 IS / 53 OOS trades worth +112.21R / +110.75R
             (58xFLIP / 51xFLIP + 4-5 cascade-fringe B2/FS)
    added (cooldown-freed replacements): +0.57R IS / +40.59R OOS

Flip-terminal entries average +1.81R (IS) / +2.09R (OOS) per trade v book
average ~+1.0R - they are the book's BEST entries, not noise. Closed 2026-10-21.
Results: _flip_first_b2.json next to this file.

RULE UNDER TEST (original text, kept for the record). The owner asked: "we
enter short on B2; but if a flip comes first (B1 -> FLIP -> B2 on the
chart), do we still enter on that B2? What if we DON'T - only enter when
the B2 comes straight after the B1, no flip in between?"

MECHANICS (settled on the engine, not the chart):
- A flip MARK re-arms the leg, so inside one swing's break list a flip is
  always TERMINAL - nothing follows it in that list. The "B2 after a flip"
  seen on a chart is the re-armed leg's counter-break, which on an fs_long
  book belongs to an UP swing and never trades (up swings enter on FS only).
- So on book 107 the owner's rule reduces EXACTLY to: drop flip-mark entries
  from the LTF signal set. Short entries (B2 of down swings) are unchanged;
  the entries that disappear are the terminal-FLIP longs - a down leg that
  flipped before any B2 fired.
- Implemented as: the fs-branch fall-through tradeable set becomes ("B2",)
  only. HTF window plane, the long-side FS trigger and every risk knob are
  untouched (the patch replaces exactly one line of btc_engine._collect_signals).

LENS: the registry net lens (fees + slippage + funding per trade, closed
trades only), same as exp_repin_all.py, so the control must reproduce the
book's pinned numbers before the arm is read.

READ-ONLY. No engine edit, no registry write, no adoption.
"""
import io
import json
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (str(HERE), str(HERE.parent), str(ROOT / "backend"),
          str(ROOT / "backend" / "src")):
    sys.path.insert(0, p)

from experiment_registry import BP, EXPERIMENTS          # noqa: E402
from run_experiment import net_r, get_swings, get_data   # noqa: E402
from exp_signal_metrics import load_era                  # noqa: E402
from exp_tf_family import build_family_module            # noqa: E402

BOOK = "fsent_champ_long_mcloff_htf15"
ENGINE = ROOT / "backend" / "src" / "btc" / "btc_engine.py"
OUT = HERE / "_flip_first_b2.json"

ORIG_LINE = ('if _b.get("kind") in ("B2", "FLIP", "DECISIVE") '
             'and _b.get("time"):')
NEW_LINE = 'if _b.get("kind") in ("B2",) and _b.get("time"):'


def dd(rs):
    peak = cum = worst = 0.0
    for r in rs:
        cum += r
        if cum > peak:
            peak = cum
        if peak - cum > worst:
            worst = peak - cum
    return round(worst, 2)


def stats(tr):
    if not tr:
        return dict(n=0, net=0.0, dd=0.0, wr=None)
    net = [net_r([t]) for t in tr]
    wr = sum(1 for r in net if r > 0) / len(tr)
    return dict(n=len(tr), net=round(sum(net), 2), dd=dd(net),
                wr=round(wr, 3))


def run(sim, args, params, b2_only):
    import src.btc.btc_engine as be
    if not b2_only:
        o = sim(*args, **params)
    else:
        src = ENGINE.read_text(encoding="utf-8")
        n = src.count(ORIG_LINE)
        assert n == 1, "fs fall-through anchor not unique: %d" % n
        m = types.ModuleType("btc_engine_b2only")
        m.__file__ = str(ENGINE)
        exec(compile(src.replace(ORIG_LINE, NEW_LINE), str(ENGINE), "exec"),
             m.__dict__)
        orig = be._collect_signals
        be._collect_signals = m._collect_signals
        try:
            o = sim(*args, **params)
        finally:
            be._collect_signals = orig
    return sorted((t for t in o["ltf_trades"] if t.get("outcome") != "open"),
                  key=lambda t: int(t["entry_ts"]))


def main():
    t0 = time.time()
    print("loading eras (IS %s, OOS separate file) ..." % "2023-01..2026-08",
          flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    params = {**BP, **cfg["params"]}
    res = {}
    for era in ("is", "oos"):
        d = ERA[era]
        args = (d["c1h"], get_swings(d, "htf15"), d["c15"], d["sw15"])
        ctl = run(sim, args, params, False)
        arm = run(sim, args, params, True)
        pin = cfg["pins"]
        pin_n, pin_net = ((pin["n"], pin["net"]) if era == "is"
                          else (pin["oos_n"], pin["oos_net"]))
        s_ctl, s_arm = stats(ctl), stats(arm)
        ok = (abs(s_ctl["n"] - pin_n) <= 2
              and abs(s_ctl["net"] - pin_net) <= 1.5)
        ckey = {(int(t["entry_ts"]), t["dir"]) for t in ctl}
        akey = {(int(t["entry_ts"]), t["dir"]) for t in arm}
        dropped = [t for t in ctl if (int(t["entry_ts"]), t["dir"]) not in akey]
        added = [t for t in arm if (int(t["entry_ts"]), t["dir"]) not in ckey]
        kk = {}
        for t in dropped:
            k = str(t.get("break_kind", "?"))
            kk[k] = kk.get(k, 0) + 1
        ka = {}
        for t in added:
            k = str(t.get("break_kind", "?"))
            ka[k] = ka.get(k, 0) + 1
        res[era] = {"control": s_ctl, "b2_only": s_arm,
                    "pin": {"n": pin_n, "net": pin_net}, "pin_ok": ok,
                    "dropped_n": len(dropped),
                    "dropped_net": round(sum(net_r([t]) for t in dropped), 2),
                    "dropped_kinds": kk,
                    "added_n": len(added),
                    "added_net": round(sum(net_r([t]) for t in added), 2),
                    "added_kinds": ka}
        print()
        print("[%s] control  n=%d net=%+.2f dd=%.2f wr=%.3f   pin n=%d net=%+.2f  %s"
              % (era, s_ctl["n"], s_ctl["net"], s_ctl["dd"], s_ctl["wr"],
                 pin_n, pin_net, "PIN OK" if ok else "PIN MISMATCH"))
        print("      b2_only  n=%d net=%+.2f dd=%.2f wr=%.3f"
              % (s_arm["n"], s_arm["net"], s_arm["dd"], s_arm["wr"]))
        print("      dropped  n=%d net=%+.2f kinds=%s" % (len(dropped), res[era]["dropped_net"], kk))
        print("      added    n=%d net=%+.2f kinds=%s" % (len(added), res[era]["added_net"], ka))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))
    print()
    print("wrote %s (%.0fs)" % (OUT.name, time.time() - t0))


if __name__ == "__main__":
    main()
