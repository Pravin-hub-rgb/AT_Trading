"""P76 - PERIOD PARTITION AND PER-YEAR BREAKDOWN OF THE FS HYBRID.

WHY THIS RUN
    P75 showed the FS hybrid is a 99.8% different book that beats the
    champion on OOS R/trade by ~2.5x and ties it in champion IS. The one
    test that killed cand_4h1h has never been applied to it: a calendar
    half-year partition. A claim resting entirely on OOS R/trade is exactly
    what a half-year split can kill.

    The owner also observed something specific: the hybrid's advantage
    looks like it lives in 2021-22, and nothing else in this programme has
    matched it there. PART B breaks the books out by calendar YEAR so that
    claim is measured rather than asserted.

PART A - THE P61 TEST, APPLIED FOR THE FIRST TIME TO THIS ARM
    Calendar half-years, fixed before looking, never grouped by
    r_multiple / outcome / pnl. Counts how often the hybrid's mean R/trade
    beats the champion's. cand_4h1h was 4-4 in IS. Stage 64's win-streak
    block was 14-3 over 24 cells.

PART B - PER YEAR
    Same books, grouped by calendar year of entry_ts. Reports net, R/trade,
    PF and trade count for BOTH books per year, so the years can be read
    side by side rather than as era aggregates.

    This is diagnostic, not a selection criterion. Nothing is adopted on
    the strength of a year table, and no year is chosen.

PASS CRITERION - UNCHANGED
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R.
    The period split is an additional gate, not a substitute: an arm that
    passes the split but fails M still fails.
"""
import sys
import types
from datetime import datetime, timezone
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

M_NULL = 193.4
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
            _sg = s.get("seg") or {}
            _sl = float(_sg.get("start_px") or 0.0)
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


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def half(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def year(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).year


def agg_by(tr, keyfn):
    acc = {}
    for t in tr:
        acc.setdefault(keyfn(t["entry_ts"]), []).append(t)
    return acc


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique")
    m = types.ModuleType("btc_engine_fsp")
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
    print("  P76  PERIOD PARTITION AND PER-YEAR, FS HYBRID vs CHAMPION")
    print("=" * 100)
    print("  PART A is the P61 test, applied to this arm for the first")
    print("  time. PART B breaks both books out by calendar YEAR.")
    print("  M = %.1fR. Nothing selected on the year table.\n" % M_NULL)

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
            args = src[scope]
            A = run(sim, False, args, params, patched)
            if (abs(len(A) - PIN[name][i][0]) > 2
                    or abs(net_r(A) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = (A, run(sim, True, args, params,
                                           patched))
        print("  controls pinned for %s" % name)

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            A, B = books[(name, scope)]
            pa, pb = agg_by(A, half), agg_by(B, half)
            keys = sorted(set(pa) | set(pb))
            w = l = t_ = 0
            print("  --- [%s] PART A: half-year R/trade" % scope.upper())
            print("      %-8s %5s %9s   %5s %9s   %s"
                  % ("period", "nCtl", "ctl R/t", "nHyb", "hyb R/t", "hyb"))
            for k in keys:
                a, b = pa.get(k, []), pb.get(k, [])
                ra = [float(x["r_multiple"]) for x in a]
                rb = [float(x["r_multiple"]) for x in b]
                rta = sum(ra) / len(ra) if ra else 0.0
                rtb = sum(rb) / len(rb) if rb else 0.0
                if ra and rb:
                    if rtb > rta:
                        w += 1
                        mk = "hyb"
                    elif rtb < rta:
                        l += 1
                        mk = "ctl"
                    else:
                        t_ += 1
                        mk = "="
                else:
                    mk = "-"
                print("      %-8s %5d %+9.3f   %5d %+9.3f   %s"
                      % (k, len(ra), rta, len(rb), rtb, mk))
            print("      hybrid wins %d, loses %d, ties %d of %d"
                  % (w, l, t_, w + l + t_))
            ya, yb = agg_by(A, year), agg_by(B, year)
            print("  --- [%s] PART B: per YEAR, net and quality"
                  % scope.upper())
            print("      %-6s | %-22s | %-22s | %s"
                  % ("year", "champion n/net/PF", "hybrid n/net/PF",
                     "hybrid better?"))
            for y in sorted(set(ya) | set(yb)):
                a, b = ya.get(y, []), yb.get(y, [])
                ra = [float(x["r_multiple"]) for x in a]
                rb = [float(x["r_multiple"]) for x in b]
                na, nb = net_of(a), net_of(b)
                ok = (nb > na) if (a and b) else None
                print("      %-6d | %5d %+8.1fR %6.2f | %5d %+8.1fR %6.2f | %s"
                      % (y, len(a), na, pf(ra) if ra else 0.0,
                         len(b), nb, pf(rb) if rb else 0.0,
                         {True: "YES", False: "no"}.get(ok, "-")))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()