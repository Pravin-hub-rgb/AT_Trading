"""Era-split autopsy: WHY does 2021-22 differ from 2023-26?

Read-only diagnostics on champion_multi_sw10 + utcsat_multi_sw10:
  IS  = 2023-26 (get_data)
  OOS = 2021-22 (load_unseen)

Compares: per-year NET, break_kind / htf_regime / decisive share,
bars_held, risk%, WR, avgR, atr% at entry, hour, weekday, FTX window.
No engine patch. Both-sides numbers printed side by side.

Run: python live_stuff/tests/exp_era_split_autopsy.py
"""
import sys
import time
import bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def year_of(ts):
    # calendar year from unix seconds (UTC)
    return time.gmtime(int(ts)).tm_year


def full_stats(tr):
    if not tr:
        return dict(n=0, gross=0.0, net=0.0, wr=0.0, rpt=0.0, aw=0.0, al=0.0,
                    pf=0.0, dd=0.0, streak=0, fast=0, dec=0)
    rs = [float(t["r_multiple"]) for t in tr]
    nets = [net_r([t]) for t in tr]
    wins = [r for r in nets if r > 0]
    loss = [r for r in nets if r <= 0]
    net = sum(nets)
    wr = 100.0 * len(wins) / len(nets)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(loss) / len(loss) if loss else 0.0
    gp = sum(wins) if wins else 0.0
    gl = -sum(loss) if loss else 0.0
    pf = gp / gl if gl > 0 else float("inf")
    eq = peak = dd = 0.0
    mx = cur = 0
    for v in nets:
        eq += v
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > dd:
            dd = d
        if v > 0:
            cur += 1
            if cur > mx:
                mx = cur
        else:
            cur = 0
    fast = sum(1 for t in tr if int(t.get("bars_held") or 0) < 12)
    dec = sum(1 for t in tr if t.get("htf_regime") == "decisive")
    return dict(n=len(nets), gross=sum(rs), net=net, wr=wr,
                rpt=net / len(nets), aw=aw, al=al, pf=pf, dd=dd,
                streak=mx, fast=fast, dec=dec)


def fmt(s):
    pf = s["pf"]
    pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
    return (f"n={s['n']:>4} G={s['gross']:+7.1f} NET={s['net']:+7.1f} "
            f"WR={s['wr']:5.1f}% R/t={s['rpt']:+.3f} "
            f"avgW={s['aw']:+.2f} avgL={s['al']:+.2f} PF={pfs:>5} "
            f"DD={s['dd']:5.1f} st={s['streak']:>2} "
            f"fast%={100.0*s['fast']/max(s['n'],1):4.1f} dec={s['dec']:>3}")


def run(sim, params, c15, sw15, c1h, sw, fine):
    kw = {**BP, **params}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def features_of(tr, c15, sw15):
    ts15 = [int(c["ts"]) for c in c15]
    hi15 = [float(c["high"]) for c in c15]
    lo15 = [float(c["low"]) for c in c15]
    cl15 = [float(c["close"]) for c in c15]
    atrp = [0.0] * len(c15)
    for i in range(14, len(c15)):
        rng = sum(hi15[i - 13:i + 1][j] - lo15[i - 13:i + 1][j]
                  for j in range(14)) / 14
        atrp[i] = 100.0 * rng / cl15[i] if cl15[i] > 0 else 0.0

    rows = []
    for t in tr:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        if e_idx >= len(ts15):
            e_idx = len(ts15) - 1
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        d = 1 if t["dir"] == "long" else -1
        r = float(t["r_multiple"])
        bars = int(t.get("bars_held") or 0)
        hour = (E % 86400) // 3600
        wd = (E // 86400 + 4) % 7  # 0=Sun
        if d == 1:
            ext = min(lo15[max(0, e_idx - 48):e_idx + 1])
            mag = (entry - ext) / entry * 100 if entry else 0.0
        else:
            ext = max(hi15[max(0, e_idx - 48):e_idx + 1])
            mag = (ext - entry) / entry * 100 if entry else 0.0
        risk_pct = abs(entry - sl) / entry * 100 if entry else 0.0
        yr = year_of(E)
        # FTX crash window Nov 2022
        ftx = yr == 2022 and time.gmtime(E).tm_mon == 11
        rows.append({
            "r": r, "net": net_r([t]), "y": yr, "ftx": ftx,
            "kind": t.get("break_kind", "?"),
            "use": t.get("htf_regime", "flip"),
            "dec": t.get("htf_regime") == "decisive",
            "bars": bars, "fast": bars < 12,
            "hour": hour, "wd": wd,
            "atrp": atrp[e_idx] if 0 <= e_idx < len(atrp) else 0.0,
            "mag": mag, "risk": risk_pct,
            "dir": d,
        })
    return rows


def bucket(name, a_rows, b_rows, key_fn, bins, la="IS", lb="OOS"):
    print(f"\n  -- {name} --", flush=True)
    print(f"  {'bin':<14} | {'nA':>4} {'NET':>7} {'avgR':>7} {'WR%':>5} "
          f"| {'nB':>4} {'NET':>7} {'avgR':>7} {'WR%':>5} | {'d_avgR':>7}",
          flush=True)
    for b in bins:
        sa = [r for r in a_rows if key_fn(r) == b]
        sb = [r for r in b_rows if key_fn(r) == b]
        def line(sub):
            if not sub:
                return f"{'-':>4} {'-':>7} {'-':>7} {'-':>5}"
            n = len(sub)
            net = sum(r["net"] for r in sub)
            avg = net / n
            wr = 100.0 * sum(1 for r in sub if r["net"] > 0) / n
            return f"{n:4d} {net:+7.1f} {avg:+7.3f} {wr:5.1f}"
        na = sum(r["net"] for r in sa) / len(sa) if sa else None
        nb = sum(r["net"] for r in sb) / len(sb) if sb else None
        davg = (nb - na) if (na is not None and nb is not None) else None
        ds = f"{davg:+7.3f}" if davg is not None else f"{'-':>7}"
        print(f"  {b:<14} | {line(sa)} | {line(sb)} | {ds}", flush=True)


def main():
    t0 = time.time()
    print("=" * 110)
    print("  ERA-SPLIT AUTOPSY — why 2021-22 differs from 2023-26 (read-only)")
    print("=" * 110)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]

    print("loading OOS 2021-22...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"  OOS ready ({time.time()-t0:.0f}s)", flush=True)

    configs = [
        ("champion_multi_sw10", EXPERIMENTS["champion_multi_sw10"]["params"]),
        ("utcsat_multi_sw10 (king)", EXPERIMENTS["utcsat_multi_sw10"]["params"]),
    ]

    for name, params in configs:
        print("\n" + "=" * 110, flush=True)
        print(f"  {name}", flush=True)
        print("=" * 110, flush=True)

        tis = run(sim, params, c15, sw15, c1h, sw10, fine_is)
        tos = run(sim, params, c15o, sw15o, c1ho, sw10o, fineo)
        si, so = full_stats(tis), full_stats(tos)
        print(f"  IS  2023-26  {fmt(si)}", flush=True)
        print(f"  OOS 2021-22  {fmt(so)}", flush=True)

        # per-year
        print("\n  -- per-year NET (gross r then net via net_r) --", flush=True)
        by_y = defaultdict(list)
        for t in tis + tos:
            by_y[year_of(t["entry_ts"])].append(t)
        print(f"  {'year':>6} {'n':>5} {'GROSS':>8} {'NET':>8} {'WR%':>6} {'R/t':>7}",
              flush=True)
        for y in sorted(by_y):
            tr = by_y[y]
            g = sum(float(t["r_multiple"]) for t in tr)
            n = net_r(tr)
            wr = 100.0 * sum(1 for t in tr if float(t["r_multiple"]) > 0) / len(tr)
            print(f"  {y:>6} {len(tr):5d} {g:+8.1f} {n:+8.1f} {wr:6.1f} "
                  f"{n/len(tr):+7.3f}", flush=True)

        # FTX window
        ftx = [t for t in tos
               if year_of(t["entry_ts"]) == 2022
               and time.gmtime(int(t["entry_ts"])).tm_mon == 11]
        oos_nof = [t for t in tos if t not in ftx]
        if ftx:
            print(f"\n  FTX Nov-2022 window: n={len(ftx)} "
                  f"G={sum(float(t['r_multiple']) for t in ftx):+.1f} "
                  f"NET={net_r(ftx):+.1f} "
                  f" | OOS-ex-FTX n={len(oos_nof)} NET={net_r(oos_nof):+.1f}",
                  flush=True)

        fi = features_of(tis, c15, sw15)
        fo = features_of(tos, c15o, sw15o)

        bucket("break kind", fi, fo, lambda r: r["kind"],
               sorted(set(r["kind"] for r in fi + fo)))
        bucket("htf regime", fi, fo, lambda r: r["use"],
               ["flip", "b2", "decisive"])
        bucket("bars held", fi, fo,
               lambda r: ("a:<12" if r["bars"] < 12 else
                          "b:12-47" if r["bars"] < 48 else
                          "c:48-191" if r["bars"] < 192 else "d:192+"),
               ["a:<12", "b:12-47", "c:48-191", "d:192+"])
        bucket("atr% entry", fi, fo,
               lambda r: ("a:<0.3" if r["atrp"] < 0.3 else
                          "b:0.3-0.5" if r["atrp"] < 0.5 else
                          "c:0.5-0.8" if r["atrp"] < 0.8 else "d:0.8+"),
               ["a:<0.3", "b:0.3-0.5", "c:0.5-0.8", "d:0.8+"])
        bucket("risk %", fi, fo,
               lambda r: ("a:<0.5" if r["risk"] < 0.5 else
                          "b:0.5-1" if r["risk"] < 1 else
                          "c:1-2" if r["risk"] < 2 else "d:2+"),
               ["a:<0.5", "b:0.5-1", "c:1-2", "d:2+"])
        bucket("dir", fi, fo, lambda r: "long" if r["dir"] == 1 else "short",
               ["long", "short"])
        bucket("hour UTC", fi, fo,
               lambda r: ("a:0-6" if r["hour"] < 6 else
                          "b:6-12" if r["hour"] < 12 else
                          "c:12-18" if r["hour"] < 18 else "d:18-24"),
               ["a:0-6", "b:6-12", "c:12-18", "d:18-24"])
        bucket("weekday UTC", fi, fo,
               lambda r: f"wd{r['wd']}",
               [f"wd{i}" for i in range(7)])

        # market-level: candle ATR / range by year (context, not trades)
        print("\n  -- market context: 15m atr% mean by year --", flush=True)
        for label, candles in (("IS", c15), ("OOS", c15o)):
            hi = [float(c["high"]) for c in candles]
            lo = [float(c["low"]) for c in candles]
            cl = [float(c["close"]) for c in candles]
            ts = [int(c["ts"]) for c in candles]
            acc = defaultdict(list)
            for i in range(14, len(candles)):
                rng = sum(hi[i - 13:i + 1][j] - lo[i - 13:i + 1][j]
                          for j in range(14)) / 14
                if cl[i] > 0:
                    acc[year_of(ts[i])].append(100.0 * rng / cl[i])
            for y in sorted(acc):
                vals = acc[y]
                print(f"    {label} {y}: atr%_mean={sum(vals)/len(vals):.3f} "
                      f"n_bars={len(vals)}", flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
