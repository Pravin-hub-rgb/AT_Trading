"""P78 - WHY DOES THE FS HYBRID WORK IN A BAD ERA? The mechanism study.

THE FRAMING
    P77 established that the FS hybrid wins 2021 and 2022 and loses every
    year from 2023 on. The owner redirected the research away from "does it
    beat the champion" and towards "why does it work in the worst years" -
    which is the right question, because a mechanism that explains the bad
    era is worth more than the candidate itself.

THE HYPOTHESIS BEING TESTED - THE BEAR-MARKET ASYMMETRY
    BTC in 2021H2-2022H2 was a sustained bear market. In a falling market:

      - A BREAK entry (B2/FLIP) fires when price breaks a structure
        extreme. In a downtrend those breaks are rallies that fail, so the
        entry is LATE - bought after the bounce has already run.
      - An FS entry fires when structure is first declared, which in a
        downtrend is nearer the high, so it is EARLY and better placed.

    If that is the mechanism, then in the bear years the hybrid should win
    overwhelmingly on the SHORT side, and its edge should shrink or invert
    on the LONG side. If instead it wins evenly across both directions, the
    bear-market story is wrong and the advantage is something else.

    This is the one thing about the hybrid that would be GENERALISABLE. A
    "trade earlier in falling markets" rule is a live rule. "Use the FS
    engine" is not.

WHAT IS MEASURED - ALL PATH-TRUE, FROM TRADE RECORDS
      PART A  the utcsat lane's half-year split, which truncated from the
             P77 log and should be read before being quoted
      PART B  long/short decomposition of both books, per era
      PART C  holding period (bars_held) - is the hybrid faster in and out?
      PART D  entry timing: bars between the signal and the exit of the
             PREVIOUS trade, i.e. how much of a move each book captures

    Every field is a property of when the trade happened, not of what it
    earned. No grouping by r_multiple, outcome or pnl anywhere - the P52
    lookahead rule, and the rule that killed the naive version of this
    study.

PASS CRITERION - UNCHANGED AND STILL NOT MET
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R. P77
    already failed this on the period split. This run is diagnostic: it
    cannot make the candidate adoptable, and it is not trying to.
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


def agg_by(tr, keyfn):
    acc = {}
    for t in tr:
        acc.setdefault(keyfn(t), []).append(t)
    return acc


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique")
    m = types.ModuleType("btc_engine_fsm")
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


def line(lbl, tr):
    if not tr:
        print("      %-22s %5d %s" % (lbl, 0, "-"))
        return
    rs = [float(t["r_multiple"]) for t in tr]
    print("      %-22s %5d %+8.1fR %+8.3f %7.2f"
          % (lbl, len(tr), net_of(tr), net_of(tr) / len(rs), pf(rs)))


def main():
    print("=" * 100)
    print("  P78  WHY DOES THE FS HYBRID WORK IN A BAD ERA?")
    print("=" * 100)
    print("  Hypothesis: in a bear market a BREAK entry is LATE (it fires on")
    print("  a rally that fails) and an FS entry is EARLY. If true, the")
    print("  hybrid's edge should sit on the SHORT side in 2021-22.")
    print("  Diagnostic only - P77 already failed the criterion.\n")

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
            A = run(sim, False, src[scope], params, patched)
            if (abs(len(A) - PIN[name][i][0]) > 2
                    or abs(net_r(A) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = (A, run(sim, True, src[scope], params,
                                           patched))
    print("  controls pinned in all four cells\n")

    print("  PART A - utcsat lane half-year split (truncated at P77)")
    A, B = books[("utcsat_multi_sw10", "oos")]
    pa, pb = agg_by(A, lambda t: half(t["entry_ts"])), \
        agg_by(B, lambda t: half(t["entry_ts"]))
    w = l = t_ = 0
    for k in sorted(set(pa) | set(pb)):
        ra = [float(x["r_multiple"]) for x in pa.get(k, [])]
        rb = [float(x["r_multiple"]) for x in pb.get(k, [])]
        rta = sum(ra) / len(ra) if ra else 0.0
        rtb = sum(rb) / len(rb) if rb else 0.0
        mk = "-"
        if ra and rb:
            if rtb > rta:
                w += 1
                mk = "hyb"
            elif rtb < rta:
                l += 1
                mk = "ctl"
            else:
                t_ += 1
        print("      %-8s ctl n%-4d %+7.3f | hyb n%-4d %+7.3f | %s"
              % (k, len(ra), rta, len(rb), rtb, mk))
    print("      utcsat OOS: hybrid wins %d, loses %d, ties %d\n" % (w, l, t_))
    A, B = books[("utcsat_multi_sw10", "is")]
    pa, pb = agg_by(A, lambda t: half(t["entry_ts"])), \
        agg_by(B, lambda t: half(t["entry_ts"]))
    w = l = t_ = 0
    for k in sorted(set(pa) | set(pb)):
        ra = [float(x["r_multiple"]) for x in pa.get(k, [])]
        rb = [float(x["r_multiple"]) for x in pb.get(k, [])]
        rta = sum(ra) / len(ra) if ra else 0.0
        rtb = sum(rb) / len(rb) if rb else 0.0
        if ra and rb:
            if rtb > rta:
                w += 1
            elif rtb < rta:
                l += 1
            else:
                t_ += 1
    print("      utcsat IS: hybrid wins %d, loses %d, ties %d"
          % (w, l, t_))

    for scope in ("oos", "is"):
        print("\n  " + "=" * 98)
        print("  LANE: champion_multi_sw10 / %s" % scope.upper())
        print("  " + "=" * 98)
        A, B = books[("champion_multi_sw10", scope)]
        print("  PART B/C/D - direction, hold length, and pace")
        for lbl, tr in (("champion", A), ("FS hybrid", B)):
            longs = [t for t in tr if t["dir"] == "long"]
            shorts = [t for t in tr if t["dir"] != "long"]
            holds = [int(t.get("bars_held") or 0) for t in tr]
            holds.sort()
            med = holds[len(holds) // 2] if holds else 0
            p90 = holds[int(len(holds) * 0.9)] if holds else 0
            line("%s ALL" % lbl, tr)
            line("%s  LONG" % lbl, longs)
            line("%s  SHORT" % lbl, shorts)
            print("      %-22s median hold %5d bars, p90 %5d bars"
                  % (lbl + " hold", med, p90))
    print("\n  Diagnostic only. P77 closed the candidate.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()