"""Single entry point for all experiments.

Usage:
    python run_experiment.py <key>          run one experiment
    python run_experiment.py --all          run all visible experiments
    python run_experiment.py --group <name> run a named group
    python run_experiment.py --list         show all experiments
    python run_experiment.py --audit        run full pre-live audit
    python run_experiment.py --diff <a> <b> compare two experiments

CURRENT LEADERS (2026-09-20, post D3 audit — see docs/ANCHOR_BASIS_AUDIT.md):

    python run_experiment.py --group best      # the two leaders, one shot

    champion_multi_sw10      KING         500t +325.8R NET / DD 17.8 / WR 30.0%
        multi-position (exp_mltf) king on the 1h sw10 window chain, NO partials.
        Live needs a 4-5 position cap (cap-5 costs zero edge; see audit doc 3c).

    utcsat_multi_sw10        NEW KING     454t +359.0R NET / DD 14.8 / WR 30.8%
        = champion_multi_sw10 + skip UTC-SATURDAY entries (exp_skip_utc_sat=1).
        The whole bleed is UTC-Saturday (-24R @ 91% loss on the single autopsy);
        UTC Sunday is PROFITABLE (+52R single / +124R multi) and is KEPT.
        WARNING: the weekend must be aligned to UTC — the IST date strings in the
        CSVs shift the calendar by 5h30m and an IST-weekend filter (nowknd_*)
        loses money on the multi (it throws away UTC Sun evening = IST Mon open).

    nowknd_swingpause_single_sw10  BEST SINGLE  294t +217.6R NET / DD 18.2 / WR 29.6%
        Single-position config: structural swing-pause (exp_swingpause) + skip
        IST-weekend entries (exp_skip_weekend). On the single the IST-aligned
        weekend skip measured BEST (vs UTC-Sat-only +166.3 / UTC Sat+Sun +150.0)
        — cascade effects differ per config; both are pinned for comparison.
        Fully causal / live-implementable. Baseline was +137.7 / DD 29.2.

    swingpause_single_sw10   BEST SINGLE  357t +174.8R NET / DD 23.4 / WR 25.8%
        Single-position config whose loss gate is STRUCTURAL: after a loss, no
        re-entry until a 15m swing FORMED AFTER that loss confirms (fresh
        structure). cooldown_bars=8 is redundant with it (cd0 == cd8; run
        swingpause_cd0_single_sw10 to verify). Fully causal / live-implementable:
        at entry time you need only your last loss time + your swing chain's
        last confirmed pivot time. Beats every previous single config on R, DD
        and NET/DD (baseline single: +137.7 / DD 29.2 / 4.7 -> 174.8 / 23.4 / 7.5).

    Run any variant with:
        python run_experiment.py swingpause_single_sw10
        python run_experiment.py --group cooldown   # the full cooldown family
"""
import sys, time, json, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import EXPERIMENTS, GROUPS, BP, ENGINE_DEFAULTS
from test_experiments_craze import (
    build_module, load_candles, _compute_swings,
    SWING, MB15, INSTRUMENT, stats, BASE,
)
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

_g = _gvp(INSTRUMENT)


# ---------------------------------------------------------------------------
# Identity gate (structural, D3 2026-09-20): the patched engine with ALL flags
# off must reproduce the shipped engine's trade list EXACTLY, else nothing
# downstream is trustworthy. Basis: coarse 15m fills + chop 61.8 (the craze
# identity basis — this is what test_experiments_craze.main() asserts, 340t/+225.3).
# Runs once per process, before any experiment. Cheap (two sims, data cached).
# ---------------------------------------------------------------------------
_id_gate = {"done": False}


def identity_gate(data=None, sim=None):
    if _id_gate["done"]:
        return
    if data is None:
        data = get_data()
    if sim is None:
        sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(
        data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=[], **dict(BASE))
    r_patch = sim(data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=[], **dict(BASE))
    ts_, tp_ = r_ship["ltf_trades"], r_patch["ltf_trades"]
    ok = (len(ts_) == len(tp_)
          and [t["r_multiple"] for t in ts_] == [t["r_multiple"] for t in tp_])
    g_ship = sum(float(t["r_multiple"]) for t in ts_)
    g_patch = sum(float(t["r_multiple"]) for t in tp_)
    print("[identity-gate] shipped %dt/%+.1fR vs patched-off %dt/%+.1fR -> %s" %
          (len(ts_), g_ship, len(tp_), g_patch, "IDENTICAL" if ok else "DIVERGED"))
    if abs(len(ts_) - 340) > 1 or abs(g_ship - 225.3) > 0.5:
        print("[identity-gate] WARNING: shipped anchor drifted from 340t/+225.3R "
              "(coarse+chop61.8) — reference pins may be stale")
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
    fine = _load_fine_1m(
        min(c1h[0]["ts"], c15[0]["ts"]),
        max(c1h[-1]["ts"], c15[-1]["ts"]),
        symbol=INSTRUMENT,
    )
    _cache["loaded"] = {
        "c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
        "sw15": sw15, "sw20": sw20, "sw10": sw10, "fine": fine,
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


def evaluate(key, tr):
    cfg = EXPERIMENTS[key]
    s = stats(tr)
    n = s["n"]
    gross = s["gross"]
    nt = net_r(tr)
    pins = cfg.get("pins", {})
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
            checks.append(("dd", s["dd"], pins["dd"], abs(s["dd"] - pins["dd"]) < 0.5))
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
            }
            for t in tr
        ],
    }
    json_path = ROOT / "live_stuff" / "tests" / ("_exp_%s_results.json" % key)
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
    json_path = ROOT / "live_stuff" / "tests" / "_exp_all_results.json"
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
    archive_dir = ROOT / "live_stuff" / "tests" / "_archive"
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
    test_dir = str(ROOT / "live_stuff" / "tests")
    env["PYTHONPATH"] = test_dir + ";" + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT / "live_stuff" / "tests"),
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
