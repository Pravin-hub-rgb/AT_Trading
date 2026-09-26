"""Loss-volume autopsy — what does volume DO into our losers?

Baseline trade list (fine fills, production params). For every trade:
  entry rvol/pct, mean rvol over hold, rvol at exit bar, volume expansion
  ratio during hold, rvol path (rising/falling), 1h rvol at entry.

Compare WIN vs LOSS distributions + bucket losses by common patterns.
Any pattern → volume-trail / volume-exit candidate for path-true.

Run: python live_stuff/tests/exp_volume_loss_autopsy.py
"""
import sys
import time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "live_stuff/tests"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

INSTRUMENT = "BTCUSDT_BYBIT"
PARAMS = {
    "sl_buf_atr": 0.01,
    "ext_stop_r": 1.5,
    "mode": "b2_vs_flip_chop",
    "chop_thresh": 58.0,
    "cooldown_bars": 10,
    "max_consecutive_losses": 3,
}


def load_tf(tf):
    df = load_btc_df(tf, INSTRUMENT)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        vol = float(getattr(row, "volume", 0.0) or 0.0)
        candles.append({
            "date": date, "ts": int(row.ts),
            "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close),
            "volume": vol,
        })
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def features(candles, roll_w):
    n = len(candles)
    vols = [c.get("volume") or 0.0 for c in candles]
    pref = [0.0] * (n + 1)
    for i, v in enumerate(vols):
        pref[i + 1] = pref[i] + v
    pct = [50.0] * n
    rvol = [1.0] * n
    for i in range(n):
        lo = max(0, i - roll_w)
        if i - lo < 8:
            continue
        window = vols[lo:i]
        cur = vols[i]
        pct[i] = 100.0 * sum(1 for x in window if x <= cur) / len(window)
        mean = (pref[i] - pref[lo]) / (i - lo)
        if mean > 0:
            rvol[i] = cur / mean
    return {"vol": vols, "pct": pct, "rvol": rvol, "pref": pref}


def bar_at(ts_list, entry_ts, step):
    import bisect
    target = entry_ts
    i = bisect.bisect_right(ts_list, target - step)
    if i - 1 >= 0 and ts_list[i - 1] + step == target:
        return i - 1
    return i - 1


def stats(rs):
    n = len(rs)
    if n == 0:
        return dict(n=0, net=0.0, wr=0.0, mean=0.0, med=0.0)
    xs = sorted(rs)
    med = xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])
    return dict(n=n, net=sum(rs), wr=100.0 * sum(1 for x in rs if x > 0) / n,
                mean=sum(rs) / n, med=med)


def show(title, rows, min_n=3):
    print(f"\n  === {title} ===")
    print(f"  {'bucket':<40} {'n':>5} {'NET':>8} {'WR%':>6} {'mean':>8} {'med':>8}")
    for lab, rs in rows:
        s = stats(rs)
        if s["n"] == 0:
            continue
        if s["n"] < min_n and not lab.startswith("ALL"):
            continue
        print(f"  {lab:<40} {s['n']:>5} {s['net']:>+8.1f} {s['wr']:>6.1f} "
              f"{s['mean']:>+8.3f} {s['med']:>+8.3f}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  LOSS-VOLUME AUTOPSY — common volume behaviour into SLs")
    print("=" * 100)

    c15, f15 = load_tf("15m")
    c1h, f1h = load_tf("1h")
    c5, f5 = load_tf("5m")
    print(f"  loaded 15m={len(c15)} 1h={len(c1h)} 5m={len(c5)}", flush=True)

    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    fine = _load_fine_1m(
        min(c1h[0]["ts"], c15[0]["ts"]),
        max(c1h[-1]["ts"], c15[-1]["ts"]),
        symbol=INSTRUMENT,
    )
    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine, **PARAMS
    )["ltf_trades"]
    print(f"  trades={len(tr)}  ({time.time()-t0:.0f}s)", flush=True)

    f15v = features(c15, 96)
    f1hv = features(c1h, 24)
    f5v = features(c5, 288)
    ts15 = [c["ts"] for c in c15]
    ts1h = [c["ts"] for c in c1h]
    ts5 = [c["ts"] for c in c5]
    v15 = f15v["vol"]
    r15 = f15v["rvol"]
    p15 = f15v["pct"]

    rows = []
    for t in tr:
        ets = int(t["entry_ts"])
        xts = int(t.get("exit_ts") or ets)
        i0 = bar_at(ts15, ets, 900)
        i1 = bar_at(ts15, xts, 900)
        if i1 < i0:
            i1 = i0
        h1 = bar_at(ts1h, ets, 3600)
        h5 = bar_at(ts5, ets, 300)
        if i0 < 0 or i0 >= len(c15):
            continue
        # hold-window volume features (causal up to exit for diagnosis)
        lo, hi = i0, min(i1, len(c15) - 1)
        hold_n = hi - lo + 1
        hold_sum = sum(v15[lo:hi + 1])
        # baseline = mean of prior 96 before entry
        b_lo = max(0, i0 - 96)
        base = (f15v["pref"][i0] - f15v["pref"][b_lo]) / max(1, i0 - b_lo)
        exp_ratio = (hold_sum / hold_n / base) if base > 0 and hold_n else 1.0
        # rvol path: mean rvol first half vs second half of hold
        mid = (lo + hi) // 2
        r_early = sum(r15[lo:mid + 1]) / max(1, mid - lo + 1)
        r_late = sum(r15[mid:hi + 1]) / max(1, hi - mid + 1)
        # rvol AT exit bar (climax?)
        r_exit = r15[hi]
        # volume rising into exit? exit bar vol vs entry bar vol
        v_exit_vs_entry = (v15[hi] / v15[i0]) if v15[i0] > 0 else 1.0
        # max adverse rvol: highest rvol while underwater — approximate:
        # use all bars in hold; for losses the whole hold is mostly underwater
        r_max = max(r15[lo:hi + 1]) if hold_n else r15[i0]
        # first 3 bars after entry rvol mean (post-entry surge?)
        r_first3 = sum(r15[i0:min(i0 + 3, len(r15))]) / min(3, len(r15) - i0)
        # was entry bar a volume spike?
        rows.append({
            "t": t,
            "r": float(t["r_multiple"]),
            "win": float(t["r_multiple"]) > 0,
            "kind": t.get("break_kind") or "?",
            "dir": t.get("dir"),
            "outcome": t.get("outcome") or "?",
            "rv_in": r15[i0],
            "pct_in": p15[i0],
            "rv_1h": f1hv["rvol"][h1] if 0 <= h1 < len(c1h) else 1.0,
            "rv_5m": f5v["rvol"][h5] if 0 <= h5 < len(c5) else 1.0,
            "exp_hold": exp_ratio,
            "r_early": r_early,
            "r_late": r_late,
            "r_exit": r_exit,
            "v_x_ve": v_exit_vs_entry,
            "r_max": r_max,
            "r_first3": r_first3,
            "hold": hold_n,
        })

    wins = [x for x in rows if x["win"]]
    losses = [x for x in rows if not x["win"]]

    def med(key, group):
        xs = sorted(g[key] for g in group)
        if not xs:
            return float("nan")
        m = len(xs) // 2
        return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])

    print("\n  --- WIN vs LOSS medians ---")
    keys = ["rv_in", "pct_in", "rv_1h", "rv_5m", "exp_hold", "r_early",
            "r_late", "r_exit", "v_x_ve", "r_max", "r_first3", "hold"]
    print(f"  {'feature':<14} {'WIN med':>10} {'LOSS med':>10}")
    for k in keys:
        print(f"  {k:<14} {med(k, wins):>10.3f} {med(k, losses):>10.3f}")

    # Outcome split: sl vs trail losses
    sl = [x for x in losses if x["outcome"] == "sl"]
    trl = [x for x in losses if x["outcome"] == "trail"]
    other = [x for x in losses if x["outcome"] not in ("sl", "trail")]
    print(f"\n  loss outcomes: sl={len(sl)} trail={len(trl)} other={len(other)}")
    print(f"  {'feature':<14} {'SL med':>10} {'TRAIL-loss med':>14}")
    for k in ["rv_in", "exp_hold", "r_late", "r_exit", "r_max", "r_first3"]:
        print(f"  {k:<14} {med(k, sl):>10.3f} {med(k, trl):>14.3f}")

    # Bucket losses by common patterns
    def loss_rs(pred):
        return [x["r"] for x in losses if pred(x)]

    def all_rs(pred):
        return [x["r"] for x in rows if pred(x)]

    show("LOSS patterns — entry rvol", [
        ("ALL losses", [x["r"] for x in losses]),
        ("loss & rv_in<0.5", loss_rs(lambda x: x["rv_in"] < 0.5)),
        ("loss & rv_in 0.5-1", loss_rs(lambda x: 0.5 <= x["rv_in"] < 1)),
        ("loss & rv_in>=1", loss_rs(lambda x: x["rv_in"] >= 1)),
        ("WIN & rv_in<0.5", [x["r"] for x in wins if x["rv_in"] < 0.5]),
        ("WIN & rv_in>=1", [x["r"] for x in wins if x["rv_in"] >= 1]),
    ])

    show("HOLD volume expansion (exp_hold = hold mean / trailing mean)", [
        ("ALL", [x["r"] for x in rows]),
        ("exp<0.7 (dry-up)", all_rs(lambda x: x["exp_hold"] < 0.7)),
        ("exp 0.7-1.3", all_rs(lambda x: 0.7 <= x["exp_hold"] < 1.3)),
        ("exp>=1.3 (flood)", all_rs(lambda x: x["exp_hold"] >= 1.3)),
        ("loss & exp<0.7", loss_rs(lambda x: x["exp_hold"] < 0.7)),
        ("loss & exp>=1.3", loss_rs(lambda x: x["exp_hold"] >= 1.3)),
        ("win & exp<0.7", [x["r"] for x in wins if x["exp_hold"] < 0.7]),
        ("win & exp>=1.3", [x["r"] for x in wins if x["exp_hold"] >= 1.3]),
    ])

    show("Volume RISING into exit (r_late vs r_early)", [
        ("ALL rising (r_late>r_early)", all_rs(lambda x: x["r_late"] > x["r_early"])),
        ("ALL falling", all_rs(lambda x: x["r_late"] <= x["r_early"])),
        ("loss rising", loss_rs(lambda x: x["r_late"] > x["r_early"])),
        ("loss falling", loss_rs(lambda x: x["r_late"] <= x["r_early"])),
        ("win rising", [x["r"] for x in wins if x["r_late"] > x["r_early"]]),
        ("win falling", [x["r"] for x in wins if x["r_late"] <= x["r_early"]]),
    ])

    show("Exit-bar volume climax (r_exit)", [
        ("ALL r_exit<0.5", all_rs(lambda x: x["r_exit"] < 0.5)),
        ("ALL r_exit 0.5-1.5", all_rs(lambda x: 0.5 <= x["r_exit"] < 1.5)),
        ("ALL r_exit>=1.5", all_rs(lambda x: x["r_exit"] >= 1.5)),
        ("loss r_exit>=1.5", loss_rs(lambda x: x["r_exit"] >= 1.5)),
        ("loss r_exit<0.5", loss_rs(lambda x: x["r_exit"] < 0.5)),
        ("win r_exit>=1.5", [x["r"] for x in wins if x["r_exit"] >= 1.5]),
        ("win r_exit<0.5", [x["r"] for x in wins if x["r_exit"] < 0.5]),
    ])

    show("Post-entry 3-bar surge (r_first3)", [
        ("ALL r_first3>=2", all_rs(lambda x: x["r_first3"] >= 2)),
        ("ALL r_first3 1-2", all_rs(lambda x: 1 <= x["r_first3"] < 2)),
        ("ALL r_first3<1", all_rs(lambda x: x["r_first3"] < 1)),
        ("loss r_first3>=2", loss_rs(lambda x: x["r_first3"] >= 2)),
        ("win r_first3>=2", [x["r"] for x in wins if x["r_first3"] >= 2]),
        ("loss r_first3<1", loss_rs(lambda x: x["r_first3"] < 1)),
        ("win r_first3<1", [x["r"] for x in wins if x["r_first3"] < 1]),
    ])

    show("Max rvol during hold (r_max) — spike-while-in-trade", [
        ("ALL r_max>=3", all_rs(lambda x: x["r_max"] >= 3)),
        ("ALL r_max 2-3", all_rs(lambda x: 2 <= x["r_max"] < 3)),
        ("ALL r_max<2", all_rs(lambda x: x["r_max"] < 2)),
        ("loss r_max>=3", loss_rs(lambda x: x["r_max"] >= 3)),
        ("win r_max>=3", [x["r"] for x in wins if x["r_max"] >= 3]),
        ("loss r_max<2", loss_rs(lambda x: x["r_max"] < 2)),
        ("win r_max<2", [x["r"] for x in wins if x["r_max"] < 2]),
    ])

    # Kind × loss volume (B2 losses dry vs flood)
    print("\n  --- B2/FLIP loss volume split ---")
    for kind in ("B2", "FLIP"):
        kloss = [x for x in losses if x["kind"] == kind]
        kwin = [x for x in wins if x["kind"] == kind]
        print(f"  {kind}: loss n={len(kloss)} med_rv_in={med('rv_in', kloss):.2f} "
              f"med_exp={med('exp_hold', kloss):.2f} med_r_exit={med('r_exit', kloss):.2f} | "
              f"win n={len(kwin)} med_rv_in={med('rv_in', kwin):.2f} "
              f"med_exp={med('exp_hold', kwin):.2f}")

    # Trail losses specifically: volume rising into trail-stop (premature tighten?)
    print("\n  --- TRAIL losses: did volume expand against us? ---")
    if trl:
        rising = [x for x in trl if x["r_late"] > x["r_early"]]
        falling = [x for x in trl if x["r_late"] <= x["r_early"]]
        print(f"  trail-loss rising vol: n={len(rising)} NET={sum(x['r'] for x in rising):+.1f}")
        print(f"  trail-loss falling vol: n={len(falling)} NET={sum(x['r'] for x in falling):+.1f}")
        spike = [x for x in trl if x["r_max"] >= 3]
        print(f"  trail-loss with r_max>=3: n={len(spike)} NET={sum(x['r'] for x in spike):+.1f}")

    # SL losses: volume dry-up into SL (no conviction) vs climax dump
    print("\n  --- SL losses: dry-up vs climax dump ---")
    if sl:
        dry = [x for x in sl if x["exp_hold"] < 0.7]
        flood = [x for x in sl if x["exp_hold"] >= 1.3]
        mid = [x for x in sl if 0.7 <= x["exp_hold"] < 1.3]
        print(f"  SL dry-up exp<0.7:  n={len(dry)} NET={sum(x['r'] for x in dry):+.1f}")
        print(f"  SL mid:             n={len(mid)} NET={sum(x['r'] for x in mid):+.1f}")
        print(f"  SL flood exp>=1.3:  n={len(flood)} NET={sum(x['r'] for x in flood):+.1f}")
        climax = [x for x in sl if x["r_exit"] >= 2]
        quiet = [x for x in sl if x["r_exit"] < 0.5]
        print(f"  SL climax r_exit>=2: n={len(climax)} NET={sum(x['r'] for x in climax):+.1f}")
        print(f"  SL quiet  r_exit<0.5: n={len(quiet)} NET={sum(x['r'] for x in quiet):+.1f}")

    # Common signature: entry quiet + hold dry + no exit climax = ?
    print("\n  --- combined signatures on ALL trades ---")
    sigs = [
        ("quiet entry + dry hold", lambda x: x["rv_in"] < 0.75 and x["exp_hold"] < 0.7),
        ("quiet entry + flood hold", lambda x: x["rv_in"] < 0.75 and x["exp_hold"] >= 1.3),
        ("loud entry + dry hold", lambda x: x["rv_in"] >= 1.25 and x["exp_hold"] < 0.7),
        ("loud entry + flood hold", lambda x: x["rv_in"] >= 1.25 and x["exp_hold"] >= 1.3),
        ("entry spike + exit quiet", lambda x: x["rv_in"] >= 1.5 and x["r_exit"] < 0.5),
        ("entry quiet + exit spike", lambda x: x["rv_in"] < 0.5 and x["r_exit"] >= 2),
        ("vol rising through hold", lambda x: x["r_late"] > x["r_early"] * 1.25),
        ("vol collapsing through hold", lambda x: x["r_late"] < x["r_early"] * 0.75),
    ]
    for lab, pred in sigs:
        sub = [x for x in rows if pred(x)]
        s = stats([x["r"] for x in sub])
        if s["n"]:
            n_w = sum(1 for x in sub if x["win"])
            n_l = s["n"] - n_w
            print(f"  {lab:<32} n={s['n']:3d} NET={s['net']:+7.1f} WR={s['wr']:5.1f}% "
                  f"(W{n_w}/L{n_l})")

    print(f"\n(done in {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
