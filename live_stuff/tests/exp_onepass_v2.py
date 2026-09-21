"""SEQUENTIAL ONE-PASS v2 — with L5 causal mark discovery (the deep live audit).

For every batch trade of champion_multi_sw10, build a TRUE causal chain at the
discovery instant:
  - declared swings = batch-chain swings with confirmed_at_idx <= slice end
    (valid: the batch chain is prefix-identical on truncation — chain-diff test)
  - the FORMING swing = the next batch swing, with seg.end clamped to the
    running extreme at the slice cut, and only its marks that fired before the
    cut (L5: forming-swing marks are real-time events, knowable at their bar)
  - indices remapped into slice space (L3)
Then run the sim on the causal slice (fine=[]), match the batch entry (L4 pad),
collect extras, and run the SEQUENTIAL state machine (cooldown+halt3) to get
the live-expected NET.

Run:  python live_stuff/tests/exp_onepass_v2.py [n_trades]
"""
import sys, time, bisect
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS, fund
from src.btc.btc_routes import _trade_costs
from src.walker import FlowCandle
import test_experiments_craze as craze

G_FEE, G_ES, G_XS = 0.055, 0.005, 0.01
DAY = 86400
BAR = 900
PAD = 2 * BAR


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, G_FEE, 0.0, G_ES, G_XS)
    f = fund(tr)
    return sum(rs) - c2 - f


def causal_chain(full_chain, candle_ts_full, slice_lo_full, slice_hi_full):
    """Causal chain at the slice cut: declared swings + ALL forming swings
    (multiple can be unconfirmed simultaneously — declaration lag), each with
    only its marks that fired before the cut, seg.end clamped to the cut."""
    out = []
    for si, s in enumerate(full_chain):
        seg = s.get("seg") or {}
        c_idx = s.get("confirmed_at_idx")
        c_idx = int(c_idx) if c_idx is not None else 10 ** 9
        s_idx = int(seg.get("start_idx", 10 ** 9))
        if s_idx > slice_hi_full:
            break  # chain is ordered; everything after started beyond the cut
        if s_idx < slice_lo_full:
            continue  # started before the slice window — warmup
        e_idx = int(seg.get("end_idx", -1))
        c = dict(s)
        newseg = dict(seg)
        newseg["start_idx"] = s_idx - slice_lo_full
        nb = []
        for b in (s.get("breaks") or []):
            bi = int(b["idx"])
            if slice_lo_full <= bi <= slice_hi_full:
                b2 = dict(b)
                b2["idx"] = bi - slice_lo_full
                nb.append(b2)
        c["breaks"] = nb
        c["swing_index"] = len(out)
        if c_idx <= slice_hi_full:
            # declared: full structure known
            newseg["end_idx"] = (e_idx - slice_lo_full) if e_idx >= 0 else -1
            c["seg"] = newseg
            c["confirmed_at_idx"] = c_idx - slice_lo_full
            c["confirmed_at_time"] = (s.get("confirmed_at_time", "") or "")[:19]
            c["forming"] = False
        else:
            # forming: end = running extreme at the cut (clamped)
            clamped = min(max(e_idx, s_idx), slice_hi_full) if e_idx >= 0 else slice_hi_full
            newseg["end_idx"] = clamped - slice_lo_full
            c["seg"] = newseg
            c["confirmed_at_idx"] = None
            c["confirmed_at_time"] = ""
            c["forming"] = True
        out.append(c)
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t0 = time.time()
    data = get_data()
    sim = craze.build_module()
    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    low15 = [float(c["low"]) for c in c15]
    high15 = [float(c["high"]) for c in c15]
    n15 = len(c15)
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}

    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print("batch: %d trades NET=%+.1f" % (len(batch), net_of(batch)))

    accepted = []
    extras = []
    seen_extra = set()
    repro = 0
    eligible = 0
    misses = defaultdict(int)
    E0 = ts15[0]

    trades = batch if not limit else batch[:limit]
    for i, t in enumerate(trades):
        E = int(t["entry_ts"])
        d = t["dir"]
        if E - E0 < 30 * DAY:
            continue
        eligible += 1
        lo_ts = E - 30 * DAY
        hi_ts = E + PAD
        lo = max(0, bisect.bisect_left(ts15, lo_ts))
        hi = min(n15 - 1, bisect.bisect_right(ts15, hi_ts) - 1)
        if hi - lo < 300:
            misses["slice-too-small"] += 1
            continue
        sl15 = c15[lo:hi + 1]
        f15 = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in sl15]

        chain15 = causal_chain(data["sw15"], ts15, lo, hi)

        # 1h side: FULL prefix (prefix-identical to batch => exact batch windows).
        # 15m side: causal slice (declaration-lag-safe chain + forming swings).
        try:
            r = sim(data["c1h"], data["sw10"], sl15, chain15, fine_ltf=data["fine"], **params)
        except Exception as ex:
            misses["sim-error:%s" % type(ex).__name__] += 1
            continue
        cand = r["ltf_trades"]

        hit = None
        for x in cand:
            if x["dir"] == d and E <= int(x["entry_ts"]) <= hi_ts:
                hit = x
                break
        if hit is not None:
            repro += 1
            accepted.append(hit)
        else:
            misses["no-repro"] += 1
        for x in cand:
            ets = int(x["entry_ts"])
            if E <= ets <= hi_ts:
                key = (ets, x["dir"], round(float(x["entry_price"]), 2))
                if key not in seen_extra:
                    seen_extra.add(key)
                    extras.append(dict(x))
        if (i + 1) % 50 == 0:
            print("  ... %d/%d (repro %d, extras %d) %.0fs" % (i + 1, len(trades), repro, len(extras), time.time() - t0))

    print("")
    print("reproduction: %d/%d (%.1f%%)   causal extras: %d" % (repro, eligible, 100.0 * repro / max(eligible, 1), len(extras)))
    print("miss reasons:", dict(misses))

    cd = params["cooldown_bars"]
    halt_n = params["max_consecutive_losses"]

    def sequential(cands):
        cands = sorted(cands, key=lambda x: (int(x["entry_ts"]), x["dir"]))
        kept = []
        last_loss_i = -10 ** 9
        consec = 0
        halt_skip = False
        for c in cands:
            ets = int(c["entry_ts"])
            i_bar = (ets - E0) // BAR
            if cd > 0 and i_bar - last_loss_i < cd:
                continue
            if halt_skip:
                halt_skip = False
                consec = 0
                continue
            kept.append(c)
            if float(c["r_multiple"]) < 0:
                last_loss_i = i_bar
                consec += 1
                if consec >= halt_n:
                    halt_skip = True
                    consec = 0
            else:
                consec = 0
        return kept

    live_m = sequential(accepted)
    live_a = sequential(accepted + extras)

    def report(tag, tr):
        if not tr:
            print("  %s: empty" % tag)
            return
        rs = [float(t["r_multiple"]) for t in tr]
        c2, _ = _trade_costs(tr, G_FEE, 0.0, G_ES, G_XS)
        f = fund(tr)
        net = sum(rs) - c2 - f
        pk = cm = dd = 0.0
        for x in rs:
            cm += x; pk = max(pk, cm); dd = max(dd, pk - cm)
        print("  %-30s n=%d gross=%+.1f NET=%+.1f DD=%.1f" % (tag, len(tr), sum(rs), net, dd))

    print("")
    print("=== LIVE-EXPECTED (one-pass v2: causal chain with L5 forming marks) ===")
    report("batch reference", batch)
    report("live: reproduced matches", live_m)
    report("live: matches + causal extras", live_a)


if __name__ == "__main__":
    main()

