"""P80 - DIRECTIONAL FS. Take FS entries on one side only.

THE IDEA
    P78 found the mechanism and it was not the one hypothesised. The
    champion OOS long side is not weak, it is absent: 162 trades for +1.8R
    at PF 1.22. Its entire OOS result is its 117 short trades. The FS
    hybrid recovers exactly that side - 199 trades for +93.3R at PF 2.44 -
    while leaving the champion shorts intact.

        champion     long = break,  short = break
        FS hybrid    long = FS,     short = FS
        THIS         long = FS,     short = break   (and the mirror)

    P75 showed the two books are 99.8% disjoint, so this is not a blend of
    two views of the same trades - it is taking one trigger on one side and
    the other trigger on the other.

WHY THE PER-DIRECTION SPLITS MAY STILL BE A TRAP
    P75's lesson: an aggregate hides the distribution. P77's: a book can
    look good on OOS and lose six of eight IS half-years. "Hybrid long is
    better on aggregate in both eras" is exactly the shape of claim that has
    failed repeatedly. So the calendar half-year partition runs on every arm
    here, and it is the gate rather than the aggregate.

    It matters especially because the champion IS long side is strong
    (+272.6R PF 3.01). A filter that rescues OOS and damages IS is the
    trade this programme has seen ten times.

ARMS - PRE-REGISTERED, FOUR, NO SEARCH
    control    break long, break short  (= the pinned champion)
    FS_LONG    FS long, break short     <- the owner's idea
    FS_SHORT   break long, FS short     <- the mirror, so the result is
                                          not attributed to FS in general
    FS_BOTH    FS long, FS short        (= P73/P75's hybrid)

MECHANISM
    The router in _collect_signals decides per SWING: dir "up" goes to the
    break set or the FS set per the arm, "down" likewise. Entry direction
    is unchanged - an "up" swing still makes a long. Only the TRIGGER
    changes, so the two books' mechanics stay comparable.

PASS CRITERION - UNCHANGED, PLUS THE PERIOD SPLIT
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R, AND
    survive the half-year partition. The partition is what killed
    cand_4h1h and killed the FS hybrid; an arm that wins the aggregate and
    loses the split is not a result.
"""
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

ENGINE = ROOT / "backend" / "src" / "btc" / "btc_engine.py"
ANCHOR = ('    store = CandleStore(candles) if candles is not None else None\n'
          '\n'
          '    for si, s in enumerate(swings):')
FS_BRANCH = '''    store = CandleStore(candles) if candles is not None else None

    if str(entry_break).startswith("fs_"):
        _which = str(entry_break)[3:]
        for si, s in enumerate(swings):
            if skip_first and int(s.get("swing_index", 0)) < 1:
                continue
            _up = s.get("dir") == "up"
            _use_fs = (_which == "both" or (_which == "long" and _up)
                       or (_which == "short" and not _up))
            if not _use_fs:
                _seg0 = s.get("seg") or {}
                _got = False
                for _b in (s.get("breaks") or []):
                    if _b.get("kind") in ("B2", "FLIP") and _b.get("time"):
                        out.append({"bar": _b["time"],
                                    "dir": 1 if _b.get("dir") == "up" else -1,
                                    "swing_start_px": float(
                                        _seg0.get("start_px") or 0.0),
                                    "swing_no": int(s.get("swing_index", si)),
                                    "kind": _b.get("kind")})
                        _got = True
                        break
                continue
            _i = s.get("fs_at_idx")
            fs_t = None
            if store is not None and _i is not None:
                _i = int(_i)
                if 0 <= _i < len(store.candles):
                    fs_t = store.candles[_i]["date"]
            if not fs_t:
                _c = s.get("fs_at_time") or s.get("confirmed_at_time") or ""
                if len(_c) > 8:
                    fs_t = _c
            if not fs_t or (store is not None
                            and not store.by_date(fs_t)):
                continue
            _sg = s.get("seg") or {}
            _sl = float(_sg.get("start_px") or 0.0)
            if not _sl > 0:
                continue
            out.append({"bar": fs_t, "dir": 1 if _up else -1,
                        "swing_start_px": _sl,
                        "swing_no": int(s.get("swing_index", si)),
                        "kind": "FS"})
        out.sort(key=lambda x: x["bar"])
        return out

    for si, s in enumerate(swings):'''
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}
M_NULL = 193.4


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def half(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def agg_by(tr, keyfn):
    acc = {}
    for t in tr:
        acc.setdefault(keyfn(t), []).append(t)
    return acc


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique")
    m = types.ModuleType("btc_engine_dir")
    m.__file__ = str(ENGINE)
    exec(compile(src.replace(ANCHOR, FS_BRANCH), str(ENGINE), "exec"),
         m.__dict__)
    return m


def run(sim, arm, args, params, patched):
    import src.btc.btc_engine as be
    if arm == "control":
        return [t for t in sim(*args, **params)["ltf_trades"]
                if t.get("outcome") != "open"]
    orig = be._collect_signals

    def routed(swings, eb, **kw):
        return patched(swings, "fs_" + arm if eb == "decisive" else eb, **kw)

    be._collect_signals = routed
    try:
        res = sim(*args, **params)
    finally:
        be._collect_signals = orig
    return [t for t in res["ltf_trades"] if t.get("outcome") != "open"]


ARMS = ("control", "long", "short", "both")
LBL = {"control": "break long, break short",
       "long": "FS LONG, break short  <-- OWNER'S IDEA",
       "short": "break long, FS SHORT",
       "both": "FS long, FS short"}


def main():
    print("=" * 100)
    print("  P80  DIRECTIONAL FS - take FS entries on ONE SIDE only")
    print("=" * 100)
    print("  champion IS long +272.6R PF 3.01 but OOS long +1.8R PF 1.22.")
    print("  The FS hybrid recovers that side. Arms, pre-registered:")
    for a in ARMS:
        print("    %-8s %s" % (a, LBL[a]))
    print("  Gate: both eras, both lanes, clear M = 193.4R, AND survive the")
    print("  calendar half-year partition.\n")

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
    books = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            ctl = run(sim, "control", src[scope], params, patched)
            if (abs(len(ctl) - PIN[name][i][0]) > 2
                    or abs(net_r(ctl) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = {a: run(sim, a, src[scope], params,
                                           patched) for a in ARMS}
    print("  controls pinned in all four cells\n")

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            bk = books[(name, scope)]
            base = net_of(bk["control"])
            print("  --- [%s]" % scope.upper())
            print("      %-40s %5s %10s %8s %7s %7s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "WR", "dNet"))
            for a in ARMS:
                tr = bk[a]
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_of(tr)
                dv = net - base
                print("      %-40s %5d %+10.1fR %+8.3f %7.2f %6.1f%% %+9.1fR%s"
                      % (LBL[a], len(rs), net, net / len(rs), pf(rs),
                         100.0 * sum(1 for x in rs if x > 0) / len(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print("      --- period partition, R/trade vs control ---")
            pc = agg_by(bk["control"], lambda t: half(t["entry_ts"]))
            for a in ARMS[1:]:
                pa = agg_by(bk[a], lambda t: half(t["entry_ts"]))
                w = l = t_ = 0
                for k in sorted(set(pc) | set(pa)):
                    ra = [float(x["r_multiple"]) for x in pc.get(k, [])]
                    rb = [float(x["r_multiple"]) for x in pa.get(k, [])]
                    if not (ra and rb):
                        continue
                    if sum(rb) / len(rb) > sum(ra) / len(ra):
                        w += 1
                    elif sum(rb) / len(rb) < sum(ra) / len(ra):
                        l += 1
                    else:
                        t_ += 1
                print("      %-40s wins %2d loses %2d ties %2d of %2d"
                      % (LBL[a], w, l, t_, w + l + t_))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()