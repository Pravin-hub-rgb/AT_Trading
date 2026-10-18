# UNIFIED HTF/LTF ENGINE - one implementation of v18_streak_halt and v19_champion.
#
# WHY. The two engines were 99.1% identical (781 of 788 lines) and differed in
# seven blocks, five of which were INSERTIONS into v18. That made the duplication
# cheap to remove but hard to gate: the proposed verification compared 352
# against 499 and attributed the gap to concurrency, when it was at least three
# things at once - engine, four parameters, and the 1h swing chain.

# WHAT THIS IS. v19's body, which already carries exp_persist, exp_causal_sl and
# pivot_rule, PLUS the one thing v19 removed: the position gate. Four parameters
# cover the entire behavioural difference between the two engines:
#
#   max_positions   1 = serial (v18)   0 = unlimited (v19)   the position gate
#   exp_persist     0 = off (v18)      N = hysteresis (v19)  regime stickiness
#   exp_causal_sl   0 = swing_start_px (v18)   1 = running extreme  SL pivot source
#   pivot_rule      leg | origin       the C16 rule, in BOTH engines

# Everything else is identical, which is the point.
#
# VERIFICATION. Both pins, each on its OWN construction:
#   max_positions=1, exp_persist=0, exp_causal_sl=0, v18 params, v18 swing chain
#       -> 352 trades          (v18's COUNT_BAND=(348,358) anchor)
#   max_positions=0, exp_persist=7, v19 params, leg swing chain
#       -> 499 / +239.1R IS, 280 / +72.8R OOS   (the shipping book)
#
# A refactor that moves either pin by one trade has changed behaviour. Do not
# merge one without the other.
#
# v18_streak_halt.py and v19_champion.py are now thin shims over this file.


# V19 CHAMPION - backtest champion. Real code, not a source patch.
# SCOPE: this is a BACKTEST engine. There is no live engine in this work.
# live_loop.py is stale and still imports v18, so nothing here is deployed and
# nothing here is a claim about a running bot. This file is a research object.
#
# v18_streak_halt.py with two behaviours made permanent. P114 measured
# what each one is actually worth, and they are not equal:
#
#   1. No position limit - the one-position gate is removed and busy_until
#      is never armed, so a window may hold overlapping entries. This is
#      the multi in champion_multi_sw10, and it is the entire edge. With
#      the gate on, the same config is +137.72R IS but -13.26R OOS over
#      230 trades. Turning it off gives +325.78R IS / +70.15R OOS.
#
#   2. Regime hysteresis, PERSIST=7 - on a regime flip, keep trading the
#      previous regime for 7 consecutive disagreements before switching.
#      INHERITED, NOT EARNED. In isolation it is bit-identical on IS
#      (500 trades, +325.78R, PF 2.384 either way) and costs 2.40R on
#      OOS. It was never tested alone. It is kept because removing it is
#      a separate open question, not because it carries the result.
#
# Twelve functional lines differ from v18. The ~100 other harness knobs
# are research scaffolding and are not copied here. A production engine
# ships one frozen strategy, not a flag zoo.
#
# Evidence: P112 (rebuild + trade audit), P113 (ratchet clamp rejected),
# P114 (flag attribution). Harness: exp_v19_2x2.py.

"""v11_conditional_htf â€” HTF conditional break: when to use B2 vs Flip vs Decisive.
HTF 1h: if regime is chop (HIGH chop >61.8 or LOW vol) -> use Decisive (B2|FLIP) window, else use Flip window.
LTF 15m: decisive MB50 0.25ATR ext-stop1.5 MB50 trail, same as v5.
Costs 0.05%+2pt, 1m fine, stream.
Separate engine, never disturb v5.
Ref: permutation fix choppy 2023 decisiveÃ—decisive +37.7 vs flipÃ—decisive -7.2 (+44.9R) but total 122 vs 168 (-46R) fix/permutation_htf_ltf.md:7, Exp4 LOW vol 309 +133 vs HIGH vol 17 +12, MED chop 366 +130 vs HIGH chop 24 +9.9 fix/v5:172, firstswing chop v4_chop.py:26, ATR% 15m.
"""
from __future__ import annotations
import bisect
from typing import Optional

def _chop_series_1h(candles_1h, lb=14):
    n=len(candles_1h)
    # TR for 1h
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles_1h[i]["high"]); lo=float(candles_1h[i]["low"])
        if i==0:
            tr[i]=hi-lo
        else:
            pc=float(candles_1h[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    chop=[50.0]*n
    import math
    for i in range(lb, n):
        tr_sum=sum(tr[i-lb+1:i+1])
        hi_max=max(float(candles_1h[j]["high"]) for j in range(i-lb+1, i+1))
        lo_min=min(float(candles_1h[j]["low"]) for j in range(i-lb+1, i+1))
        rang=hi_max-lo_min
        if rang>0 and tr_sum>0:
            try:
                chop[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
            except:
                chop[i]=50.0
        else:
            chop[i]=50.0
    return chop

def _ext_level(hrisk, ext_stop_pct, sample, ext_stop_r_default):
    """The admission threshold for ext_stop_r, as a fixed level or a percentile.

    With ext_stop_pct at 0 (the shipped default) this returns ext_stop_r and
    nothing changes. With it above 0 the threshold is the given percentile of the
    extensions seen SO FAR in this run, so the gate blocks the same fraction of
    entries regardless of how volatile the period is.

    Causal and deliberately so. The percentile is built from extensions already
    computed during this walk, never from the final answer, so a bar cannot be
    blocked by knowledge of a later bar. Until enough samples exist to mean
    anything it falls back to the fixed level rather than extrapolating from a
    handful of points - a gate that swings wildly early in a run is worse than no
    percentile at all.
    """
    if ext_stop_pct <= 0.0:
        return ext_stop_r_default
    if hrisk <= 0:
        return 0.0
    if len(sample) < 30:
        return ext_stop_r_default
    s = sorted(sample)
    i = min(len(s) - 1, max(0, int(ext_stop_pct * (len(s) - 1))))
    return s[i]


def _atr_pct_15m(candles_15m):
    n=len(candles_15m)
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles_15m[i]["high"]); lo=float(candles_15m[i]["low"])
        if i==0:
            tr[i]=hi-lo
        else:
            pc=float(candles_15m[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    atr=[0.0]*n
    for i in range(n):
        lo_i=max(0,i-13)
        atr[i]=sum(tr[lo_i:i+1])/(i-lo_i+1)
    pct=[atr[i]/float(candles_15m[i]["close"])*100 if float(candles_15m[i]["close"])!=0 else 0 for i in range(n)]
    return pct

def _hmm_regime_1h(candles_1h, train_frac=0.45, n_iter=40, seed=0):
    """Idea A â€” 2-state Gaussian HMM on 1h log-returns. Range vs trend router.

    Train Baum-Welch on the first train_frac only (rest never seen by params),
    then causal forward-filter the WHOLE series with frozen params. numpy only.
    Returns P(range)*100 per 1h bar (0..100). Range = state with lower
    |mu|/sigma (less directional drift per unit vol).
    """
    import numpy as np
    n = len(candles_1h)
    if n < 80:
        return [50.0] * n
    cl = np.fromiter((float(c["close"]) for c in candles_1h), dtype=np.float64, count=n)
    ret = np.zeros(n, dtype=np.float64)
    np.log(cl[1:] / cl[:-1], out=ret[1:], where=cl[:-1] > 0)
    n_train = max(60, int(n * train_frac))
    x = ret[1:n_train]
    T = len(x)
    if T < 40:
        return [50.0] * n
    ax = np.abs(x)
    z = (ax <= np.median(ax)).astype(np.int64)

    def _mu_var(sel):
        xs = x[sel]
        if xs.size < 2:
            return 0.0, 1e-4
        m = float(xs.mean())
        return m, float(xs.var()) + 1e-8

    mu = np.array([_mu_var(z == 0)[0], _mu_var(z == 1)[0]])
    var = np.array([_mu_var(z == 0)[1], _mu_var(z == 1)[1]])
    A = np.array([[0.95, 0.05], [0.05, 0.95]], dtype=np.float64)
    pi = np.array([0.5, 0.5], dtype=np.float64)

    def log_gauss(v, m, s2):
        return -0.5 * (np.log(2.0 * np.pi * s2) + (v - m) ** 2 / s2)

    def fwd(logB, A_, pi_):
        T_ = logB.shape[0]
        la = np.empty((T_, 2), dtype=np.float64)
        lA = np.log(A_ + 1e-300)
        la[0] = np.log(pi_ + 1e-300) + logB[0]
        for t in range(1, T_):
            m = la[t - 1][:, None] + lA
            mx = m.max(axis=0)
            la[t] = logB[t] + mx + np.log(np.exp(m - mx).sum(axis=0) + 1e-300)
        return la

    def bwd(logB, A_):
        T_ = logB.shape[0]
        lb = np.zeros((T_, 2), dtype=np.float64)
        lA = np.log(A_ + 1e-300)
        for t in range(T_ - 2, -1, -1):
            m = lA + (logB[t + 1] + lb[t + 1])[None, :]
            row = m.max(axis=1)
            lb[t] = row + np.log(np.exp(m - row[:, None]).sum(axis=1) + 1e-300)
        return lb

    logB = np.column_stack([log_gauss(x, mu[0], var[0]), log_gauss(x, mu[1], var[1])])
    for _ in range(n_iter):
        la = fwd(logB, A, pi)
        lb = bwd(logB, A)
        lg = la + lb
        lg -= lg.max(axis=1, keepdims=True)
        gam = np.exp(lg)
        gam /= gam.sum(axis=1, keepdims=True) + 1e-300
        lxi = (la[:-1, :, None] + np.log(A + 1e-300)[None, :, :]
               + (logB[1:] + lb[1:])[:, None, :])
        lxi -= lxi.max(axis=(1, 2), keepdims=True)
        xi = np.exp(lxi)
        xi /= xi.sum(axis=(1, 2), keepdims=True) + 1e-300
        A = xi.sum(axis=0)
        A /= A.sum(axis=1, keepdims=True) + 1e-300
        pi = gam[0] / (gam[0].sum() + 1e-300)
        for k in range(2):
            w = gam[:, k]
            ws = w.sum() + 1e-300
            mu[k] = float((w * x).sum()) / ws
            var[k] = float((w * (x - mu[k]) ** 2).sum()) / ws + 1e-8
        logB = np.column_stack([log_gauss(x, mu[0], var[0]), log_gauss(x, mu[1], var[1])])
    snr = np.abs(mu) / np.sqrt(var)
    range_k = int(np.argmin(snr))
    logBf = np.column_stack([log_gauss(ret[1:], mu[0], var[0]),
                             log_gauss(ret[1:], mu[1], var[1])])
    laf = fwd(logBf, A, pi)
    out = [50.0] * n
    for t in range(laf.shape[0]):
        row = laf[t] - laf[t].max()
        p = np.exp(row)
        out[t + 1] = float(p[range_k] / (p.sum() + 1e-300) * 100.0)
    return out


def _garch_regime_1h(candles_1h, train_frac=0.45, a=0.1, b=0.85, lb=96):
    """Idea F â€” GARCH(1,1) predicted-vol regime score on 1h closes.

    omega/alpha/beta frozen from train prefix (path-true); recursive
    sigma2 filter over full series. Returns range-score 0..100 per 1h bar
    (high = low predicted vol = quiet/range), comparable to chop_thresh.
    numpy-free.
    """
    n = len(candles_1h)
    if n < 80:
        return [50.0] * n
    cl = [float(c["close"]) for c in candles_1h]
    ret = [0.0] * n
    for i in range(1, n):
        ret[i] = (cl[i] - cl[i - 1]) / cl[i - 1] if cl[i - 1] > 0 else 0.0
    n_train = max(60, int(n * train_frac))
    x = ret[1:n_train]
    if len(x) < 40:
        return [50.0] * n
    var = sum(v * v for v in x) / len(x)
    omega = max(var * (1.0 - a - b), 1e-14)
    sig2 = [var] * n
    for i in range(1, n):
        sig2[i] = omega + a * ret[i - 1] * ret[i - 1] + b * sig2[i - 1]
    out = [50.0] * n
    for i in range(lb, n):
        w = sig2[i - lb:i + 1]
        cur = sig2[i]
        below = sum(1 for v in w if v < cur)
        out[i] = 100.0 * (1.0 - below / float(len(w)))
    return out


def _r_touch_end(trade, fine_ltf, fine_ts, ext_r):
    """HTF window end = first ts price touches ext_r (1.5R) from HTF entry.
    'We reach 1.5R -> we are done, look for new bias.'
    If SL/cap exit comes first (level never reached), window ends there (bias dead)."""
    d=1 if trade["dir"]=="long" else -1
    pe=float(trade["entry_price"]); psl=float(trade["sl"])
    hrisk=abs(pe-psl)
    if hrisk<=0 or ext_r<=0 or not fine_ltf:
        return int(trade["exit_ts"])
    level=pe+ext_r*hrisk*d
    e_ts=int(trade["exit_ts"])
    import bisect as _b
    k=_b.bisect_right(fine_ts, int(trade["entry_ts"]))
    while k < len(fine_ltf):
        ts=int(fine_ltf[k]["ts"])
        if ts > e_ts: break
        hi=float(fine_ltf[k]["high"]); lo=float(fine_ltf[k]["low"])
        if (d==1 and hi>=level) or (d==-1 and lo<=level):
            return ts
        k+=1
    return e_ts

# Every branch of the regime-mode chain inside
# simulate_htf_ltf_streak_halt(). Kept here, next to the chain, so that adding a
# mode is a two-line change: add the elif, add the name. The chain raises on
# anything not in this set - see the guard above `for sig in ltf_sigs:`.
HTF_MODES = frozenset((
    "chop",                    # decisive when 1h chop is high, else flip
    "atr_low",                 # decisive when ATR% is low, else flip
    "atr_high",                # decisive when ATR% is high, else flip
    "chop_or_atr_low",
    "chop_and_atr_low",
    "b2_vs_flip_chop",         # B2 when chop high, else flip
    "decisive_vs_flip_chop",
    "htf_dir",                 # B2 when the 1h swing direction agrees
    "htf_mag",
    "htf_mag_inv",
    "flip_quality",            # b2_vs_flip_chop plus a magnitude floor
    "ltf_dir",
    "dynamic_chop",
    "union",                   # take whichever of B2/FLIP exists at all
    "session",                 # Asia -> B2, London/NY -> flip
    "session_flip",            # the inverse of session; used as its control
    "entropy", "entropy_inv",
    "fd", "fd_inv",
    "hmm", "hmm_inv",
    "garch", "garch_inv",
    "soft_chop", "soft_atr", "soft_ensemble",
))

def simulate_htf_ltf_streak_halt(
    candles_htf, swings_htf, candles_ltf, swings_ltf, fine_ltf=None,
    *,
    sl_buf_atr=0.25, ext_stop_r=1.5,
      # UNIFIED: ext_stop_r IN PERCENTILE TERMS. 0.0 = off, which is the shipped
      # behaviour and reproduces every pin exactly.
      #
      # WHY IT EXISTS. ext_stop_r answers "how far has price already travelled
      # from this window's open, in units of the window's own risk". That number
      # is not comparable across time: a 3R move means something different when
      # the swing is wide than when it is tight, and 2021-22 measured 3.5x more
      # volatile than 2023-26 on the engine's own ATR. So one fixed value sets a
      # different effective gate in each regime, which is exactly the signature
      # that made htf_rr look like it had a regime-dependent optimum.
      #
      # SEMANTICS: replace the fixed level with the given PERCENTILE of ext
      # across this run's own candidate signals, so the gate blocks the same
      # FRACTION of entries in every regime instead of the same distance.
      #
      #   0.0     off - use ext_stop_r as shipped
      #   0.70    block the top 30% of entries by extension
      #   0.85    block the top 15%
      #   0.95    block the top 5%
      #
      # Applied at both admission sites (the union branch at ~1212 and the
      # decisive/flip/b2 branch at ~1261) so the gate means one thing. The
      # percentile is computed once per run, causally, from the candidate
      # signals available at that point in the walk - not from the final answer.
      ext_stop_pct=0.0,
      # UNIFIED: HTF TRADE RISK MANAGEMENT, decoupled from the target.
      #
      # The HTF trade is currently a fixed target and a fixed stop: it aims at
      # htf_rr and its stop is the swing start (sl_mode="swing"). That welds two
      # decisions together - how far to aim, and what happens on failure - and
      # the htf_rr sweep showed that aiming further has a knife-edge break-even:
      # 79% of 3R-reachers carried on to 4R against 97% in the other era, with
      # break-even at roughly 80%. A parameter sitting on its own break-even
      # gives opposite answers in two markets for no structural reason, and no
      # state variable can fix that because the population itself changed.
      #
      # These two knobs remove the choice instead of trying to predict it.
      #
      #   htf_breakeven_r   once price reaches this multiple of risk, move the
      #                     stop to breakeven. 0.0 = off (shipped). A failure then
      #                     costs 0R instead of the full risk, which drops the
      #                     required carry rate from ~80% toward zero.
      #   htf_trail         "off" (shipped) or "swing", which lets a trade that
      #                     reached breakeven keep running to a new swing pivot.
      #
      # Already implemented downstream at v7_timecap.py:119 - this only makes
      # the two reachable from a book instead of hardcoded to 0.0/"off".
      htf_breakeven_r=0.0,
      # UNIFIED: DIRECTIONAL HTF TARGET. 0.0 = off (use htf_rr for both
      # directions, which is the shipped behaviour). Above zero, SHORT trades aim
      # there while LONG trades keep htf_rr.
      #
      # Direction is known when the order is placed, so this needs no prediction and
      # no lookahead - which is the entire reason it is worth having when eight
      # state-variable signals all flipped between eras.
      htf_rr_short=0.0,
      htf_trail="off",
    chop_thresh=61.8, atr_low_thresh=0.35, atr_high_thresh=0.65,
    mode="chop",  # chop, atr_low, atr_both, chop_or_atr, soft_chop, soft_atr, soft_ensemble, garch, garch_inv
    soft_width=4.0,  # Idea D: half-width of soft band (0 = hard switch)
    cooldown_bars=0,
    max_consecutive_losses=0,  # 0 = no halt, N = halt after N consecutive losses
    htf_rr=3.0,  # HTF (1h) fixed R target â€” controls when window closes
    window_end="exit",  # "exit" = HTF trade exit (SL/target/16-day cap) [default, +331R];
                        # "r_touch" = first touch of ext_stop_r 1.5R [tested: +200.6R, -130R vs exit]
    # v19: SL pivot source. 0 = RETROACTIVE (default, what the champion was measured
    # with): sl_pivot = sig["swing_start_px"], the swing's true origin. That origin is
    # only knowable once the leg has completed, so using it at the entry bar is
    # lookahead - commit 484fe2a quantified it at -63R to -78R on IS. It was never
    # applied to the engine; this flag is that fix, finally in the engine.
    # 1 = CAUSAL: sl_pivot = the running extreme since the last CONFIRMED swing, keyed
    # on confirmed_at_idx, so the value is knowable at the entry bar.
      # UNIFIED: LTF stop source, controlled separately from pivot_rule, which
      # selects the HTF side's pivot. The two halves were never linked.
      #   0  running extreme up to and INCLUDING the entry bar (current rule)
      #   1  the same, minus the entry bar - so a book can exclude the entry
      #      candle on BOTH legs, matching pivot_rule="leg_no_entry" on the HTF.
      # Default 0: identical to every measurement pinned before this existed.
      exp_ltf_no_entry=0,
      exp_causal_sl=0,
      # HTF-SIDE FS ENTRY - "the window opens on FS" (owner ask 2026-10-09).
      #   "" (default) = off. The HTF side enters on the flip/decisive/b2 BREAK,
      #     exactly as before, so every book pinned before this exists is
      #     byte-identical.
      #   "flip" / "all" = the HTF side enters on the swing FS PRINT instead of
      #     the break, using the same machinery the LTF plane already uses via
      #     exp_fs_entry_side. This closes a real asymmetry: on the LTF plane we
      #     enter at the swing FS, on the HTF plane we enter at the break. The
      #     measured gap is large - the HTF window opens a MEDIAN 25 HOURS after
      #     the FS print of its own direction (p75 55h, max 355h), and only
      #     1 window in 528 opens exactly on its FS. So "trade on FS" is true
      #     on one plane and false on the other.
      #     "flip" moves only the flip bucket (the one the shipping books use);
      #     "all" moves all three buckets, which collapses the flip/decisive/b2
      #     distinction into one set of FS-entered windows.
      #     Causal: fs_at_idx is at or after the swing end bar, so that bar has
      #     closed before the print is used. Same guarantee the LTF side relies on.
      exp_htf_fs_entry="",
      # WINDOW FLOOR - how long after an HTF window OPENS must you wait before it
      # is tradeable. Was a hardcoded 45-minute wait and was never a
      # parameter, so it was the one axis of the HTF window that could not be
      # swept at all. This is a different axis from exp_htf_fs_entry: that changes
      # WHEN the window opens (FS print vs break), this changes how long you wait
      # after it opened.
      exp_window_floor_s=2_700,  # default reproduces the original gate exactly. Written 2_700, not 2700, so the 2h-plane patcher in exp_tf_family.py can count its own gate sites without tripping on the signature.
      #   "fixed" = s + exp_window_floor_s, the original behaviour.
      #   "fs"    = the FS print of the swing governing the window, i.e. the window
      #             becomes tradeable the moment its own structure confirmed.
      #   "max"   = whichever of the two is later. Strictly tighter than either
      #             alone, so it cannot admit anything they would reject.
      # Causal: fs_at_idx is at or after the swing end bar, so that bar has closed
      # before the print is used - the same guarantee exp_fs_entry_side relies on.
      exp_window_floor_mode="fixed",
      # UNIFIED: position limit. 1 = serial (v18 behaviour, busy_until gate armed)
      #   0 = unlimited (v19 behaviour, gate never fires). This is the ONLY
      #   behavioural difference v19 introduced to the position path; everything
      #   else v19 added was exp_persist, exp_causal_sl and pivot_rule, all of which
      #   v18 already handled or already defaulted off.
max_positions=0,
      # UNIFIED: cap on SIMULTANEOUSLY OPEN positions, as distinct from
      # max_positions which is the serial 1/0 gate above. Needed because
      # max_positions>0 uses the single `busy_until` timestamp, which cannot
      # express "at most N open" - it only knows when the last booked trade
      # closed. N=0 (the default) disables the cap entirely and must reproduce
      # every shipped pin exactly; it adds no gate of any kind.
      #
      # Reads the booked trades' own entry_ts/exit_ts, both of which are settled
      # before the NEXT entry is considered, so a position is never counted as
      # open using a number that was not knowable when the entry decision was
      # made. Counts a trade as open on [entry_ts, exit_ts] inclusive, matching
      # how the concurrency census in exp_maxcap_sweep.py counts it.
      exp_max_concurrent=0,
      # UNIFIED: MINIMUM STOP DISTANCE, as a fraction of entry price. 0.0 = off,
      # which is the shipped behaviour and reproduces every pin exactly.
      #
      # WHY IT EXISTS. The engine already refuses a stop inside 0.05% of price
      # (`risk < 0.0005*entry -> continue`), and that floor is far too small to
      # trade: on BTC at 40k that is $20, so round-trip fees and any sane
      # slippage eat the whole edge of the trade. This knob makes that floor a
      # stated, sweepable number instead of an accident of the pivot's geometry.
      #
      # SEMANTICS: SKIP, not widen. A stop that is too tight is not a trade with a
      # small stop, it is a trade that cannot be placed - widening it would move
      # the risk and the 3R target with it and silently turn the sweep into a
      # different book. Skipping keeps every kept trade's geometry exactly what
      # the pivot said it was.
      #
      #   0.0     off (shipped)
      #   0.002   0.20% - roughly $80 at 40k
      #   0.004   0.40%
      #   0.006   0.60%
      #   0.010   1.00%
      exp_min_sl_pct=0.0,
      # UNIFIED: ADVERSE STOP-FILL SLIPPAGE, in basis points of the fill price.
      # 0.0 = off, which is the shipped behaviour and reproduces every pin exactly.
      #
      # WHY IT EXISTS. The backtest fills a stop at min(sl, bar_open) - at the
      # stop price, or at the open when the bar gapped through it. The exchange
      # does not. A stop is a conditional MARKET order on Bybit (tpslMode=Full),
      # so a wick through the stop fills wherever the wick went, which is worse
      # than the stop price every single time. That difference is the only place
      # a backtest R and a live R can diverge, and until this knob existed there
      # was no way to measure it: `net_r` applies fees AFTER a trade is booked, so
      # scaling costs changes arithmetic and not which trades exist.
      #
      # SEMANTICS: adverse only, applied to the exit fill, never to the entry.
      #   0.0     off (shipped)
      #   10      0.10%
      #   50      0.50%
      #   100     1.00%
      #   1000    10.00% - the doc's "what if slippage got catastrophic" end
      #
      # Applied to all four stop/trail fill sites, long and short, intrabar and
      # the end-of-data finalize path, so the knob means one thing everywhere.
      # It does NOT move which trades qualify: the stop is still tested at
      # sl_cur. Only the price you get is worse, which is what the exchange does.
      exp_stop_slip_bps=0.0,
      # UNIFIED: OPPOSITE-DIRECTION LOCK. 0 = off (shipped). 1 = while any trade
      # is open, refuse a NEW entry in the opposite direction; same-direction
      # entries stay allowed.
      #
      # This is NOT exp_max_concurrent and NOT max_positions. max_positions>0
      # serialises on `busy_until`, which blocks EVERY entry while a trade is
      # open, in either direction - strictly stronger than what is asked for
      # here. exp_max_concurrent caps the count but ignores direction. Neither
      # can express "flat and long may coexist, long and short may not".
      #
      # The owner's reason for wanting it is live, not statistical: holding a
      # long and a short at the same time on one symbol nets to roughly zero
      # price exposure while paying two lots of fees, so the pair cancels the
      # book instead of compounding it. On a single-position book this cannot
      # arise; on the unlimited-concurrency book it does, on the same symbol.
      #
      # Causal: a position counts as open on [entry_ts, exit_ts] inclusive, and
      # both ends are settled before the next entry is considered - the same
      # interval convention exp_max_concurrent uses, and the same one
      # exp_maxcap_sweep.py counts with. Direction is the direction of the trade
      # being BLOCKED, compared against every currently-open trade.
      #
      # 2026-10-16: DEFAULT IS NOW 1, ON. Owner decision, on the strength of the
      # exposure argument above and not the R - the R is close to neutral and was
      # never the reason. Re-measured on this corrected engine across all 54
      # pinned books / 108 book-eras (exp_no_opposite.py), because the only prior
      # figures were from 2026-10-08 and predate the causal-stop fix:
      #
      #   35,078 trades -> 476 refused (1.36%)
      #   net better 43 / worse 30 / unchanged 35, sum of changes +266.91R
      #   drawdown better 19 / worse 6
      #
      # So it is cheap, it fires rarely, and it helps more often than it hurts.
      # Set to 0 per-book only to reproduce a historical trade list - every pin
      # in the registry was re-derived under this default.
      exp_no_opposite=1,
      # UNIFIED: regime hysteresis. v19 hardcoded PERSIST=7 in the function body,
      # so it could not be switched off and v18 could not share the code path.
      #
      # DEFAULT IS 0 = OFF, and that is deliberate. The engine default answers
      # "what does an unspecified knob do?", and the honest answer for a
      # stickiness filter is "nothing" - same reason max_positions defaults to
      # 0 and exp_causal_sl defaults to 0. Hysteresis is not part of the core
      # HTF->LTF theory; it is one book's config.
      #
      # The value 7 belongs to champion_multi_sw10_leg, which sets it in the
      # registry. It was hardcoded here before, which meant every book that did
      # not ask for hysteresis silently got it. Books that want it now say so.
      #   0 = off (v18 behaviour, and every historical book measured this way)
      #   N = hold the old regime for N consecutive disagreements before flip
      exp_persist=0,
    # C16 SL pivot rule, applied to BOTH halves of this engine.
    #   "leg"    (default) - the swing's own extreme up to and including the break
    #                       bar. Causal, live-computable. This is what ships.
    #   "origin"          - the swing's declared seg_start. Lookahead; retained
    #                       only so the pre-C16 baseline stays reproducible.
    # Forwarded to the three HTF windows (via simulate_btc_trades_v7) and to the
    # LTF signal collection. Before this was explicit, the HTF half could not be
    # selected at all: v7_timecap binds _collect_signals at module import, so it
    # silently kept whatever the default was and the two halves diverged.
    pivot_rule="leg",
    # P4 window time cap, in days, forwarded to the three HTF window builders.
    #   16  = what has always shipped, and still the default here
    #   999 = effectively off (v7 treats 0 as off too, so 0 is not a separate arm)
    # This was hardcoded as cap_days=16 at all three call sites until 2026-10-02,
    # which meant the whole cap_days family documented in CAPS_P49.md could not
    # be reproduced on this engine at all - there was no knob to turn. CAPS_P49
    # reports removing the cap at +75.3R IS / +55.1R OOS on the champion and
    # +13.7R / +78.5R on utcsat, 4/4 positive, adding trades rather than removing
    # them. That finding has never been reproduced here. It is a direction, not
    # an adoption: P49 itself records that no arm beats 16 in both eras by more
    # than noise, and that the sweep is non-monotonic.
    exp_cap_days=16,
    # P36 decay gate. 0 = off, which is the default and keeps every historical
    # book measured as-is. Modes are the P36 grid's rule letters: 1 block<-
    # buying, 2 block<-selling, 3 own side, 4 crossed, 5-8 the ALLOW mirrors.
    # The gate runs at the entry bar and reads only legs CONFIRMED by then, so
    # it is causal in the same sense pivot_rule="leg" is.
    exp_decay_mode=0,
    # Fraction of the last N legs that must be broken to block. P36 used 0.75,
    # i.e. three of four.
    exp_decay_thr=0.75,
    exp_decay_legs=4,
    # Close the LTF position when its own swing confirms, but ONLY if the swing
    # confirmed within this many hours of the entry. -1 (default) = off, which
    # keeps every existing book byte-identical. 0 = exit on the first FS of any
    # age, and that is much worse than doing nothing.
    #
    # Causal: fs_at_idx >= seg.end_idx (backend_check_wd_days) and the book only
    # enters at a B2/flip break which sits before seg.end_idx, so the exit only
    # reads a confirmation that already happened. No magnitude test -- the FS
    # size buckets invert (FS_TIME_GEOMETRY).
    #
    # Measured on champion multi. The useful band is 2-6h; 8h+ stops paying on
    # both eras, and 24h is worse than the control in sample.
    #   gap   IS net R   OOS net R   IS DD   OOS DD
    #   none  +239.12    +72.79      46.8    50.6
    #   2h    +245.52    +75.37      43.6    50.4
    #   4h    +289.98    +79.42      42.3    43.9
    #   6h    +303.36    +80.30      45.7    45.0
    #   8h    +264.59    +69.70      35.8    45.4
    #   12h   +257.00    +76.90      34.4    49.6
    #   24h   +209.38    +77.93      32.9    28.9
    #   any    +133.26    +57.90      32.9    28.9
    exit_fs_max_gap_h=-1.0,
    exp_fs_small_swing=0.0,   # exit at the swing FS when the swing is SMALL
                           # value = threshold on |end_px-start_px| / ATR(20). 0 = off.
                           # Gray mode (exp_fs_gray=1) keeps the slot occupied after
                           # such an exit so no replacement trade can enter.
    exp_fs_gray=False,
    exp_fs_entry_side="",   # DIRECTIONAL FS ENTRY on the LTF plane:
                           # "long"  = LONGS enter at the swing FS print, shorts at break
                           # "short" = SHORTS enter at the swing FS print, longs at break
                           # "both"  = both sides at FS (measured weaker than either one)
                           # "" (default) = off; every side enters at the break as before
    exp_fs_break_confirm=0.0,  # OWNER 2026-10-14: "when for FS, when the high of
                              # or long, when the high of FS will break, then we
                              # will enter. For short, when FS low will be broken,
                              # then we'll enter."
                              #
                              # Only moves the side exp_fs_entry_side already put
                              # on FS. An FS signal for an "up" swing waits until a
                              # LATER candle's high exceeds the FS candle's own
                              # high; an "down" swing waits until a later candle's
                              # low goes under the FS candle's own low. Until that
                              # break the trade is not taken at all.
                              #
                              # CAUSAL: reads candles_ltf[fs_at_idx].high/low and
                              # candles_ltf[j] for j > fs_at_idx. The FS candle has
                              # closed by definition (fs_at_idx >= seg.end_idx) and
                              # the entering bar j has closed before the break is
                              # known. The entry IS the bar the break happens on, so
                              # nothing here settles later than the decision bar.
                              # No swing field is read - only this swing's own
                              # fs_at_idx, which is settled at the FS print.
                              #
                              # 0.0 = off, which leaves every existing book
                              # byte-identical.
                              # 1.0 = EVERY FS entry waits for that break.
                              # 2.0 = only the entries whose FS candle COLOUR
                              # opposes the trade wait. Long + a red FS candle,
                              # or short + a green one. When the colour agrees
                              # the print itself is already the entry and is
                              # left alone. OWNER 2026-10-14: "we enter on fs if
                              # long and fs is green we enter directly if short
                              # fs is red we enter directly but if long and fs is
                              # red on the break of red high we enter and vice
                              # versa".
    exp_fs_trail_trigger=0.0,  # THE OTHER HALF OF THE SAME IDEA, and the form
                              # worth measuring: keep the entry ON the FS print
                              # and use the FS candle's extreme as a STOP
                              # trigger instead of as an entry delay.
                              #
                              #   1.0 = when the FS candle's extreme breaks,
                              #         ratchet the stop to breakeven
                              #   2.0 = ratchet it to the FS candle's own
                              #         opposite extreme (long -> the FS
                              #         candle's low, short -> its high)
                              #
                              # Why this is a different mechanism from
                              # exp_fs_break_confirm: that one PAYS for the
                              # confirmation with the entry and loses 13-17% of
                              # the book. This one keeps every trade and only
                              # tightens the stop on the trades whose FS
                              # confirmed, so it can bank the quality gain that
                              # was measurable in both eras without paying the
                              # size loss.
                              #
                              # CAUSAL: the ratchet is applied inside the bar
                              # loop, at bar j >= the trigger bar, and reads only
                              # candles_ltf up to j. The trigger condition (did
                              # the FS candle's extreme break) is settled at the
                              # trigger bar itself. swing_start_px, risk and the
                              # 3R target are all computed at the ENTRY and are
                              # untouched, so only the stop moves.
                              #
                              # 0.0 = off, which leaves every existing book
                              # byte-identical.
    exp_fs_confirm_bars=8,    # how many LTF bars after FS to wait for that break.
                              # 8 on 15m = 2h. Beyond it the FS is treated as not
                              # confirmed. exp_fs_break_confirm uses this as an
                              # entry delay; exp_fs_trail_trigger uses it as how
                              # long the stop stays loose.
    # Weekend entry blackout, in the candle's OWN timezone (UTC), not the
    # exchange-local one that exp_skip_utc_sat/sun use. This is the knob the
    # signal book runs on (fsent_sig_full, and the whole fsent_sig_* ladder).
    # Reads only candles_ltf[i]["date"] - the bar being evaluated for entry,
    # which has already closed. No swing is read at all, so there is nothing
    # here that can settle later than the decision bar: this filter cannot
    # read the future. Default 0 = off, which is what keeps the shipped
    # trade list byte-identical to every book measured before it existed.
    exp_skip_weekend=0,
    # Partial exit: take half off at a fixed R, let the rest run.
    # exp_partial_r = the R level at which the half is sold. 0.0 (default) = off.
    # The arm test reads only `best`, the running favourable extreme of the
    # trade so far, at the bar being processed - so the trigger is knowable in
    # real time and never reads a future high. The R that gets BOOKED is then
    # half the trigger plus half the final move, i.e. the position is genuinely
    # cut in half, not scored as if it were. Both halves are reported:
    # partial_exit_price on the trade, and r_multiple blended.
    # Note this is a position-size change, not an exit - the trade still runs to
    # its own SL/target. 205 books set it, but 192 of those set 0.0.
    exp_partial_r=0.0,
    # Bias-momentum floor: only enter when the HTF bias has momentum behind
    # it, measured as swing-over-swing leg magnitude on the 1h chain.
    # exp_bias_momentum_min = the minimum ratio of this leg to the previous
    # one. 0.0 (default) = off. Values used: 0.5 / 0.6 / 0.7 / 0.8.
    # Reads swings_htf[i]["seg"].start_px / end_px for the RATIO, and the
    # swing's own "breaks" list for WHEN the ratio became knowable. That is
    # the causal question this knob has to answer, and it is the reason
    # exp_bm_causal exists below: seg.start_px and end_px are only final once
    # the leg completes, which is AFTER the entry bar.
    #   exp_bm_causal = 0 (default): take the last break declared at or before
    #     the entry bar, by break time.
    #   exp_bm_causal = 1: additionally walk back until the swing that owns
    #     that break had CONFIRMED (confirmed_at_idx -> candle_ts_htf + 1h)
    #     by the entry instant, so only legs whose final label was already
    #     settled may be read. This is the setting that makes the knob
    #     defensible; the default keeps every historical pin reproducible.
    # This is the runner-up filter in KNOB_SWEEP.md (d_oos +57.21 at 0.9) and
    # it is one of the four the signal book cannot run without.
    exp_bias_momentum_min=0.0,
    exp_bm_causal=0,
    # Trail shaping - three knobs and a skip counter, all reading the trail
    # event stream the engine already builds. They gate or soften the RATCHET,
    # never the SL check, and the ratchet fires BEFORE the SL check on the same
    # bar (D3 ordering, 2026-09-20), so a gated ratchet simply leaves the stop
    # where it was for that event.
    #   exp_trail_delay_r  - do not ratchet until unrealised R reaches this
    #     (0.0 = never delay). Read from `best`, the running extreme.
    #   exp_trail_half     - ratchet halfway to the candidate instead of all
    #     the way (0 = full ratchet). Half is the setting that survived the
    #     equity study; it tightens less, so it gives back less when the move
    #     reverses.
    #   exp_trail_delay_prevbar - measure the delay from the PREVIOUS bar's
    #     best_f rather than the current one (0 = current bar). Fine path only.
    #   exp_trail_skip_n   - drop the first N trail events outright, so a new
    #     position's stop does not ratchet on the first few confirmations
    #     (0 = never skip). This is the one the signal book runs at 2.
    # Default 0 everywhere: the shipped ratchet is the full, immediate one, and
    # every gate is inert until a book asks for it.
    exp_trail_delay_r=0.0,
    exp_trail_half=0,
    exp_trail_delay_prevbar=0,
    exp_trail_skip_n=0,
):
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect as bs
    # exit_fs_max_gap_h needs the moment every HTF swing confirms, split by
    # direction so a trade only ever exits on the FS that confirms its OWN
    # swing. fs_at_idx indexes candles_htf, so the moment is
    # candles_htf[fs_at_idx].ts. Built unconditionally and cheap, but the
    # default -1 keeps every existing book byte-identical.
    fs_up_ts=[]; fs_dn_ts=[]
    for _s in swings_htf:
        _fi=int(_s.get("fs_at_idx",-1))
        if 0<=_fi<len(candles_htf):
            (fs_up_ts if _s.get("dir")=="up" else fs_dn_ts).append(int(candles_htf[_fi]["ts"]))
    fs_up_ts=sorted(set(fs_up_ts)); fs_dn_ts=sorted(set(fs_dn_ts))
    # Build HTF intervals for both flip and decisive
    _hfs = str(exp_htf_fs_entry or "")
    # Which HTF regime buckets open on the FS print instead of on the break.
    #
    # The old table tested _hfs_on and _hfs == "all" together, so "flip" set
    # _hfs_on true and then still fell through to the shipped value for all three
    # buckets. It measured identical to off because it WAS off: the mode named
    # for the bucket it moves moved nothing. Naming the set directly removes the
    # conjunction that made that possible - a mode either moves its buckets or
    # does not exist.
    #
    # "dec" is the selective arm that mirrors what the LTF side does with
    # exp_fs_entry_side: one bucket on FS, the rest on break. In "all" the three
    # buckets collapse into a single fs_both set and the book stops
    # distinguishing regimes at all, which is what killed that arm. "dec"
    # keeps flip and b2 on their breaks, so the regime distinction survives.
    _hfs_move = {"flip": {"flip"},
                 "dec": {"decisive"},
                 "b2": {"b2"},
                 "all": {"flip", "decisive", "b2"}}
    _move = _hfs_move.get(_hfs, set())
    _fb_flip = ("fs_both" if "flip" in _move else "flip")
    _fb_dec = ("fs_both" if "decisive" in _move else "decisive")
    _fb_b2 = ("fs_both" if "b2" in _move else "b2")
    htf_trades_flip = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break=_fb_flip, sl_mode="swing", rr_target=htf_rr, rr_target_short=htf_rr_short, trailing=htf_trail, breakeven_r=htf_breakeven_r, skip_first=True, fine=fine_ltf, cap_days=exp_cap_days, pivot_rule=pivot_rule)
    htf_trades_decisive = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break=_fb_dec, sl_mode="swing", rr_target=htf_rr, rr_target_short=htf_rr_short, trailing=htf_trail, breakeven_r=htf_breakeven_r, skip_first=True, fine=fine_ltf, cap_days=exp_cap_days, pivot_rule=pivot_rule)
    htf_trades_b2 = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break=_fb_b2, sl_mode="swing", rr_target=htf_rr, rr_target_short=htf_rr_short, trailing=htf_trail, breakeven_r=htf_breakeven_r, skip_first=True, fine=fine_ltf, cap_days=exp_cap_days, pivot_rule=pivot_rule)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    # C17 (2026-10-07): store the window END as a KNOWABLE instant, not as the
    # OPEN of the bar that detected the exit. exit_ts is the open of a fine (1m)
    # bar when fine data is supplied, else the HTF bar, so it settles one bar
    # later. The old gate shifted the end by the same offset the start needs
    # (`s` IS an HTF candle open and must wait for that candle to close), which
    # granted the LTF entry instant up to 59 extra minutes INSIDE a window that
    # had already closed: measured 4 entries in IS and 3 in OOS on this book,
    # all entered on a knowably-dead window. The end side now takes no shift at
    # all and the start keeps its own. Dead-window entries after the fix: 0.
    _wend_settle = 60 if fine_ltf else 3600
    def to_intervals(trades):
        # Window end: "exit" = HTF trade exit (SL/target/cap) â€” default, best R.
        # "r_touch" = first touch of 1.5R â€” tested 2026-09-08: +200.6R vs +331R (removed 88 trades avg +1.48R). Rejected.
        # "bias_flip" = next OPPOSITE-direction HTF entry (bias-based, not trade-based).
        # Tested 2026-09-08: 485t +368.6R vs exit 330t +331.1R (+37.5R) BUT added cohort t=1.21 (not significant),
        # 2026 worse (+55.1/DD7.3 vs +69.0/DD5.0), 2023 flat R at 85% more churn. net/DD 38.6 vs 34.0. NOT adopted.
        iv=[]
        last_htf_ts=int(candles_htf[-1]["ts"]) if candles_htf else 0
        for t in trades:
            if t["outcome"]=="open":
                # L1: still-open HTF window = active bias through end of slice.
                # Truncated causal slices always end with the governing window
                # open; dropping it zeroed every LTF gate (C10 L1).
                iv.append([int(t["entry_ts"]), last_htf_ts + 3600,
                           1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])])
                continue
            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if window_end=="r_touch" else int(t["exit_ts"]) + _wend_settle

            iv.append([int(t["entry_ts"]), wend, 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])])
        iv.sort(key=lambda x: x[0])
        if window_end=="bias_flip":
            last_ts=int(candles_htf[-1]["ts"])
            for i,w in enumerate(iv):
                nxt=None
                for j in range(i+1,len(iv)):
                    if iv[j][2]!=w[2]:
                        nxt=iv[j][0]; break
                w[1]=(nxt-1) if nxt is not None else max(w[1], last_ts)
        return [tuple(w) for w in iv]
    intervals_flip=to_intervals(htf_trades_flip)
    intervals_decisive=to_intervals(htf_trades_decisive)
    intervals_b2=to_intervals(htf_trades_b2)
    starts_flip=[s for s,_,_,_,_ in intervals_flip]
    starts_decisive=[s for s,_,_,_,_ in intervals_decisive]
    starts_b2=[s for s,_,_,_,_ in intervals_b2]
    # Regime series: chop 1h and atr% 15m mapped to LTF bar ts
    chop=_chop_series_1h(candles_htf, lb=14)
    atr_pct=_atr_pct_15m(candles_ltf)
    # Bias-momentum precompute. Built once per call, before the entry walk,
    # because the gate below bisects it per candidate signal. One tuple per
    # HTF break, not per swing: a swing can print several breaks and each one
    # is a separate moment the ratio became tradeable.
    #   _bm_mags   - |end_px - start_px| per HTF swing, the leg magnitudes
    #   _bm_breaks - (break_time[:19], ratio_vs_prev_leg, owner_confirmed_idx)
    #   _bm_times  - the first field only, for bisect
    # Built unconditionally rather than under `if exp_bias_momentum_min`, so
    # the cost does not depend on which book is running and the default path
    # stays byte-identical to a build with the block absent.
    _bm_mags=[]
    for _bm_s in swings_htf:
        _bm_seg=_bm_s.get("seg") or {}
        _bm_spx=float(_bm_seg.get("start_px",0) or 0)
        _bm_epx=float(_bm_seg.get("end_px",0) or 0)
        _bm_mags.append(abs(_bm_epx-_bm_spx))
    _bm_breaks=[]
    for _bmi in range(len(swings_htf)):
        if _bmi<1 or _bm_mags[_bmi-1]<=0: continue
        _bm_ratio=_bm_mags[_bmi]/_bm_mags[_bmi-1]
        for _bmb in (swings_htf[_bmi].get("breaks") or []):
            _bmbt=_bmb.get("time","")
            if _bmbt: _bm_breaks.append((_bmbt[:19],_bm_ratio,int(swings_htf[_bmi].get("confirmed_at_idx",-1))))
    _bm_breaks.sort(key=lambda z:z[0])
    _bm_times=[z[0] for z in _bm_breaks]
    candle_ts_ltf=[int(c["ts"]) for c in candles_ltf]
    candle_ts_htf=[int(c["ts"]) for c in candles_htf]
    # C14: regime gate at the ENTRY INSTANT (signal bar close = next candle open).
    # Only 1h candles that CLOSED by the entry instant may set the regime -
    # the running 1h candle's final chop is future data (up to 45 min lookahead).
    # Precompute chop per LTF bar from the last 1h bar CLOSED by ts+900.
    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]
    chop_per_ltf=[50.0]*len(candles_ltf)
    # v19: regime hysteresis state (exp_persist=7)
    _rg_s=None; _rg_c=0; PERSIST=exp_persist  # UNIFIED: was hardcoded 7 in v19
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
        if j>=0 and j < len(chop):
            chop_per_ltf[i]=chop[max(0,j)]
    # --- DECAY GATE (P36) ---------------------------------------------------
    # Of the last N CONFIRMED 15m legs in each direction, what fraction had
    # their start level broken? An up-leg defends its start low, a down-leg
    # defends its start high. High buying decay means recent buyers were
    # stopped out, which is a reason not to buy.
    #
    # This lived only in exp_decay_*.py as a post-hoc filter over trades the
    # engine had already booked. Written in as a real gate on 2026-10-02 so it
    # can be a registry book and so the entry-time decision is the one that is
    # recorded, rather than a trade being retroactively dropped.
    #
    # Strictly causal: a leg is read only once it is CONFIRMED at or before the
    # entry bar, and the break scan runs from that confirmation to the entry bar
    # and no further. Nothing here looks past the entry.
    #
    # Modes match the P36 grid's rule letters:
    #   0 off
    #   1 "both<-buying"  block when BUYING decay is high
    #   2 "both<-selling" block when SELLING decay is high
    #   3 "own side"      block a long on buying decay, a short on selling decay
    #   4 "crossed"       block a long on SELLING decay, a short on buying decay
    #   5-8 the ALLOW mirrors of 1-4. Kept because the grid measured them and
    #      every one of them was badly negative - that is evidence, and an
    #      evidence row should stay reproducible.
    def _decay_legs(swings, want_dir):
        # Own datetime import. The module's `import datetime as _dt` sits BELOW
        # this block, so borrowing that name here is a NameError. Kept local
        # rather than hoisting the module import so the ordering stays obvious.
        import datetime as _dec_dt
        out=[]
        for sw in swings:
            t=sw.get("confirmed_at_time","")
            if isinstance(t,str) and len(t)>=19:
                try: ts=int(_dec_dt.datetime.strptime(t[:19],"%Y-%m-%d %H:%M:%S").timestamp())
                except Exception: continue
            elif isinstance(t,(int,float)): ts=int(t)
            else: continue
            d=1 if sw.get("dir")=="up" else -1
            if d!=want_dir: continue
            seg=sw.get("seg",{}) or {}
            px=float(seg.get("start_px",0) or 0)
            if px<=0: continue
            out.append((ts,px))
        out.sort()
        return out
    _dec_up=_decay_legs(swings_ltf, 1)
    _dec_dn=_decay_legs(swings_ltf, -1)
    _dec_lo=[float(c["low"]) for c in candles_ltf]
    _dec_hi=[float(c["high"]) for c in candles_ltf]
    def _decay_frac(legs, series, is_low, t, n):
        vis=[L for L in legs if L[0]<=t]
        if not vis: return None
        rec=vis[-n:]
        j=bs.bisect_right(candle_ts_ltf,t)-1
        if j<0: return None
        br=0
        for cts,px in rec:
            a=bs.bisect_left(candle_ts_ltf,cts)
            b=j
            if b<a: continue
            seg=series[a:b+1]
            if not seg: continue
            if is_low:
                if min(seg)<px: br+=1
            else:
                if max(seg)>px: br+=1
        return br/float(len(rec))
    def _decay_blocks(mode, direction, t, thr, n):
        if mode==0: return False
        bu=_decay_frac(_dec_up,_dec_lo,True,t,n)
        se=_decay_frac(_dec_dn,_dec_hi,False,t,n)
        long_=direction>0
        if mode==1: hit=bu is not None and bu>=thr
        elif mode==2: hit=se is not None and se>=thr
        elif mode==3: hit=(bu is not None and bu>=thr) if long_ else (se is not None and se>=thr)
        elif mode==4: hit=(se is not None and se>=thr) if long_ else (bu is not None and bu>=thr)
        elif mode==5: hit=bu is not None and bu<thr
        elif mode==6: hit=se is not None and se<thr
        elif mode==7: hit=(bu is not None and bu<thr) if long_ else (se is not None and se<thr)
        elif mode==8: hit=(se is not None and se<thr) if long_ else (bu is not None and bu<thr)
        else: return False
        return bool(hit)
    # --- NEW MODE DATA: swing direction/magnitude per LTF bar ---
    import datetime as _dt
    def _sw_ts_dir_mag(swings):
        tss,ds,ms=[],[],[]
        for sw in swings:
            t=sw.get("confirmed_at_time","")
            if isinstance(t,str) and len(t)>=19:
                try: ts=int(_dt.datetime.strptime(t[:19],"%Y-%m-%d %H:%M:%S").timestamp())
                except: continue
            elif isinstance(t,(int,float)): ts=int(t)
            else: continue
            d=1 if sw.get("dir")=="up" else -1
            seg=sw.get("seg",{})
            sp=float(seg.get("start_px",0)); ep=float(seg.get("end_px",0))
            mag=abs(ep-sp)/sp if sp>0 else 0
            tss.append(ts); ds.append(d); ms.append(mag)
        return tss,ds,ms
    htf_sw_ts,htf_sw_dir,htf_sw_mag=_sw_ts_dir_mag(swings_htf)
    ltf_sw_ts,ltf_sw_dir,ltf_sw_mag=_sw_ts_dir_mag(swings_ltf)
    htf_dir_per_ltf=[0]*len(candles_ltf)
    htf_mag_per_ltf=[0.0]*len(candles_ltf)
    ltf_dir_per_ltf=[0]*len(candles_ltf)
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(htf_sw_ts, ts+900)-1
        if j>=0: htf_dir_per_ltf[i]=htf_sw_dir[j]; htf_mag_per_ltf[i]=htf_sw_mag[j]
        j2=bs.bisect_right(ltf_sw_ts, ts+900)-1
        if j2>=0: ltf_dir_per_ltf[i]=ltf_sw_dir[j2]
    # Rolling percentile of chop (for dynamic_chop mode)
    chop_pct_per_ltf=[50.0]*len(candles_ltf)
    _lookback=672
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
        if j>=0:
            _s=max(0,j-_lookback); _w=chop[_s:j+1]
            if _w:
                _cur=chop[j]; _below=sum(1 for c in _w if c<_cur)
                chop_pct_per_ltf[i]=_below/len(_w)*100.0
    # --- Session per LTF bar (Idea H): 0=Asia(0-7), 1=London(7-14), 2=NY(14-21), 3=Night(21-24) ---
    session_per_ltf=[0]*len(candles_ltf)
    import datetime as _dts
    for i,ts in enumerate(candle_ts_ltf):
        _hr=_dts.datetime.utcfromtimestamp(ts).hour
        if _hr<7: session_per_ltf[i]=0      # Asia: rangeâ†’B2
        elif _hr<14: session_per_ltf[i]=1   # London: trendâ†’FLIP
        elif _hr<21: session_per_ltf[i]=2   # NY: trendâ†’FLIP
        else: session_per_ltf[i]=3           # Night: rangeâ†’B2
    # --- Rolling entropy of 1h returns (Idea L) --- computed per HTF bar, mapped to LTF
    import math
    _ret_1h=[]
    for i in range(1,len(candles_htf)):
        p0=float(candles_htf[i-1]["close"]); p1=float(candles_htf[i]["close"])
        _ret_1h.append((p1-p0)/p0 if p0>0 else 0.0)
    _ent_lb=96  # 4 days â€” compute per HTF bar (not per LTF bar) for speed
    _ent_htf=[50.0]*len(candles_htf)
    _nhtf=len(candles_htf)
    for i in range(_ent_lb, len(_ret_1h)):
        _wins=_ret_1h[i-_ent_lb:i]
        if not _wins: continue
        _nbins=min(15,max(5,int(math.sqrt(len(_wins)))))
        _mn=min(_wins); _mx=max(_wins); _rng=_mx-_mn
        if _rng<=0: continue
        _bins=[0]*_nbins
        for v in _wins:
            bi=min(int((v-_mn)/_rng*_nbins), _nbins-1)
            _bins[bi]+=1
        _tot=float(len(_wins)); _ent=0.0
        for c in _bins:
            if c>0:
                p=c/_tot; _ent -= p*math.log2(p)
        _max_ent=math.log2(_nbins) if _nbins>1 else 1.0
        _ei=i+1
        if _ei<_nhtf:
            _ent_htf[_ei]=(_ent/_max_ent)*100.0 if _max_ent>0 else 50.0
    entropy_per_ltf=[50.0]*len(candles_ltf)
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
        if j>=0 and j<len(_ent_htf):
            entropy_per_ltf[i]=_ent_htf[j]
    # --- Rolling fractal dimension of 1h candles (Idea K) --- computed per HTF bar, mapped
    fd_per_ltf=[50.0]*len(candles_ltf)
    _fd_lb=48  # 2 days â€” reduced for speed
    _fd_htf=[50.0]*len(candles_htf)
    for i in range(_fd_lb, len(candles_htf)):
        _cl=[float(candles_htf[k]["close"]) for k in range(i-_fd_lb, i+1)]
        if len(_cl)<4: continue
        _mn=min(_cl); _mx=max(_cl); _rng2=_mx-_mn
        if _rng2<=0: continue
        _ds=[]; _ps=[]
        for _step in (1,2,4):
            _sum=0.0; _cnt=0
            for _k in range(_step, len(_cl)):
                _sum+=abs(_cl[_k]-_cl[_k-_step]); _cnt+=1
            if _cnt>0 and _rng2>0:
                _ds.append(math.log(_sum/_cnt/_rng2+1e-12))
                _ps.append(math.log(1.0/_step))
        if len(_ds)>=2:
            _ss=sum(_ds); _sps=sum(_ps)
            _sps2=sum(p*p for p in _ps); _ssp=sum(d*p for d,p in zip(_ds,_ps))
            _den=len(_ds)*_sps2-_sps*_sps
            if abs(_den)>1e-15:
                _slope=(len(_ds)*_ssp-_ss*_sps)/_den
                fd=1.0-abs(_slope)
                _fd_htf[i]=max(0.0,min(100.0,(1.0-fd)*100.0))
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
        if j>=0 and j<len(_fd_htf):
            fd_per_ltf[i]=_fd_htf[j]
    # --- HMM regime (Idea A): train prefix, forward-filter full series ---
    hmm_per_ltf=[50.0]*len(candles_ltf)
    if mode in ("hmm","hmm_inv"):
        _hmm_htf=_hmm_regime_1h(candles_htf)
        for i,ts in enumerate(candle_ts_ltf):
            j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
            if j>=0 and j<len(_hmm_htf):
                hmm_per_ltf[i]=_hmm_htf[j]
    # --- GARCH regime (Idea F): predicted-vol range score, train-frozen params ---
    garch_per_ltf=[50.0]*len(candles_ltf)
    if mode in ("garch","garch_inv"):
        _garch_htf=_garch_regime_1h(candles_htf)
        for i,ts in enumerate(candle_ts_ltf):
            j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
            if j>=0 and j<len(_garch_htf):
                garch_per_ltf[i]=_garch_htf[j]
    # LTF signals (decisive)
    from src.btc.btc_engine import CandleStore
    ltf_store = CandleStore(candles_ltf)
    _lbreak="decisive"
    if exp_fs_entry_side:
        # DIRECTIONAL FS ENTRY. On the chosen side(s) the LTF entry waits for
        # the swing own FS print instead of firing on the decisive break; the
        # other side falls through unchanged. Only the TRIGGER differs - an
        # "up" swing still makes a long. Causal: fs_at_idx is at or after the
        # swing end bar, so that bar has closed before the print is used.
        _lbreak="fs_"+exp_fs_entry_side
    ltf_sigs=_collect_signals(swings_ltf, _lbreak, skip_first=True, selection="stream", candles=candles_ltf, pivot_rule=pivot_rule)
    # ── exp_fs_break_confirm: wait for the FS candle's own extreme to break ───
    # swing_index -> the bar the FS trade may actually be taken on, or -1 if the
    # break never arrives inside exp_fs_confirm_bars. Built only when the knob is
    # on, so the default path is untouched.
    _fs_confirm_at={}
    if exp_fs_break_confirm or exp_fs_trail_trigger:
        _cap=max(1,int(exp_fs_confirm_bars))
        for _s in swings_ltf:
            _fi=int(_s.get("fs_at_idx",-1))
            _si=int(_s.get("swing_index",-1))
            if _si<0 or not (0<=_fi<len(candles_ltf)): continue
            _up=(_s.get("dir")=="up")
            _ref=float(candles_ltf[_fi]["high"]) if _up else float(candles_ltf[_fi]["low"])
            _hit=-1
            for _j in range(_fi+1, min(_fi+1+_cap, len(candles_ltf))):
                _c=candles_ltf[_j]
                if (float(_c["high"])>_ref) if _up else (float(_c["low"])<_ref):
                    _hit=_j; break
            # Does the FS candle's colour OPPOSE the trade this swing would take?
            # An FS signal's direction IS the swing direction: an "up" swing is a
            # long, a "down" swing is a short. Long + a red FS candle opposes;
            # short + a green FS candle opposes. Only then is the entry delayed.
            _green=float(candles_ltf[_fi]["close"])>float(candles_ltf[_fi]["open"])
            _op=(not _green) if _up else _green
            _fs_confirm_at[_si]=(_hit,_op)
    filtered=[]
    # UNKNOWN MODE IS A HARD ERROR, checked once here rather than per bar.
    #
    # This chain used to end in `else: use="flip"`, and `use="flip"` was also
    # assigned before the chain started. A mode string that matched nothing -
    # a typo in a registry entry, a renamed branch, an experiment passing a mode
    # that was never implemented - therefore fell through silently and traded
    # as plain flip. Measured on fsent_champ_long: mode="GARBAGE_MODE_xyz"
    # returned n=495 / +462.58R, byte-identical to the fallback, with no error
    # and no log line. A book could silently stop being the book its entry
    # claims it is and nothing in the harness would notice.
    #
    # The chain is also reached only from inside `for sig in ltf_sigs:`, so a
    # book with zero LTF signals would never have raised even with the guard
    # inline here. Validating once, above the loop, makes the failure depend on
    # the config alone.
    #
    # Verified before raising: all 94 dict books in the registry carry a mode
    # that is in this set, and no caller outside the registry passes one that
    # is not. HTF_MODES is derived from the branches below so a new mode cannot
    # be added without being listed here.
    if mode not in HTF_MODES:
        raise ValueError(
            "unknown HTF regime mode %r. Valid modes: %s"
            % (mode, ", ".join(sorted(HTF_MODES)))
        )
    # Sample buffer for ext_stop_pct. Built fresh per run so one run's extensions
    # never leak into the next, and only ever appended to from inside this walk.
    _EXT_SAMPLE = []
    ext_stop_r_default = ext_stop_r
    for sig in ltf_sigs:
        bar_time=sig["bar"]  # datetime string
        bar=ltf_store.pos(bar_time)  # position via timestamp lookup
        if bar < 0 or bar >= len(candles_ltf): continue
        bar_ts=candle_ts_ltf[bar]
        # Move an FS entry from the FS print to the bar where the FS candle's own
        # extreme actually breaks. Dropped entirely if it never breaks inside the
        # cap. swing_start_px is left exactly as _collect_signals set it (seg
        # start_px, the same level every other FS signal uses) so the ONLY thing
        # that changes is WHEN we enter - not what the stop is anchored to.
        if exp_fs_break_confirm and sig.get("kind")=="FS":
            _ent=_fs_confirm_at.get(int(sig.get("swing_no",-1)))
            if _ent is None: continue
            _hit,_op=_ent
            # 2.0+ = only delay when the FS candle's colour opposes the trade.
            # Colour agreeing means the FS bar already ran in our direction, so
            # the print itself is the entry and nothing is delayed.
            if exp_fs_break_confirm<2.0 or _op:
                if _hit<0: continue
                bar=_hit
                bar_ts=candle_ts_ltf[bar]
        # P36 decay gate, evaluated at the entry bar on legs confirmed by then.
        if _decay_blocks(exp_decay_mode, sig["dir"], bar_ts, exp_decay_thr, exp_decay_legs):
            continue
        # regime at bar
        ch=chop_per_ltf[bar] if bar < len(chop_per_ltf) else 50.0
        atrp=atr_pct[bar] if bar < len(atr_pct) else 0.5
        # decide which HTF interval set to use
        # Every branch below is covered by HTF_MODES, which is enforced by the
        # guard above `for sig in ltf_sigs:`. Reaching the final `else` is
        # therefore a bug in this chain, not a config the caller may pass, so it
        # raises instead of quietly trading as flip.
        use=None
        if mode=="chop":
            use="decisive" if ch > chop_thresh else "flip"
        elif mode=="atr_low":
            use="decisive" if atrp < atr_low_thresh else "flip"
        elif mode=="atr_high":
            use="decisive" if atrp > atr_high_thresh else "flip"
        elif mode=="chop_or_atr_low":
            use="decisive" if (ch > chop_thresh or atrp < atr_low_thresh) else "flip"
        elif mode=="chop_and_atr_low":
            use="decisive" if (ch > chop_thresh and atrp < atr_low_thresh) else "flip"
        elif mode=="b2_vs_flip_chop":
            # HTF B2 vs Flip conditional: use B2 when chop high else Flip
            use="b2" if ch > chop_thresh else "flip"
        elif mode=="decisive_vs_flip_chop":
            use="decisive" if ch > chop_thresh else "flip"
        elif mode=="htf_dir":
            use="b2" if htf_dir_per_ltf[bar]==1 else "flip"
        elif mode=="htf_mag":
            use="b2" if htf_mag_per_ltf[bar]>(chop_thresh/10000.0) else "flip"
        elif mode=="htf_mag_inv":
            use="flip" if htf_mag_per_ltf[bar]>(chop_thresh/10000.0) else "b2"
        elif mode=="flip_quality":
            use="b2" if ch > chop_thresh else "flip"
            if use=="flip" and htf_mag_per_ltf[bar]<(chop_thresh/10000.0):
                continue
        elif mode=="ltf_dir":
            use="b2" if ltf_dir_per_ltf[bar]==1 else "flip"
        elif mode=="dynamic_chop":
            use="b2" if chop_pct_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="union":
            use="union"
        elif mode=="session":
            # Idea H: Asia(0,3)=rangeâ†’B2, London/NY(1,2)=trendâ†’flip
            _s=session_per_ltf[bar]
            use="b2" if _s in (0,3) else "flip"
        elif mode=="session_flip":
            # Inverted: Asiaâ†’flip, London/NYâ†’B2
            _s=session_per_ltf[bar]
            use="flip" if _s in (0,3) else "b2"
        elif mode=="entropy":
            # Idea L: low entropy=rangeâ†’B2, high entropy=trendâ†’flip
            use="b2" if entropy_per_ltf[bar]<chop_thresh else "flip"
        elif mode=="entropy_inv":
            use="flip" if entropy_per_ltf[bar]<chop_thresh else "b2"
        elif mode=="fd":
            # Idea K: low FD=trendâ†’flip, high FD=rangeâ†’B2
            use="b2" if fd_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="fd_inv":
            use="flip" if fd_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="hmm":
            # Idea A: P(range)*100 > chop_thresh â†’ range â†’ B2 else flip
            use="b2" if hmm_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="hmm_inv":
            use="flip" if hmm_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="garch":
            # Idea F: low predicted vol (high range-score) â†’ B2, high vol â†’ flip
            use="b2" if garch_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="garch_inv":
            use="flip" if garch_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="soft_chop":
            # Idea D: soft band around chop_thresh â€” uncertain zone uses both windows
            _hw=max(float(soft_width),0.0)
            if ch>chop_thresh+_hw: use="b2"
            elif ch<chop_thresh-_hw: use="flip"
            else: use="decisive"
        elif mode=="soft_atr":
            # Idea D soft on production atr_high path; band falls back to chop
            _hw=max(float(soft_width),0.0)
            if atrp>atr_high_thresh+_hw: use="decisive"
            elif atrp<atr_high_thresh-_hw: use="flip"
            else: use="decisive" if ch>chop_thresh else "flip"
        elif mode=="soft_ensemble":
            # Idea D: blend chop + ATR% + entropy + FD into one range score (0-100),
            # soft-route: highâ†’B2, lowâ†’FLIP, bandâ†’decisive (both).
            _hw=max(float(soft_width),1e-6)
            def _ramp(x,thr,half=1.0):
                if half<=0: return 1.0 if x>thr else 0.0
                if x>=thr+half: return 1.0
                if x<=thr-half: return 0.0
                return 0.5+0.5*(x-thr)/half
            _p=0.25*(
                _ramp(ch,chop_thresh,_hw)
                + _ramp(atrp*100.0,atr_high_thresh*100.0,_hw)
                + _ramp(100.0-entropy_per_ltf[bar],50.0,_hw)
                + _ramp(fd_per_ltf[bar],50.0,_hw)
            )*100.0
            if _p>50.0+_hw: use="b2"
            elif _p<50.0-_hw: use="flip"
            else: use="decisive"
        else:
            raise AssertionError(
                "HTF_MODES lists %r as valid but the regime chain does not route "
                "it - add the elif above this line" % (mode,)
            )
        # v19: hold the old regime for PERSIST consecutive disagreements.
        if PERSIST>0:
            if _rg_s is None: _rg_s=use
            if use!=_rg_s:
                _rg_c+=1
                if _rg_c>=PERSIST: _rg_s=use; _rg_c=0
            else: _rg_c=0
            use=_rg_s
        # pick intervals
        if use=="union":
            # Idea 2: check BOTH B2 and FLIP intervals
            _union_matched=False
            for _iv,_st in [(intervals_b2,starts_b2),(intervals_flip,starts_flip)]:
                if not _iv: continue
                _idx=bs.bisect_right(_st,bar_ts)-1
                if _idx<0: continue
                _s,_e,_d,_pe,_psl=_iv[_idx]
                if (_s+2700<bar_ts+900<_e) and sig["dir"]==_d:
                    _union_matched=True
                    # keep _pe,_psl for extension check
                    pe=_pe; psl=_psl; d=_d
                    break
            if not _union_matched: continue
            # union unpacks into _s/_e and never binds s/e, so capture here,
            # outside the union-gate anchor block, for the reporting fields.
            if _union_matched: win_start=_s; win_end=_e
            if ext_stop_r > 0 or ext_stop_pct > 0:
                hrisk = abs(pe - psl)
                if hrisk > 0:
                    ext = (float(candles_ltf[bar]["close"]) - pe) * d / hrisk
                    _EXT_SAMPLE.append(ext)
                    _LVL = _ext_level(hrisk, ext_stop_pct, _EXT_SAMPLE, ext_stop_r_default)
                    if _LVL > 0 and ext > _LVL: continue
            filtered.append((sig,use,win_start,win_end))
            continue
        elif use=="flip":
            intervals=intervals_flip; starts=starts_flip
        elif use=="b2":
            intervals=intervals_b2; starts=starts_b2
        else:
            intervals=intervals_decisive; starts=starts_decisive
        if not intervals:
            continue
        idx=bs.bisect_right(starts, bar_ts)-1
        if idx<0: continue
        s,e,d,pe,psl=intervals[idx]
        win_start=s; win_end=e   # report-only; see the note at init
        # C15: the window START is knowable from the flip candle CLOSE
        # (entry_ts + 3600); the LTF entry instant is bar_ts + 900. Gate in
        # knowable-instant space.
        # C17: the window END is stored knowable (see _wend_settle), so
        # the second side takes no shift - it was reusing the start's offset
        # and admitting entries on windows that were already dead.
        #
        # WINDOW FLOOR. Was a hardcoded 45-minute wait and never a parameter,
        # so it was the one axis of the HTF window nobody could sweep. It answers
        # "how long after a window opens must you wait before trading it", which is
        # a different question from exp_htf_fs_entry ("does the window open at the
        # FS print or at the break"). Changing the trigger moves s; this moves the
        # wait after s. Two axes, and only one had been tested.
        #
        # mode "fixed"  - the original behaviour, s + exp_window_floor_s.
        # mode "fs"     - the floor is the FS print of the swing that governs this
        #   window, so a window is tradeable from the moment its own structure
        #   confirmed rather than 45 minutes after the break that opened it.
        # mode "max"    - whichever is later. Strictly tighter than either alone,
        #   so it cannot admit anything the other two would reject.
        _floor = s + exp_window_floor_s
        if exp_window_floor_mode in ("fs", "max"):
            _arr = fs_up_ts if d > 0 else fs_dn_ts
            if _arr:
                _i = bs.bisect_right(_arr, s) - 1
                if _i >= 0:
                    _fs_t = int(_arr[_i])
                    _floor = _fs_t if exp_window_floor_mode == "fs" else max(_floor, _fs_t)
        if not (_floor < bar_ts+900 < e): continue
        if sig["dir"] != d: continue
        if ext_stop_r > 0 or ext_stop_pct > 0:
            hrisk = abs(pe - psl)
            if hrisk > 0:
                ext = (float(candles_ltf[bar]["close"]) - pe) * d / hrisk
                _EXT_SAMPLE.append(ext)
                _LVL = _ext_level(hrisk, ext_stop_pct, _EXT_SAMPLE, ext_stop_r_default)
                if _LVL > 0 and ext > _LVL: continue
        filtered.append((sig, use, win_start, win_end))
    # Now simulate LTF with filtered signals (same as v1_15m LTF walk, swing trail)
    n=len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
                "ltf_trades": [], "intervals": intervals_flip}
    candle_ts=candle_ts_ltf
    # ATR for SL buffer
    tr_l=[0.0]*n
    for _i in range(n):
        _c=candles_ltf[_i]
        if _i==0: tr_l[_i]=float(_c["high"])-float(_c["low"])
        else:
            _pc=float(candles_ltf[_i-1]["close"])
            tr_l[_i]=max(float(_c["high"])-float(_c["low"]), abs(float(_c["high"])-_pc), abs(float(_c["low"])-_pc))
    atr15=[0.0]*n
    for _i in range(n):
        _lo=max(0,_i-13)
        atr15[_i]=sum(tr_l[_lo:_i+1])/(_i-_lo+1)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    ltf_trades=[]
    _gray_until=""   # set only by an exp_fs_gray exit; empty means "slot is free"
    # v19 causal SL: running extreme since the last CONFIRMED swing.
    # A swing's confirmed_at_idx is the instant the swing becomes knowable, so at
    # bar i the value below depends only on candles up to i. Ported verbatim from
    # backtest/tests/_w1h_gray_tmp.py:995-1021, the harness copy that produced
    # the 484fe2a numbers. When a swing confirms, the running extreme RESETS to
    # that swing's seg end, then tracks from there.
    _csl=[0.0]*n; _csh=[0.0]*n
    if exp_causal_sl:
        _conf_evs=[]
        for _s in swings_ltf:
            _ca=_s.get("confirmed_at_idx")
            if _ca is not None and int(_ca)>=0:
                _e=_s.get("seg",{}).get("end_idx",-1)
                if _e is not None and int(_e)>=0:
                    _conf_evs.append((int(_ca),int(_e)))
        _conf_evs.sort()
        _cref=0; _cei=0
        _clo=float(candles_ltf[0]["low"]); _chi=float(candles_ltf[0]["high"])
        for _ci in range(n):
            while _cei<len(_conf_evs) and _conf_evs[_cei][0]<=_ci:
                # +1: the forming swing starts on the bar AFTER the finished leg.
                # Resetting to seg end put the running extreme on the low of a
                # candle belonging to a leg that had already completed, which is
                # the retroactive pivot one swing earlier - not a causal value.
                # Checked: across all 2900 swings, seg_end + 1 is never after
                # confirmed_at_idx, so this cannot read a future bar.
                _cref=_conf_evs[_cei][1]+1; _cei+=1
                if _cref<=_ci and _cref<n:
                    # Scan _cref.._ci, not just _cref. The old code took only the
                    # single candle at _cref, so every bar between the swing end
                    # and the confirm instant was skipped - and the lowest of
                    # those is usually the one that matters. On 30 Nov 2023 the
                    # reset fired at 22:15 pointing at 19:45, and the 21:15 low
                    # in between was never read; the engine used the 22:45 low
                    # instead, 118 points higher. That alone turned a +18.61R
                    # winner into a -1.00R stop-out.
                    _clo=min(float(candles_ltf[k]["low"]) for k in range(_cref,_ci+1))
                    _chi=max(float(candles_ltf[k]["high"]) for k in range(_cref,_ci+1))
            _cl=float(candles_ltf[_ci]["low"]); _ch2=float(candles_ltf[_ci]["high"])
            if _cl<_clo: _clo=_cl
            if _ch2>_chi: _chi=_ch2
            _csl[_ci]=_clo; _csh[_ci]=_chi
    # v19: no position limit - busy_until stays empty and is never armed
    # UNIFIED: v19 deleted this initialisation along with the gate but kept
    # the assignment at the end of the loop, so restoring the gate without
    # this line raises UnboundLocalError on the first entry. The line itself is
    # kept VERBATIM from v18:572 because test_experiments_craze.py anchors on it.
    busy_until=""  # datetime string — timestamp-based, not index
    # UNIFIED: booked-trade intervals backing exp_max_concurrent. Stays empty at
    # N=0 so the gate never fires and the shipped pins are untouched.
    _open_ivs=[]  # (entry_ts:int, exit_ts:int) for trades booked so far
    # UNIFIED: same intervals but carrying direction, backing exp_no_opposite.
    # Kept separate from _open_ivs rather than widening that one because
    # _open_ivs' 2-tuple shape is read by the exp_max_concurrent gate and by
    # harnesses that unpack it positionally; adding a third element would break
    # both for no benefit. Filled under the same "never populate when the knob is
    # off" rule so the shipped path allocates nothing extra per entry.
    _open_dirs=[]  # (entry_ts:int, exit_ts:int, dir:int)
    last_loss_bar=-999999
    consecutive_losses=0
    halt_skip_next=False  # True after Nth loss: skip NEXT entry, then reset
    # Weekday helper for exp_skip_weekend, memoised per calendar DAY: the walk
    # re-evaluates the same date once per LTF bar, and strptime/date() per bar
    # is pure overhead on a 4-year replay. The cache is keyed on the date
    # substring only, so it holds one int per distinct day and cannot grow per
    # bar. A local function rather than a module-level one because the cache is
    # per-simulate() call and must not be shared across books.
    _wd_cache={}
    def _is_weekend(dstr):
        _d = dstr[:10]
        _w = _wd_cache.get(_d)
        if _w is None:
            import datetime as _dt
            _w = _dt.date(int(_d[:4]), int(_d[5:7]), int(_d[8:10])).weekday()
            _wd_cache[_d] = _w
        return _w
    # Window bounds for the audit trail, carried on every booked trade.
    # Captured into their own names rather than read from s/e at the append
    # site: the union branch (mode=="union") unpacks into _s/_e and only
    # carries pe, psl and d forward, so s and e still hold the PREVIOUS bar's
    # window there. Reading s/e directly would publish a stale window on every
    # union book. Nothing reads these names for control flow - they are
    # reporting only, and they must not be able to move a number.
    win_start=0; win_end=0
    from src.btc.btc_engine import _trail_events as _te
    import bisect
    # win_start/win_end ride along with the signal: the window bounds are bound in the
    # filtering loop above, not here, so they cannot be read from s/e at booking time.
    for sig, use, win_start, win_end in filtered:
        bar_time=sig["bar"]  # datetime string
        i=ltf_store.pos(bar_time)  # position via timestamp lookup
        if i < 0 or i>=n-1: continue
        # UNIFIED: the position gate, restored from v18:582 under a parameter.
        # max_positions=1 reproduces v18 exactly; 0 is v19 (unlimited).
        if max_positions > 0 and busy_until and bar_time <= busy_until: continue
        # UNIFIED: simultaneous-open cap. Distinct from the serial gate above,
        # which knows only when the last booked trade closed. Counts trades
        # already booked whose [entry_ts, exit_ts] contains this entry bar.
        # Causal: every exit_ts in _open_ivs was settled before this entry was
        # considered, since trades are booked in stream order.
        if exp_max_concurrent > 0 and _open_ivs:
            _bt=int(candles_ltf[i]["ts"])
            _nopen=sum(1 for (_a,_b) in _open_ivs if _a <= _bt <= _b)
            if _nopen >= exp_max_concurrent: continue
        # UNIFIED: opposite-direction lock. A new entry is refused only if a trade
        # in the OTHER direction is open right now; trades in the same direction
        # do not block it. Placed after the position gates because those are
        # stronger and cheaper, and before the signal's direction is read below
        # only in the sense that it uses sig["dir"] directly.
        if exp_no_opposite and _open_dirs:
            _bt2=int(candles_ltf[i]["ts"])
            _d2=int(sig["dir"])
            if any(_dd != _d2 and _a <= _bt2 <= _b for (_a,_b,_dd) in _open_dirs):
                continue
        # CRAZE ANCHOR: the line above is the v18 gate restored verbatim, so
        # test_experiments_craze.py's t10 anchor (which rewrites the bare
        # `if busy_until and bar_time <= busy_until: continue` form) does not
        # match. That anchor exists to inject exp_mltf gating. It is the ONE
        # anchor of 62 that Phase 2 had to touch, and it is touched here rather
        # than in the harness so the harness stays engine-agnostic.
        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue
        # Streak halt (causal): after N consecutive losses BOOKED, skip NEXT entry
        if halt_skip_next:
            halt_skip_next=False
            consecutive_losses=0
            continue
        if exp_skip_weekend and _is_weekend(candles_ltf[i]["date"]) >= 5:
            continue
        if exp_bias_momentum_min > 0 and _bm_breaks:
            _bm_idx = bs.bisect_right(_bm_times, sig["bar"][:19]) - 1
            if exp_bm_causal:
                _bm_ets = candle_ts_ltf[i] + 900  # entry instant = signal bar close
                while _bm_idx >= 0:
                    _bm_c = _bm_breaks[_bm_idx][2]
                    if 0 <= _bm_c < len(candle_ts_htf) and candle_ts_htf[_bm_c] + 3600 <= _bm_ets:
                        break
                    _bm_idx -= 1  # owner unconfirmed at entry: walk to last DECLARED break
            if _bm_idx >= 0 and _bm_breaks[_bm_idx][1] < exp_bias_momentum_min:
                continue
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        # SL pivot. RETRO = the swing's true origin (lookahead). CAUSAL = the running
        # extreme as of bar i (knowable in real time).
        if exp_causal_sl:
            # _ci must exist before it is read. Defining it after this line
            # compiles fine and never runs when exp_causal_sl=0, which is why it
            # reached a commit.
            _ci = i - 1 if (exp_ltf_no_entry and i > 0) else i
            sl_pivot = _csl[_ci] if direction==1 else _csh[_ci]
        else:
            sl_pivot = sig["swing_start_px"]
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl>=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
            # UNIFIED: minimum stop distance, exp_min_sl_pct as a fraction of
            # entry price. Kept as its OWN line so the shipped guard above stays
            # byte-identical: test_experiments_craze.py anchors on that exact
            # line and asserts it appears twice, then injects the D3 risk-width
            # gate after it. Folding the two together broke that contract and the
            # harness caught it. The two are additive - both must pass.
            if exp_min_sl_pct>0 and risk<exp_min_sl_pct*entry: continue
            target=entry+3.0*risk
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl<=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
            # UNIFIED: same minimum stop distance as the long branch above, and
            # the same reason it is a separate line - the harness anchor counts
            # the `risk<0.0005*entry` line twice across the function.
            if exp_min_sl_pct>0 and risk<exp_min_sl_pct*entry: continue
            target=entry-3.0*risk
        sl0=sl; sl_cur=sl; best=entry
        # ── exp_fs_trail_trigger: ratchet the STOP, never delay the ENTRY ──────
        # Computed once per trade. The trigger bar is where the FS candle's own
        # extreme broke, which _fs_confirm_at already resolved at a bar no later
        # than itself; the level is applied inside the bar loop only for bars at
        # or after it, so nothing here is knowable earlier than it is used.
        _fs_trig_bar=-1; _fs_trig_px=0.0; _fs_trig_ts=None
        if exp_fs_trail_trigger and sig.get("kind")=="FS":
            _sn=int(sig.get("swing_no",-1))
            _ent=_fs_confirm_at.get(_sn)
            if _ent is not None and _ent[0]>=0:
                for _s in swings_ltf:
                    if int(_s.get("swing_index",-1))!=_sn: continue
                    _fi=int(_s.get("fs_at_idx",-1))
                    if not (0<=_fi<len(candles_ltf)): break
                    _fs_trig_bar=_ent[0]
                    _fs_trig_ts=int(candles_ltf[_fs_trig_bar]["ts"])
                    _fs_trig_px=(float(candles_ltf[_fi]["low"]) if direction==1
                                 else float(candles_ltf[_fi]["high"])) if exp_fs_trail_trigger>=2.0 else entry
                    break
        _partial_taken=False; _partial_r=0.0
        _trail_skip_rem=exp_trail_skip_n
        # Trail events: timestamp-based (confirmed_at_time â†’ position via store)
        want_dir = "up" if direction == 1 else "down"
        events = []
        for s in swings_ltf:
            if s.get("dir") != want_dir:
                continue
            ct = s.get("confirmed_at_time", "")
            if not ct:
                continue
            cidx = ltf_store.pos(ct)
            if cidx >= 0:
                events.append((cidx, float(s["seg"]["start_px"])))
        events.sort(key=lambda x: x[0])
        ev_idx=-1
        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None
        for j in range(i+1, n if not fine_ltf else i+1):
            c=candles_ltf[j]
            hi=float(c["high"]); lo=float(c["low"])
            if direction==1:
                if hi>best: best=hi
            else:
                if lo<best: best=lo
            if exp_partial_r>0 and not _partial_taken and risk>0:
                _cur_r=(best-entry)*direction/risk
                if _cur_r>=exp_partial_r:
                    _partial_taken=True; _partial_r=exp_partial_r
            # FS-extreme stop trigger. Only ever TIGHTENS, and only to a level on
            # the losing side of the price running at bar j, so it cannot arm a
            # stop that the same bar immediately takes out. risk, sl0 and the 3R
            # target were all fixed at entry and are not recomputed.
            if _fs_trig_bar>=0 and j>=_fs_trig_bar:
                _ft=(_fs_trig_px-sl_buf_atr*atr15[j]) if (direction==1 and sl_buf_atr>0) else _fs_trig_px
                if direction!=1 and sl_buf_atr>0:
                    _ft=_fs_trig_px+sl_buf_atr*atr15[j]
                if direction==1:
                    if _ft>sl_cur and _ft<best: sl_cur=_ft
                else:
                    if _ft<sl_cur and _ft>best: sl_cur=_ft
            if direction==1:
                # D3 ordering fix 2026-09-20: the ratchet applies BEFORE the SL
                # check â€” the stop is armed the instant the swing confirms (bar
                # open), so this same bar is enforced against the new level.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    _tr_ok=True
                    if _trail_skip_rem>0:
                        _trail_skip_rem-=1; _tr_ok=False
                    if _tr_ok and exp_trail_delay_r>0 and risk>0:
                        if ((best-entry)*direction/risk) < exp_trail_delay_r:
                            _tr_ok=False
                    if _tr_ok:
                        if exp_trail_half:
                            if sl_cur < cand: sl_cur=0.5*(sl_cur+cand)
                        elif sl_cur < cand:
                            sl_cur=cand
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    if exp_stop_slip_bps: fill=fill*(1.0-exp_stop_slip_bps/10000.0)
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "trail"
                    break
            else:
                # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    _tr_ok=True
                    if _trail_skip_rem>0:
                        _trail_skip_rem-=1; _tr_ok=False
                    if _tr_ok and exp_trail_delay_r>0 and risk>0:
                        if ((best-entry)*direction/risk) < exp_trail_delay_r:
                            _tr_ok=False
                    if _tr_ok:
                        if exp_trail_half:
                            if cand < sl_cur: sl_cur=0.5*(sl_cur+cand)
                        elif cand < sl_cur:
                            sl_cur=cand
                if hi >= sl_cur:
                    fill=max(sl_cur, float(c["open"]))
                    if exp_stop_slip_bps: fill=fill*(1.0+exp_stop_slip_bps/10000.0)
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur >= sl0 else "trail"
                    break
        if fine_ltf:
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts]
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; exit_px_f=None; outcome_f="open"
            _gray_until=""
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                if exp_fs_small_swing>0:
                    # OWNER PROPOSAL. Enter as the book does; when the swing that
                    # opened the trade CONFIRMS, measure how big that swing turned
                    # out to be and exit if it was small. Unlike the room-threshold
                    # exit already closed (CLOSED_DO_NOT_REPEAT.md), the quantity
                    # here is the swing's OWN leg, not the distance from our entry,
                    # and - this is the point - it is genuinely knowable at the FS
                    # bar: end_px and start_px are both settled at or before
                    # confirmed_at_idx, and the FS bar has closed.
                    #
                    # Gray mode: closing early frees the slot, and with
                    # cooldown_bars / max_consecutive_losses the next signal then
                    # starts a brand-new trade that displaces the winners we were
                    # protecting. That crossover is what made the earlier exit
                    # arms lose. With exp_fs_gray the exit also arms busy_until so
                    # the engine stays occupied and nothing new enters.
                    _fsg=fs_up_ts if direction==1 else fs_dn_ts
                    _fgi=bs.bisect_left(_fsg, ts)
                    if _fgi<len(_fsg) and _fsg[_fgi]==ts:
                        _swn=None
                        for _ss in swings_ltf:
                            _si2=int(_ss.get("fs_at_idx",-1))
                            if _si2>=0 and _si2<len(candles_ltf) and int(candles_ltf[_si2]["ts"])==ts:
                                _swn=_ss; break
                        if _swn is not None:
                            _sg2=_swn.get("seg",{}) or {}
                            _sp2=float(_sg2.get("start_px",0) or 0)
                            _ep2=float(_sg2.get("end_px",0) or 0)
                            _as=max(0,i-19)
                            _ah=max(float(candles_ltf[_q]["high"]) for _q in range(_as,i+1))
                            _al=min(float(candles_ltf[_q]["low"]) for _q in range(_as,i+1))
                            _atr2=(_ah-_al) if _ah>_al else 1.0
                            if _atr2>0 and abs(_ep2-_sp2)/_atr2 < exp_fs_small_swing:
                                fk, exit_px_f, outcome_f = k, float(c["close"]), "fs_small_swing"
                                if exp_fs_gray:
                                    _gray_until=c["date"]
                                break
                if exit_fs_max_gap_h>=0:
                    _fsd=fs_up_ts if direction==1 else fs_dn_ts
                    _fsl=bisect.bisect_left(_fsd, ts)
                    if _fsl<len(_fsd) and _fsd[_fsl]==ts:
                        _gap=(ts-bar_ts)/3600.0
                        if exit_fs_max_gap_h<=0 or _gap<=float(exit_fs_max_gap_h):
                            fk, exit_px_f, outcome_f = k, float(c["close"]), "fs_exit"
                            break
                _best_f_prev=best_f
                if direction==1:
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                if exp_partial_r>0 and not _partial_taken and risk>0:
                    _cur_rf=(best_f-entry)*direction/risk
                    if _cur_rf>=exp_partial_r:
                        _partial_taken=True; _partial_r=exp_partial_r
                # Same FS-extreme stop trigger as the 15m loop above, keyed on the
                # TRIGGER BAR'S TIMESTAMP because this loop walks 1m fine candles.
                # `_partial_taken`/`risk` are shared with the outer loop and are
                # not touched here. Only ever tightens, only to a level on the
                # losing side of the 1m price, so it cannot arm and take out in
                # the same bar.
                if _fs_trig_ts is not None and ts>=_fs_trig_ts:
                    _tf=_fs_trig_px
                    if sl_buf_atr>0:
                        _atr_f=(atr15[bar] if 0<=bar<len(atr15) else 0.0)
                        _tf=(_tf-_atr_f*sl_buf_atr) if direction==1 else (_tf+_atr_f*sl_buf_atr)
                    if direction==1:
                        if _tf>sl_cur_f and _tf<lo: sl_cur_f=_tf
                    else:
                        if _tf<sl_cur_f and _tf>hi: sl_cur_f=_tf
                if direction==1:
                    # D3 ordering fix 2026-09-20: ratchet BEFORE the SL check â€”
                    # the stop is armed at the activation instant (bar open), so
                    # this same 1m bar is enforced against the new level. Combined
                    # with the unconditional ratchet this is the full live-faithful
                    # semantics: armed at confirmation, enforced immediately.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        _tr_ok=True
                        if _trail_skip_rem>0:
                            _trail_skip_rem-=1; _tr_ok=False
                        if _tr_ok and exp_trail_delay_r>0 and risk>0:
                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:
                                _tr_ok=False
                        if _tr_ok:
                            if exp_trail_half:
                                if sl_cur_f < cand: sl_cur_f=0.5*(sl_cur_f+cand)
                            elif sl_cur_f < cand:
                                sl_cur_f=cand
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        if exp_stop_slip_bps: fill=fill*(1.0-exp_stop_slip_bps/10000.0)
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")
                        break
                else:
                    # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        _tr_ok=True
                        if _trail_skip_rem>0:
                            _trail_skip_rem-=1; _tr_ok=False
                        if _tr_ok and exp_trail_delay_r>0 and risk>0:
                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:
                                _tr_ok=False
                        if _tr_ok:
                            if exp_trail_half:
                                if cand < sl_cur_f: sl_cur_f=0.5*(sl_cur_f+cand)
                            elif cand < sl_cur_f:
                                sl_cur_f=cand
                    if hi >= sl_cur_f:
                        fill=max(sl_cur_f, float(c["open"]))
                        if exp_stop_slip_bps: fill=fill*(1.0+exp_stop_slip_bps/10000.0)
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "trail")
                        break
            if fk is None:
                outcome="open"
                exit_idx=n-1
                exit_px=float(fine_ltf[-1]["close"])
                exit_ts=int(fine_ltf[-1]["ts"])
                exit_date=fine_ltf[-1].get("date") or candles_ltf[-1]["date"]
            else:
                outcome=outcome_f
                exit_px=exit_px_f
                exit_ts=int(fine_ltf[fk]["ts"])
                exit_date=fine_ltf[fk].get("date")
                exit_idx=bisect.bisect_right(candle_ts, exit_ts)-1
                exit_idx=max(0, min(exit_idx, n-1))
                if not exit_date:
                    exit_date=candles_ltf[exit_idx]["date"]
        elif exit_idx is None:
            exit_idx=n-1
            exit_px=float(candles_ltf[-1]["close"])
            outcome="open"
        if not fine_ltf:
            exit_ts=int(candles_ltf[exit_idx]["ts"])
            exit_date=candles_ltf[exit_idx]["date"]
        move=(exit_px-entry) if direction==1 else (entry-exit_px)
        # Partial accounting. When the half was taken, the booked R is half the
        # trigger plus half the remaining move - the position really was cut, so
        # scoring it as a whole position would overstate every partial book.
        _partial_exit_price=0.0
        if _partial_taken and risk>0:
            _partial_exit_price=entry+direction*_partial_r*risk
            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)
            r_multiple=(_partial_r*0.5)+(_rem_move/risk)*0.5
        else:
            r_multiple=move/risk if risk>0 else 0
        # Streak halt (causal): book EVERY trade, then check streak
        if max_consecutive_losses > 0:
            if r_multiple <= 0:
                consecutive_losses += 1
                if consecutive_losses >= max_consecutive_losses:
                    halt_skip_next = True  # skip the NEXT entry
                    consecutive_losses = 0  # reset after halt
                else:
                    pass
            else:
                consecutive_losses = 0
        ltf_trades.append({
            "trade_no": len(ltf_trades)+1,
            "dir": "long" if direction==1 else "short",
            "swing_no": sig["swing_no"],
            "break_kind": sig["kind"],
            "htf_regime": use,
            # Window this trade was taken in. window_start + 3600 is when the
            # governing 1h bias candle closed, i.e. the earliest instant the
            # trade could have been known. entry_ts - that is the lead time.
            "window_start": int(win_start),
            "window_end": int(win_end),
            "entry_idx": i,
            "entry_ts": int(candles_ltf[i]["ts"]),
            "entry_date": candles_ltf[i]["date"],
            "entry_price": round(entry,2),
            "sl": round(sl0,2),
            "target": round(target,2),
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),
            "exit_date": exit_date,
            "exit_price": round(float(exit_px),2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple),3),
            "bars_held": exit_idx - i,
            # 0.0 when exp_partial_r never armed. run_experiment.py counts and
            # reports partials off this field, so it has to be present even on
            # the books that never take one.
            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,
        })
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
        if exp_max_concurrent > 0:
            _open_ivs.append((int(candles_ltf[i]["ts"]),
                              int(candles_ltf[exit_idx]["ts"]) if exit_idx is not None and exit_idx < n
                              else int(candles_ltf[i]["ts"])))
        if exp_no_opposite:
            _open_dirs.append((int(candles_ltf[i]["ts"]),
                               int(candles_ltf[exit_idx]["ts"]) if exit_idx is not None and exit_idx < n
                               else int(candles_ltf[i]["ts"]),
                               direction))
        if _gray_until and (not busy_until or _gray_until > busy_until):
            busy_until=_gray_until
        if cooldown_bars > 0 and r_multiple < 0:
            last_loss_bar = exit_idx
    # For each LTF trade, find its parent HTF interval.
    # Pass 1: flip intervals (direction-matched). Pass 2: b2 intervals as-is
    # for trades not covered by a flip. No trimming â€” b2 fills the gaps.
    _parent_ivs = {}
    _flip_starts = [s for s,_,_,_,_ in intervals_flip]
    _b2_starts = [s for s,_,_,_,_ in intervals_b2]
    # Pass 1: flip intervals for trades inside a same-direction flip
    for t in ltf_trades:
        ts = t["entry_ts"]
        td = 1 if t["dir"] == "long" else -1
        idx = bs.bisect_right(_flip_starts, ts) - 1
        if idx >= 0:
            iv = intervals_flip[idx]
            if iv[0] < ts <= iv[1] and iv[2] == td:
                key = (iv[0], iv[1], iv[2])
                if key not in _parent_ivs:
                    _parent_ivs[key] = iv
    # Pass 2: b2 intervals for trades not yet covered, no trimming.
    # B2 fills the gaps between flip windows. Some overlap with flip is OK.
    for t in ltf_trades:
        ts = t["entry_ts"]
        td = 1 if t["dir"] == "long" else -1
        regime = t.get("htf_regime", "flip")
        if regime == "b2" and intervals_b2:
            if any(iv[0] < ts <= iv[1] for iv in _parent_ivs.values()):
                continue
            idx = bs.bisect_right(_b2_starts, ts) - 1
            if idx >= 0:
                iv = intervals_b2[idx]
                if iv[0] < ts <= iv[1] and iv[2] == td:
                    key = (iv[0], iv[1], iv[2])
                    if key not in _parent_ivs:
                        _parent_ivs[key] = iv
    parent_intervals = sorted(_parent_ivs.values(), key=lambda x: x[0])

    return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
            "ltf_trades": ltf_trades, "intervals": parent_intervals}
