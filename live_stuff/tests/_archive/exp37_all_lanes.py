"""Exp 37 — ALL FOUR LANES, one background run (coarse; fine for survivors)."""
import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
OUT = {}

def run(tag, sim, c1h, sw1h, c15, sw15, **kw):
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show(tag, s)
    OUT[tag] = dict(n=s["n"], gross=round(s["gross"], 1), wr=round(s["wr"], 1),
                    dd=round(s["dd"], 1), mx=s["mx"], h1=round(s["h1"], 1),
                    h2=round(s["h2"], 1), py={k: round(v, 1) for k, v in sorted(s["py"].items())})
    return tr, s

def cap2(tr):
    kept, open_ = [], []
    for t in sorted(tr, key=lambda x: int(x["entry_ts"])):
        open_ = [o for o in open_ if int(o["exit_ts"]) > int(t["entry_ts"])]
        if len(open_) < 2:
            kept.append(t); open_.append(t)
    return kept

def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    print("chains ready (%.0fs)" % (time.time() - t0), flush=True)

    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    show("shipped-anchor", s_ship)
    r0 = sim(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
    t0_ = r0["ltf_trades"] if isinstance(r0, dict) else r0
    s0 = stats(t0_)
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (%dt exact)" % s0["n"], flush=True)

    print("\n=== LANE A: anchor superstack (coarse) ===", flush=True)
    run("A0-anchor-lb14", sim, c1h, sw1h20, c15, sw15, **BP)
    run("A1-anchor-lb30", sim, c1h, sw1h20, c15, sw15, **{**BP, "exp31_lb": 30})
    run("A2-lb30+chop55+mb10", sim, c1h, sw1h10, c15, sw15,
        **{**BP, "exp31_lb": 30, "chop_thresh": 55.0})
    run("A3-A2+persist5", sim, c1h, sw1h10, c15, sw15,
        **{**BP, "exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 5})
    run("A4-A2+persist2", sim, c1h, sw1h10, c15, sw15,
        **{**BP, "exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2})
    run("A5-lb30+persist5(mb20)", sim, c1h, sw1h20, c15, sw15,
        **{**BP, "exp31_lb": 30, "exp_persist": 5})

    print("\n=== LANE B: halt behaviour on anchor-lb30 (coarse) ===", flush=True)
    lb30 = {**BP, "exp31_lb": 30}
    tr_nohalt, _ = run("B0-lb30-halt0", sim, c1h, sw1h20, c15, sw15,
                       **{**lb30, "max_consecutive_losses": 0})
    tr_h3, _ = run("B1-lb30-halt3", sim, c1h, sw1h20, c15, sw15,
                   **{**lb30, "max_consecutive_losses": 3})
    h3_ts = set(int(t["entry_ts"]) for t in tr_h3)
    skipped = [t for t in tr_nohalt if int(t["entry_ts"]) not in h3_ts]
    sr = sum(float(t["r_multiple"]) for t in skipped)
    print("  B-skipped-by-halt3: %dt R=%+.1f" % (len(skipped), sr), flush=True)
    OUT["B-skipped"] = dict(n=len(skipped), gross=round(sr, 1))
    run("B2-lb30-halt6", sim, c1h, sw1h20, c15, sw15,
        **{**lb30, "max_consecutive_losses": 6})
    run("B3-lb30-halt3-cd0", sim, c1h, sw1h20, c15, sw15,
        **{**lb30, "max_consecutive_losses": 3, "cooldown_bars": 0})

    print("\n=== LANE C: mltf post-fix (coarse) ===", flush=True)
    opt = {**BP, "chop_thresh": 55.0, "exp_persist": 2, "cooldown_bars": 0}
    run("C0-anchor-lb14", sim, c1h, sw1h20, c15, sw15, **BP)
    tr_c1, _ = run("C1-OPT-mltf-cd0-mb10", sim, c1h, sw1h10, c15, sw15,
                   **{**opt, "exp_mltf": True})
    s_c1c = stats(cap2(tr_c1))
    show("C1-cap2", s_c1c)
    OUT["C1-cap2"] = dict(n=s_c1c["n"], gross=round(s_c1c["gross"], 1),
                          dd=round(s_c1c["dd"], 1), h1=round(s_c1c["h1"], 1),
                          h2=round(s_c1c["h2"], 1))
    tr_c2, _ = run("C2-OPT-mltf-cd10-mb10", sim, c1h, sw1h10, c15, sw15,
                   **{**{**opt, "cooldown_bars": 10}, "exp_mltf": True})
    s_c2c = stats(cap2(tr_c2))
    show("C2-cap2", s_c2c)
    OUT["C2-cap2"] = dict(n=s_c2c["n"], gross=round(s_c2c["gross"], 1),
                          dd=round(s_c2c["dd"], 1), h1=round(s_c2c["h1"], 1),
                          h2=round(s_c2c["h2"], 1))
    evs = []
    for t in tr_c1:
        evs.append((int(t['entry_ts']), 1))
        evs.append((int(t['exit_ts']), -1))
    evs.sort()
    cur = 0
    mxc = 0
    for _e in evs:
        cur += _e[1]
        mxc = max(mxc, cur)
    print('  C1 maxconcurrent:', mxc, flush=True)
    OUT['C1-maxconcurrent'] = mxc
    print("\n=== LANE D: loss autopsy anchor-lb30 (coarse) ===", flush=True)
    import bisect as bs
    from datetime import datetime, timezone
    from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h, _atr_pct_15m
    r_lb30 = sim(c1h, sw1h20, c15, sw15, fine_ltf=[], **{**BP, "exp31_lb": 30})
    trd = r_lb30["ltf_trades"] if isinstance(r_lb30, dict) else r_lb30
    chop = _chop_series_1h(c1h, lb=30)
    atrp = _atr_pct_15m(c15)
    ts15 = [c["ts"] for c in c15]
    ts1h_close = [c["ts"] + 3600 for c in c1h]
    o15 = [c["open"] for c in c15]; c15c = [c["close"] for c in c15]
    hi15 = [c["high"] for c in c15]; lo15 = [c["low"] for c in c15]
    atr15 = [0.0] * len(c15)
    for i in range(1, len(c15)):
        tr_ = max(hi15[i] - lo15[i], abs(hi15[i] - c15c[i - 1]), abs(lo15[i] - c15c[i - 1]))
        atr15[i] = atr15[i - 1] + (tr_ - atr15[i - 1]) / 14 if i >= 14 else tr_
    def chop_at(bar_ts):
        j = bs.bisect_right(ts1h_close, bar_ts + 900) - 1
        return chop[j] if 0 <= j < len(chop) else 50.0
    rows = []; consec = 0
    for t in trd:
        i = int(t["entry_idx"]); d = 1 if t["dir"] == "long" else -1
        entry = float(t["entry_price"]); sl = float(t["sl"])
        risk = abs(entry - sl); bar_ts = ts15[i]; rm = float(t["r_multiple"])
        chase = 0
        for j in range(i, 0, -1):
            if d == 1 and c15c[j] > o15[j]: chase += 1
            elif d == -1 and c15c[j] < o15[j]: chase += 1
            else: break
        slw = risk / atr15[i] if atr15[i] > 0 else 0.0
        if d == 1:
            ext = max(hi15[max(0, i - 96):i + 1]); room = (ext - entry) / risk if risk > 0 else 0.0
        else:
            ext = min(lo15[max(0, i - 96):i + 1]); room = (entry - ext) / risk if risk > 0 else 0.0
        ch = chop_at(bar_ts); ap = atrp[i] if i < len(atrp) else 0.5
        apct = 100.0 * sum(1 for x in atrp[max(0, i - 500):i + 1] if x <= ap) / max(min(i, 500), 1)
        hour = datetime.fromtimestamp(bar_ts, tz=timezone.utc).hour
        pre = consec
        if rm < 0: consec += 1
        else: consec = 0
        rows.append(dict(r=rm, win=rm > 0, chase=chase, slw=slw, room=room,
                         chop=ch, apct=apct, hour=hour, streak=pre,
                         date=t.get("entry_date", "")))
    def bucket(name, pred):
        sel = [x for x in rows if pred(x)]
        if not sel:
            print("  %-22s n=0" % name, flush=True); return
        rs_ = sum(x["r"] for x in sel)
        wr = 100.0 * sum(x["win"] for x in sel) / len(sel)
        h1 = sum(x["r"] for x in sel if x["date"][:4] in ("2023", "2024"))
        h2 = sum(x["r"] for x in sel if x["date"][:4] in ("2025", "2026"))
        print("  %-22s n=%4d R=%+8.1f WR=%4.1f%% H1=%+7.1f H2=%+7.1f"
              % (name, len(sel), rs_, wr, h1, h2), flush=True)
        OUT["D-" + name] = dict(n=len(sel), gross=round(rs_, 1),
                                h1=round(h1, 1), h2=round(h2, 1))
    losses = [x for x in rows if not x["win"]]; wins = [x for x in rows if x["win"]]
    print("POP: %d | %d losses (avg %+.2f) | %d wins (avg %+.2f)"
          % (len(rows), len(losses), sum(x["r"] for x in losses) / len(losses),
             len(wins), sum(x["r"] for x in wins) / len(wins)), flush=True)
    for lo, hi in [(0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.8), (0.8, 99)]:
        bucket("slw %.2f-%.2f" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["slw"] < hi)
    for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 5), (5, 99)]:
        bucket("chase %d-%d" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["chase"] < hi)
    for lo, hi in [(0, 50), (50, 58), (58, 65), (65, 75), (75, 200)]:
        bucket("chop %.0f-%.0f" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["chop"] < hi)
    for lo, hi in [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]:
        bucket("atrpct %.0f-%.0f" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["apct"] < hi)
    for a, b in [(0, 8), (8, 13), (13, 17), (17, 21), (21, 24)]:
        bucket("hour %02d-%02d" % (a, b), lambda x, a=a, b=b: a <= x["hour"] < b)
    bucket("streak>=3", lambda x: x["streak"] >= 3)
    bucket("streak>=5", lambda x: x["streak"] >= 5)
    (ROOT / "live_stuff/tests/_exp37_results.json").write_text(json.dumps(OUT, indent=1))
    print("\n(exp37 coarse done %.0fs — results saved)" % (time.time() - t0), flush=True)

if __name__ == "__main__":
    main()


