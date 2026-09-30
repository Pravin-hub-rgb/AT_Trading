"""P75 - DECOMPOSE THE FS HYBRID. Survivors vs newcomers.

THE ONLY MEASUREMENT P73 NEVER MADE
    P73 reported 646 trades and +405.2R against a 500-trade +325.8R
    control, and the owner's reading - "+150 trades for +70R" - assumed the
    FS arm ADDS to the champion's book. Nothing established that, and the
    audit (P74) confirmed the routed `decisive` path no longer produces
    break entries at all, so the two books cannot simply be unioned.

    This measures it. Trades are matched on (entry_ts, direction), the same
    path-true key used in P59, so the split is a grouping of two live books
    and never a partition on r_multiple, outcome or pnl.

THE FOUR NUMBERS THAT MATTER
    SURVIVORS    champion trades still present in the hybrid book
    DROPPED      champion trades the hybrid lost
    NEW          hybrid trades the champion did not have
    and each group's net R, so "it added 146 trades worth +79.4R" either
    becomes a fact or dies.

    If DROPPED is large and positive, the hybrid is not adding, it is
    TRADING - swapping a chunk of the champion's book for a different chunk,
    and the net is a difference of two books rather than a gain.

THE PRIOR, STATED BEFORE RUNNING
    P74 withdrew P73's registration on three grounds and this addresses one
    of them. The expectation is that SURVIVORS is small - the `decisive`
    path stops emitting break entries entirely, so only coincidences from
    the untouched `flip` and `b2` paths should survive - and that most of
    the 646 is NEW. If instead SURVIVORS is large, the routed path was not
    the thing driving the change and the whole audit needs re-reading.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
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

    if entry_break == "fs_only":
        for si, s in enumerate(swings):
            if skip_first and int(s.get("swing_index", 0)) < 1:
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
            _seg = s.get("seg") or {}
            _sl = float(_seg.get("start_px") or 0.0)
            if not _sl > 0:
                continue
            out.append({"bar": fs_t,
                        "dir": 1 if s.get("dir") == "up" else -1,
                        "swing_start_px": _sl,
                        "swing_no": int(s.get("swing_index", si)),
                        "kind": "FS"})
        out.sort(key=lambda x: x["bar"])
        return out

    for si, s in enumerate(swings):'''
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def key_of(t):
    """Path-true match key: (entry instant, direction). Never a realised
    field - P59's rule."""
    return (int(t["entry_ts"]), 1 if t["dir"] == "long" else -1)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique")
    m = types.ModuleType("btc_engine_fs2")
    m.__file__ = str(ENGINE)
    exec(compile(src.replace(ANCHOR, FS_BRANCH), str(ENGINE), "exec"),
         m.__dict__)
    return m


def run(sim, use_fs, args, params, patched):
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
    print("  P75  DECOMPOSE THE FS HYBRID - SURVIVORS vs NEWCOMERS")
    print("=" * 100)
    print("  Matched on (entry_ts, direction) only - never a realised field.")
    print("  This is the number P73 never measured.\n")

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

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            A = run(sim, False, args, params, patched)
            B = run(sim, True, args, params, patched)
            if (abs(len(A) - pin[i][0]) > 2
                    or abs(net_r(A) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(A), net_r(A), *pin[i]))
                return
            ka = {key_of(t): t for t in A}
            kb = {key_of(t): t for t in B}
            both = sorted(set(ka) & set(kb))
            drop = sorted(set(ka) - set(kb))
            new = sorted(set(kb) - set(ka))
            print("  --- [%s]  champion %dt %+.1fR | FS hybrid %dt %+.1fR "
                  "(dNet %+.1fR)"
                  % (scope.upper(), len(A), net_r(A), len(B), net_r(B),
                     net_of(B) - net_r(A)))
            print("      %-14s %6s %10s %8s %7s"
                  % ("group", "n", "net", "R/t", "PF"))
            for lbl, keys, m_ in (("SURVIVORS", both, ka),
                                  ("DROPPED", drop, ka),
                                  ("NEW", new, kb)):
                tr = [m_[k] for k in keys]
                if not tr:
                    print("      %-14s %6d %10s" % (lbl, 0, "-"))
                    continue
                rs = [float(t["r_multiple"]) for t in tr]
                print("      %-14s %6d %+10.1fR %+8.3f %7.2f"
                      % (lbl, len(tr), net_of(tr), net_of(tr) / len(tr),
                         pf(rs)))
            print("      identity: %d common of %d champion and %d hybrid"
                  % (len(both), len(A), len(B)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()