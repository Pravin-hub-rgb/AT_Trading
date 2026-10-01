"""P72 - A TRUE FS-ONLY ENGINE. Enter when structure confirms, not when it breaks.

THE OPEN ITEM
    CLOSED_DO_NOT_REPEAT.md, still open:

        "True FS-only engine. 2900/1634 confirmed swings exist; only the
         314/179 that produced a B2/flip entry have been priced. An FS-only
         entry could be a larger book. Not simulated."

    Nemotron P3 said the same thing and rated it rank 3 of 10: "Never
    simulated; 2,900 swings vs 314 priced; different trigger set."

WHY THIS IS A REAL EXPERIMENT AND NOT JUST MORE TRADES
    Every entry the champion takes is a BREAK - a B2 or a FLIP, price
    crossing a structure extreme. The swing engine also stamps an FS
    moment on every swing: the bar at which the structure was FIRST
    declared, before any break. That is a strictly earlier, strictly
    different trigger, and it is available on all 2900/1634 confirmed
    swings rather than only the 314/179 that went on to break.

    So this is not "the same book with a looser filter". It is a different
    question: does the book have an edge at the moment structure is
    recognised, or only at the moment it is broken?

WHAT THE PATCH DOES, PRECISELY
    `_collect_signals` is given an early-return branch for
    entry_break == "fs_only" that emits ONE signal per swing, at that
    swing's `fs_at_time`, in the swing's own direction, with
    swing_start_px = the swing's start pivot (which is what the engine
    already uses as the stop for a same-direction mark). Swings with
    swing_index 0 are skipped, matching skip_first. Swings whose fs time is
    missing or trimmed from the window are skipped rather than guessed.

    Nothing else in _collect_signals changes, so the control path is
    byte-identical and the B2/FLIP book is still reproducible in the same
    run as a within-run control.

CAUSALITY
    fs_at_time is the bar the swing engine declared the structure on. That is
    information available at that bar and not before, which is what a live
    system would have. This is NOT the pivot's timestamp, so it carries no
    P52 lookahead.

PASS CRITERION - FIXED BEFORE RUNNING
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R. A
    much larger book that nets less is not a result - it is the trade this
    programme has now seen ten times, and this arm is the most likely
    instance of it yet because the trigger fires roughly nine times more
    often.

THE PRIOR, STATED HONESTLY
    Weak. Every break-triggered arm in this programme that added trades by
    relaxing the trigger lost money - B1 at P71 lost 36-164R for FEWER
    trades, and the relative-price filter at P69 lost on four of four
    cells. A relaxed trigger has been the losing move every time. This is
    worth running precisely because the item has been open for a long time
    unrun, not because the evidence is encouraging.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
ENGINE = ROOT / "backend" / "src" / "btc" / "btc_engine.py"
ANCHOR = ('    store = CandleStore(candles) if candles is not None else None\n'
          '\n'
          '    for si, s in enumerate(swings):')
FS_BRANCH = '''    store = CandleStore(candles) if candles is not None else None

    if entry_break == "fs_only":
        # P72: enter at the swing's FIRST SEAL rather than at a break.
        # One signal per swing, at fs_at_time, in the swing's own direction,
        # stopped at the swing's start pivot - the same level the engine
        # already uses for a same-direction mark. fs_at_time is the bar the
        # structure was declared on, so it is available live at that bar and
        # is NOT the pivot timestamp.
        for si, s in enumerate(swings):
            if skip_first and int(s.get("swing_index", 0)) < 1:
                continue
            # Resolve the bar by INDEX, not by fs_at_time. The first
            # attempt used s["fs_at_time"] directly and produced 1600+
            # signals whose `bar` was the string '00:30' - a time of day,
            # not a datetime - so store.pos() never matched and the engine
            # returned zero trades in every cell while the signal count
            # looked perfectly healthy. fs_at_idx indexes the candle list,
            # so it is exact and format-independent.
            _i = s.get("fs_at_idx")
            fs_t = None
            if store is not None and _i is not None:
                _i = int(_i)
                if 0 <= _i < len(store.candles):
                    fs_t = store.candles[_i]["date"]
            if not fs_t:
                _cand = s.get("fs_at_time") or s.get("confirmed_at_time") or ""
                if len(_cand) > 8:            # only a full datetime is usable
                    fs_t = _cand
            if not fs_t:
                continue
            if store is not None and not store.by_date(fs_t):
                continue
            _seg = s.get("seg") or {}
            _sl = float(_seg.get("start_px") or 0.0)
            if not (_sl > 0):
                continue
            out.append({
                "bar": fs_t,
                "dir": 1 if s.get("dir") == "up" else -1,
                "swing_start_px": _sl,
                "swing_no": int(s.get("swing_index", si)),
                "kind": "FS",
            })
        out.sort(key=lambda x: x["bar"])
        return out

    for si, s in enumerate(swings):'''
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique (%d)"
                         % src.count(ANCHOR))
    m = types.ModuleType("btc_engine_fs")
    m.__file__ = str(ENGINE)
    exec(compile(src.replace(ANCHOR, FS_BRANCH), str(ENGINE), "exec"),
         m.__dict__)
    return m


def run_arm(sim, use_fs, args, params, patched):
    import src.btc.btc_engine as be
    if not use_fs:
        return [t for t in sim(*args, **params)["ltf_trades"]
                if t.get("outcome") != "open"]
    orig = be._collect_signals

    def routed(swings, eb, **kw):
        return patched(swings, "fs_only" if eb == "decisive" else eb, **kw)

    be._collect_signals = routed
    try:
        res = sim(*args, **params)
    finally:
        be._collect_signals = orig
    return [t for t in res["ltf_trades"] if t.get("outcome") != "open"]


def main():
    print("=" * 100)
    print("  P72  A TRUE FS-ONLY ENGINE")
    print("=" * 100)
    print("  Enter at the swing's FIRST SEAL (fs_at_time) instead of at a")
    print("  B2/FLIP break. Available on all confirmed swings, not just the")
    print("  small share that went on to break. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    patched = patched_module()._collect_signals
    sim = tc.build_module()

    # Diagnose before running the book: an arm that yields no trades is
    # either a bug or a real zero, and the difference is one count.
    print("  SIGNAL DIAGNOSTIC")
    for scope in ("is", "oos"):
        args = src[scope]
        sig = patched(args[1], "fs_only")
        sig2 = patched(args[3], "fs_only")
        kinds = {}
        fsmiss = sum(1 for s_ in list(args[1]) + list(args[3])
                     if not (s_.get("fs_at_time")
                             or s_.get("confirmed_at_time")))
        slbad = sum(1 for s_ in list(args[1]) + list(args[3])
                    if not float((s_.get("seg") or {}).get("start_px") or 0) > 0)
        print("    [%s] fs_only signals: htf=%d ltf=%d | swings lacking "
              "fs/confirmed time=%d | swings with start_px<=0=%d"
              % (scope.upper(), len(sig), len(sig2), fsmiss, slbad))
        if sig:
            k = {}
            for x in sig[:2000]:
                k[x["kind"]] = k.get(x["kind"], 0) + 1
            print("    [%s] sample bar=%r dir=%r sl=%.2f kinds=%s"
                  % (scope.upper(), sig[0]["bar"], sig[0]["dir"],
                     sig[0]["swing_start_px"], k))
    print()

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            ctl = run_arm(sim, False, args, params, patched)
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            fs = run_arm(sim, True, args, params, patched)
            base = net_r(ctl)
            print("  --- [%s]  control (B2/FLIP) %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(ctl), base))
            print("      %-24s %6s %9s %7s %6s %6s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "dNet"))
            for lbl, tr in (("control (break entry)", ctl),
                            ("FS-only entry", fs)):
                rs = [float(t["r_multiple"]) for t in tr]
                if not rs:
                    print("      %-24s %6d   (no closed trades)"
                          % (lbl, len(tr)))
                    continue
                net = net_r(tr)
                dv = net - base
                print("      %-24s %6d %+9.1fR %+7.3f %6.2f %6.1f %+9.1fR%s"
                      % (lbl, len(rs), net, net / len(rs), pf(rs), dd(rs),
                         dv, "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()