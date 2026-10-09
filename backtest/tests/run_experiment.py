"""Single entry point for all experiments.

ONCE ON A FRESH CLONE, run this first:

    python exp_resultsdb.py ingest

    results.db is gitignored, so a fresh clone has none, and the database is
    what holds the book list - multi_books() and signal_books() read it, so
    exp_multi_metrics.py and exp_signal_metrics.py sweep zero books without it.
    The check command refuses to pass on an empty database for the same reason.

Usage:
    python exp_resultsdb.py ingest      # ONCE on a fresh clone, before anything else
    python run_experiment.py <key>          run one experiment
    python run_experiment.py --all          run all visible experiments
    python run_experiment.py --group <name> run a named group
    python run_experiment.py --list         show all experiments
    python run_experiment.py --audit        run full pre-live audit
    python run_experiment.py --diff <a> <b> compare two experiments

CURRENT LEADERS (2026-09-21, post deep audit):

    python run_experiment.py --group best      # the two leaders, one shot

    utcsat_multi_sw10              KING MULTI    454t +359.0R NET / DD 14.8 / WR 30.8%
        = champion_multi_sw10 + skip UTC-SATURDAY entries (exp_skip_utc_sat=1).
        The whole bleed is UTC-Saturday (-24R @ 91% loss on the single autopsy);
        UTC Sunday is PROFITABLE (+52R single / +124R multi) and is KEPT.
        WARNING: the weekend must be aligned to UTC — the IST date strings in the
        CSVs shift the calendar by 5h30m and an IST-weekend filter (nowknd_*)
        loses money on the multi (it throws away UTC Sun evening = IST Mon open).

    fullstack_wage10_cd0_single_sw10  KING SINGLE  200t +310.7R NET / DD 11.2 / WR 32.5%
        = swing_pause + wage_10h + IST-weekend skip + chop15 band (55-61) +
          ATR blow-off (≥1.4) + cd=0. Five stacked filters, all structural:
          chop-band removes choppy entries, ATR blow-off removes late trend entries,
          wage gate removes young windows, swingpause blocks after losses,
          weekend skip removes low-liquidity periods.
        Baseline: +137.7 / DD 29.2 / NET/DD 4.7 → now +310.7 / 11.2 / 27.7.

    champion_multi_sw10            CONSERVATIVE  500t +325.8R NET / DD 17.8 / WR 30.0%
        multi-position (exp_mltf) king on the 1h sw10 window chain, NO partials.
        Live needs a 4-5 position cap (cap-5 costs zero edge; see audit doc 3c).

    Run any variant with:
        python run_experiment.py wage10_swingpause_wskip_single_sw10
        python run_experiment.py --group best
        python run_experiment.py --group kingsweep
"""
import sys, time, json, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import EXPERIMENTS, GROUPS, BP, ENGINE_DEFAULTS
from test_experiments_craze import (
    build_module, load_candles, _compute_swings,
    SWING, MB15, INSTRUMENT, stats, BASE,
)
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _trade_costs
# The identity gate answers "does the patched module equal the engine it patches?"
# craze patches unified.py, so the comparison target must be unified.py. It used to
# import v18_streak_halt here, which made the gate diff two different books - v18's
# construction (minBars_1h=20, its own params) against unified's leg chain. It
# reported DIVERGED no matter what, and the only way to make it pass would have
# been to "fix" a divergence that was never in the harness.
#
# v18 is not lost: unified.py documents v18's pin on v18's OWN construction
# (max_positions=1, exp_persist=0, exp_causal_sl=0 -> 352 trades, v18's
# COUNT_BAND=(348,358)), and v18_streak_halt.py still exists for that. This gate
# is only patch-neutrality; verifying the v18 book is a different job.
#
# NOTE: the _shipped_* reference rows in experiment_registry.py carry v18-era pins
# (340 / 351 trades). They were measured through this import and will need
# re-anchoring on unified. They are reference rows, not books.
import src.btc.engines.htf_ltf.unified as shipped_mod

_g = _gvp(INSTRUMENT)


# ---------------------------------------------------------------------------
# Identity gate (structural, D3 2026-09-20): the patched engine with ALL flags
# off must reproduce the shipped engine's trade list EXACTLY, else nothing
# downstream is trustworthy. Basis: coarse 15m fills + chop 61.8 (the craze
# identity basis — this is what test_experiments_craze.main() asserts).
    #
    # ANCHOR RE-DERIVED 2026-10-01, was 340t / +225.3R. That was an ORIGIN-era
    # figure, so C16's pivot-rule flip moved this basis out from under the gate and
    # every harness calling it printed a warning. exp_identity_gate_drift.py
    # settles the cause rather than assuming it, running the shipped engine on
    # this same basis under both rules:
    #     pivot_rule="origin"  -> 340t / +225.3R   matches the old anchor exactly
    #     pivot_rule="leg"     -> 339t / +237.5R
    #     rule delta           ->  -1 trade, +12.3R
    # Same signature C16 left everywhere else: one trade, R moved, count nearly
    # identical. If this gate ever warns again, the cause is NOT the pivot rule.
# Runs once per process, before any experiment. Cheap (two sims, data cached).
# ---------------------------------------------------------------------------
# The gate runs on the v18 construction, not on the neutral default, so that
# "patched == shipped" is checked against a book that has an anchor with a
# stated provenance instead of a bare observation.
#
# 339t/+237.5R was removed as the gate's anchor. It was captured when shipped
# was v18_streak_halt; shipped is now unified, so the number moved for a reason
# that was itself verified (origin reproduces 500/+325.78/dd17.83, leg reproduces
# 499/+239.12). Re-recording the new number would just restate the output, so
# instead the gate is given a construction that an outside band can check.
#
# GATE_COUNT_BAND is shared with backend/tests/test_v18_causal_integrity.py and
# is honestly what it is: a band re-anchored on 2026-10-01 from a 352-trade
# measurement on Bybit perp, not a first-principles spec. It earns its place by
# being tolerant of small legitimate drift while still catching a gross move,
# and by having a second, independent consumer. It is not self-evidencing.
# NOTE: this uses BP, not the BASE imported from test_experiments_craze. The two
# differ by chop_thresh - BASE is 61.8, BP is the production 58.0 that
# btc_routes 914-918 ships. COUNT_BAND was measured on the production basis, so
# running the gate on BASE lands at 339, outside the band, for a reason that has
# nothing to do with the engine. On BP this construction reproduces 352, the
# band centre.
GATE_KW = {**dict(BP), "max_positions": 1, "exp_persist": 0, "exp_causal_sl": 0}
GATE_COUNT_BAND = (348, 358)

_id_gate = {"done": False}


def identity_gate(data=None, sim=None):
    if _id_gate["done"]:
        return
    if data is None:
        data = get_data()
    if sim is None:
        sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(
        data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=[], **GATE_KW)
    r_patch = sim(data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=[], **GATE_KW)
    ts_, tp_ = r_ship["ltf_trades"], r_patch["ltf_trades"]
    ok = (len(ts_) == len(tp_)
          and [t["r_multiple"] for t in ts_] == [t["r_multiple"] for t in tp_])
    g_ship = sum(float(t["r_multiple"]) for t in ts_)
    g_patch = sum(float(t["r_multiple"]) for t in tp_)
    print("[identity-gate] shipped %dt/%+.1fR vs patched-off %dt/%+.1fR -> %s" %
          (len(ts_), g_ship, len(tp_), g_patch, "IDENTICAL" if ok else "DIVERGED"))
    if not (GATE_COUNT_BAND[0] <= len(ts_) <= GATE_COUNT_BAND[1]):
        print("[identity-gate] WARNING: %dt falls outside the v18 production band %s"
              % (len(ts_), list(GATE_COUNT_BAND)))
        print("[identity-gate] the engine moved on the v18 construction; the band is "
              "shared with backend/tests/test_v18_causal_integrity.py and should move "
              "with it, deliberately, in both places at once")
    if not ok:
        raise SystemExit("IDENTITY GATE FAILED — patched engine no longer matches shipped; "
                         "all experiment results are untrustworthy until fixed")
    _id_gate["done"] = True

# ---------------------------------------------------------------------------
# D3 anchor audit (2026-09-20): load-bearing production constants — fail fast.
# min_bars_15m=50 is REQUIRED: the 15m chain length is the single most
# sensitive knob in the system (mb35 -> 437t / +58.3R vs mb50 -> 351t / +238.0R
# on the production basis). Docs/spec once claimed 35; production is 50.
# ---------------------------------------------------------------------------
assert SWING.get("min_bars_15m") == 50, \
    "min_bars_15m drifted to %r (production=50; mb35 collapses the anchor to +58R)" % SWING.get("min_bars_15m")
assert SWING.get("min_bars_1h") == 20, \
    "min_bars_1h drifted to %r (production=20)" % SWING.get("min_bars_1h")


# ---------------------------------------------------------------------------
# Cost model (matches exp40c/exp49 convention)
# ---------------------------------------------------------------------------
def fund(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f


def net_r(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


# ---------------------------------------------------------------------------
# Cached data loading
# ---------------------------------------------------------------------------
_cache = {}


def get_data():
    if "loaded" in _cache:
        return _cache["loaded"]
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    # htf15: the 1h swing series at min_bars=15, for the HTF-sweep candidate.
    # The HTF plane is engine slot 2, and this series feeds the leg ratio, the
    # bias-momentum breaks, the bias flips and _sw_ts_dir_mag (the flip/decisive
    # classification). sw10 is min_bars=10 and is what every registered book
    # ships on; this is the longer-leg variant that removes the single negative
    # half-year - see method/HTF_SWEEP_OWNER_RULE.md. It is a separate key rather
    # than a params entry because the swing series is chosen by the registry's
    # `swing` FIELD, not by an engine parameter, so a new HTF length needs a new
    # series here before a book can point at it.
    htf15 = _compute_swings(f1h, "continuous", min_bars=15)
    fine = _load_fine_1m(
        min(c1h[0]["ts"], c15[0]["ts"]),
        max(c1h[-1]["ts"], c15[-1]["ts"]),
        symbol=INSTRUMENT,
    )
    _cache["loaded"] = {
        "c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
        "sw15": sw15, "htf15": htf15, "sw20": sw20, "sw10": sw10, "fine": fine,
    }
    print("data loaded (%.0fs)" % (time.time() - t0), flush=True)
    return _cache["loaded"]


def _load_fine_1m(ts_start, ts_end, symbol="BTCUSDT"):
    try:
        from src.btc.btc_routes import _load_fine_1m as _lf
        return _lf(ts_start, ts_end, symbol=symbol)
    except Exception:
        return []


def get_swings(data, key):
    if key == "sw20":
        return data["sw20"]
    elif key == "sw10":
        return data["sw10"]
    elif key == "htf15":
        # 1h swings at min_bars=15 - the HTF plane at a longer leg. See the
        # construction note in get_data.
        return data["htf15"]
    elif key == "sw15":
        return data["sw15"]
    raise ValueError("unknown swing key: %s" % key)


# ---------------------------------------------------------------------------
# Run a single experiment
# ---------------------------------------------------------------------------
def run_one(key, data=None, sim=None):
    cfg = EXPERIMENTS[key]
    if data is None:
        data = get_data()
    if sim is None:
        sim = build_module()

    base = BP if cfg.get("use_bp", True) else ENGINE_DEFAULTS
    params = {**base, **cfg["params"]}
    sw = get_swings(data, cfg["swing"])
    # Fill basis: "fine" (default, 1m exits) or "coarse" (15m-bar exits).
    # The identity-gate reference rows run coarse; every strategy experiment runs fine.
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []

    t0 = time.time()
    if cfg["engine"] == "shipped":
        r = shipped_mod.simulate_htf_ltf_streak_halt(
            data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=fine, **params
        )
    else:
        r = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=fine, **params)

    tr = r["ltf_trades"] if isinstance(r, dict) else r
    elapsed = time.time() - t0
    return tr, elapsed


def _net_dd(tr):
    """Peak-to-trough on the NET equity curve (r_multiple minus cost_r).

    stats() reports the GROSS drawdown. Costs are a real drag on equity, so a
    book that is only flat on paper is not flat in the account. Every pin written
    on 2026-10-02 is on this basis; older pins are on the gross basis and are
    left alone so their comparison to history does not move.
    """
    peak = cum = dd = 0.0
    for t in tr:
        if t.get("outcome") == "open":
            continue
        cum += float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
        if cum > peak:
            peak = cum
        if peak - cum > dd:
            dd = peak - cum
    return dd


def evaluate(key, tr):
    cfg = EXPERIMENTS[key]
    s = stats(tr)
    n = s["n"]
    gross = s["gross"]
    # NET IS CLOSED-TRADES ONLY, the same basis as _net_stats, _net_dd and
    # every registry pin. net_r() sums every trade dict, including positions
    # still open at the era boundary; trail10_multi carries ten of those
    # (multi-year, +1040.6R of paper R) and unfiltered this line reported
    # net=793.1 against a pin of -247.5 - a FAIL the pin did nothing wrong to
    # earn. n and gross keep their old all-trades meaning: that is what the
    # pins' n counts and what the legacy gross pins were written on.
    nt = net_r([t for t in tr if t.get("outcome") != "open"])
    pins = cfg.get("pins") or {}
    partials = sum(1 for t in tr if t.get("partial_exit_price", 0.0) > 0)

    # Yearly breakdown
    py = defaultdict(float)
    for t in tr:
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[yr] += float(t["r_multiple"])

    # 6-segment WF (each ~60 trades)
    wf = []
    if n >= 60:
        seg_size = max(n // 6, 1)
        for seg in range(6):
            start = seg * seg_size
            end = min(start + seg_size, n)
            if start >= n:
                break
            seg_rs = [float(tr[i]["r_multiple"]) for i in range(start, end)]
            wf.append(sum(seg_rs))
    else:
        wf.append(gross)

    # Validate pins
    pin_ok = True
    pin_detail = ""
    if pins:
        checks = []
        if "n" in pins:
            checks.append(("n", n, pins["n"], n == pins["n"]))
        if "gross" in pins:
            checks.append(("gross", gross, pins["gross"], abs(gross - pins["gross"]) < 0.5))
        if "net" in pins:
            checks.append(("net", nt, pins["net"], abs(nt - pins["net"]) < 0.5))
        if "dd" in pins:
            # TWO DRAWDOWNS EXIST AND THEY ARE NOT THE SAME NUMBER.
            #
            #   dd      peak-to-trough on the GROSS equity curve (r_multiple
            #           only). This is what this runner has always reported and
            #           what every pre-2026-10-02 registry pin was written in.
            #   dd_net  peak-to-trough on the NET equity curve
            #           (r_multiple minus cost_r).
            #
            # The registry board and every pin written on 2026-10-02 use the NET
            # figure, because costs are a real drag on equity and a book that is
            # only flat on paper is not flat in the account. But this runner
            # computes gross, so a net pin read as a gross pin fails by ~10R on
            # every book - which is exactly what happened to champion_multi_sw10_leg
            # (gross 32.0, net 46.9) and to every decay book.
            #
            # Both are legitimate; comparing them is not. Check against whichever
            # the pin declares, and say so out loud when they disagree, rather
            # than leaving a pin that always fails and nobody can tell why.
            net_dd = _net_dd(tr)
            if "dd_net" in pins:
                checks.append(("dd_net", net_dd, pins["dd_net"], abs(net_dd - pins["dd_net"]) < 0.5))
            else:
                checks.append(("dd(gross-basis pin)", s["dd"], pins["dd"], abs(s["dd"] - pins["dd"]) < 0.5))
        for name, actual, expected, ok in checks:
            if not ok:
                pin_ok = False
                pin_detail += " %s=%.1f(expected %.1f)" % (name, actual, expected)

    return {
        "key": key,
        "desc": cfg["desc"],
        "n": n,
        "gross": gross,
        "net": nt,
        "wr": s["wr"],
        "dd": s["dd"],
        "mx": s["mx"],
        "partials": partials,
        "wf": wf,
        "worst_seg": min(wf) if wf else 0,
        "yearly": dict(py),
        "min_year": min(py.values()) if py else 0,
        "pin_ok": pin_ok,
        "pin_detail": pin_detail,
        # D3: basis label — fills basis + effective chop threshold
        "basis": "%s/c%.1f" % (cfg.get("basis", "fine"),
                               {**(BP if cfg.get("use_bp", True) else ENGINE_DEFAULTS),
                                **cfg.get("params", {})}["chop_thresh"]),
    }


def format_row(r, show_pins=True):
    pin_mark = "OK" if r["pin_ok"] else "FAIL" + r["pin_detail"]
    wf_str = " ".join(["%+.0f" % w for w in r["wf"]])
    return (
        "  %-30s %4dt G %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  "
        "streak %2d  part %2d  worst6 %+7.1f  minY %+7.1f  %s  %s  [%s]"
        % (
            r["key"], r["n"], r["gross"], r["net"], r["wr"], r["dd"],
            r["mx"], r["partials"], r["worst_seg"], r["min_year"],
            pin_mark if show_pins else "—",
            r.get("basis", ""),
            wf_str,
        )
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def cmd_list():
    print("\nRegistered experiments:")
    print("-" * 80)
    for key, cfg in sorted(EXPERIMENTS.items()):
        if key.startswith("_"):
            continue
        pin_str = ""
        if cfg.get("pins"):
            p = cfg["pins"]
            if "net" in p:
                pin_str = "  NET pin: %+.1f" % p["net"]
            elif "gross" in p:
                pin_str = "  gross pin: %+.1f" % p["gross"]
        print("  %-30s %s%s" % (key, cfg["desc"], pin_str))
    print("\nGroups:")
    for gname, gkeys in sorted(GROUPS.items()):
        if gkeys is None:
            print("  %-20s all visible experiments" % gname)
        else:
            print("  %-20s %s" % (gname, ", ".join(gkeys)))


def cmd_run(key):
    data = get_data()
    sim = build_module()
    identity_gate(data, sim)
    cfg = EXPERIMENTS[key]
    print("\n=== %s ===" % cfg["desc"])
    tr, elapsed = run_one(key, data, sim)
    r = evaluate(key, tr)
    print(format_row(r))
    print("  time: %.1fs" % elapsed)

    # Write JSON
    out = {
        "key": key,
        "desc": cfg["desc"],
        "params": {**BP, **cfg["params"]} if cfg.get("use_bp", True) else cfg["params"],
        "swing": cfg["swing"],
        "results": r,
        "trades": [
            {
                "entry_date": t.get("entry_date"),
                "exit_date": t.get("exit_date"),
                "dir": t.get("dir"),
                "entry_price": t.get("entry_price"),
                "exit_price": t.get("exit_price"),
                "sl": t.get("sl"),
                "r_multiple": t.get("r_multiple"),
                "outcome": t.get("outcome"),
                "bars_held": t.get("bars_held"),
                "partial_exit_price": t.get("partial_exit_price", 0.0),
                # audit trail: which 1h window this trade came from
                "htf_regime": t.get("htf_regime"),
                "window_start": t.get("window_start"),
                "window_end": t.get("window_end"),
                "sl": t.get("sl"),
                "target": t.get("target"),
                "break_kind": t.get("break_kind"),
            }
            for t in tr
        ],
    }
    json_path = ROOT / "backtest" / "tests" / ("_exp_%s_results.json" % key)
    json_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("  results -> %s" % json_path.name)
    return r


def cmd_all():
    data = get_data()
    sim = build_module()
    identity_gate(data, sim)
    results = []
    print("\n" + "=" * 100)
    print("RUNNING ALL EXPERIMENTS")
    print("=" * 100)
    for key in sorted(EXPERIMENTS.keys()):
        if key.startswith("_"):
            continue
        tr, elapsed = run_one(key, data, sim)
        r = evaluate(key, tr)
        print(format_row(r))
        results.append(r)
    # Summary
    print("\n" + "-" * 100)
    print("SUMMARY (sorted by NET)")
    print("-" * 100)
    for r in sorted(results, key=lambda x: x["net"], reverse=True):
        print(format_row(r, show_pins=False))
    # Write combined JSON
    json_path = ROOT / "backtest" / "tests" / "_exp_all_results.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("\n  combined results -> %s" % json_path.name)


def cmd_group(name):
    keys = GROUPS.get(name)
    if keys is None:
        cmd_all()
        return
    data = get_data()
    sim = build_module()
    identity_gate(data, sim)
    print("\n=== GROUP: %s ===" % name)
    for key in keys:
        tr, elapsed = run_one(key, data, sim)
        r = evaluate(key, tr)
        print(format_row(r))


def cmd_diff(key_a, key_b):
    data = get_data()
    sim = build_module()
    identity_gate(data, sim)
    tr_a, _ = run_one(key_a, data, sim)
    tr_b, _ = run_one(key_b, data, sim)
    ra = evaluate(key_a, tr_a)
    rb = evaluate(key_b, tr_b)
    print("\n=== DIFF: %s vs %s ===" % (key_a, key_b))
    print(format_row(ra))
    print(format_row(rb))
    print("\n  Delta: NET %+.1f  DD %+.1f  worst6 %+.1f" % (
        rb["net"] - ra["net"], rb["dd"] - ra["dd"], rb["worst_seg"] - ra["worst_seg"]))


def cmd_archive(name):
    """Run an archived experiment script with correct paths."""
    archive_dir = ROOT / "backtest" / "tests" / "_archive"
    if name.endswith(".py"):
        name = name[:-3]
    script = archive_dir / ("%s.py" % name)
    if not script.exists():
        # List available
        available = sorted([f.stem for f in archive_dir.glob("exp*.py")])
        print("Unknown archive: %s" % name)
        print("Available: %s" % ", ".join(available))
        raise SystemExit(1)
    import subprocess
    env = dict(__import__("os").environ)
    test_dir = str(ROOT / "backtest" / "tests")
    env["PYTHONPATH"] = test_dir + ";" + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT / "backtest" / "tests"),
        env=env,
        capture_output=False,
    )
    raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Experiment runner",
        epilog="Examples:\n"
               "  python run_experiment.py champion_multi_sw10\n"
               "  python run_experiment.py --all\n"
               "  python run_experiment.py --archive exp47_yearly_stats\n"
               "  python run_experiment.py --list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("key", nargs="?", help="Experiment key (see --list)")
    parser.add_argument("--all", action="store_true", help="Run all experiments")
    parser.add_argument("--group", help="Run a named group")
    parser.add_argument("--list", action="store_true", help="List experiments")
    parser.add_argument("--audit", action="store_true", help="Run deep audit")
    parser.add_argument("--diff", nargs=2, metavar="KEY", help="Compare two experiments")
    parser.add_argument("--archive", metavar="NAME", help="Run an archived experiment script")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.all:
        cmd_all()
    elif args.group:
        cmd_group(args.group)
    elif args.audit:
        print("Running deep audit...")
        from exp_deep_audit import main as audit_main
        audit_main()
    elif args.diff:
        cmd_diff(args.diff[0], args.diff[1])
    elif args.archive:
        cmd_archive(args.archive)
    elif args.key:
        if args.key not in EXPERIMENTS:
            print("Unknown experiment: %s" % args.key)
            print("Available: %s" % ", ".join(k for k in sorted(EXPERIMENTS) if not k.startswith("_")))
            raise SystemExit(1)
        cmd_run(args.key)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
