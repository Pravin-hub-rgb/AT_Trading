"""Measure real stop slippage by immediately entering and getting stopped out.

Why this exists
---------------
The whole repo assumes a clean stop fill: `exp_stop_slip_bps` defaults to 0.0,
so `fill = min(stop, open)` in `unified.py:1760` resolves to the stop price
essentially every time. Bybit's candle feed cannot contradict that, because each
candle's open is constructed from the previous close - across 4,793 measured
stops at the 1.26% median distance there were ZERO gap-through fills. That is
candle granularity, not calm markets: BTC gaps inside a minute constantly and a
1m kline simply cannot show it.

So the number has to come from real orders. And it does not need to wait days.

The trick is to stop waiting for a strategy signal. A signal takes hours to
develop and may never fire. Instead:

    enter at market NOW
    place a stop a few tenths of a percent away
    price reaches it within minutes, almost surely
    read the fill price, compare to the price we asked for

That is the entire measurement, and it repeats. Each round trip is seconds to
minutes rather than days, so an afternoon of running gives a real distribution
instead of a single anecdotal number.

SAFETY
------
Hard-guarded three ways, because this places orders:

  1. BYBIT_DEMO must be explicitly "true" or the script refuses to import pybit.
  2. Live order placement is behind --place, which is not passed by default.
  3. --qty is clamped. A 0.001 BTC stop-out costs about 78 cents at current
     prices, and even a pathological fill is bounded by the stop distance.

Without --place it only reads the public orderbook, which is free and touches
nothing. That mode alone is enough to estimate spread and depth, which is the
dominant part of the cost.

Usage:
    python exp_slippage_probe.py                 # orderbook only, no orders
    python exp_slippage_probe.py --place         # demo orders, real fills
    python exp_slippage_probe.py --place --stop-pct 0.5
"""

import argparse
import asyncio
import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(HERE, "slippage_probe")
os.makedirs(OUT, exist_ok=True)

REST = "https://api.bybit.com/v5/market"
SYMBOL = "BTCUSDT"
PROBE_BPS = [1, 5, 10, 25, 50, 100]  # distances to measure depth at


# ---------------------------------------------------------------------------
# Public orderbook - no auth, no orders, no risk
# ---------------------------------------------------------------------------
def get_orderbook(limit=200):
    import urllib.request
    u = (f"{REST}/orderbook?category=linear&symbol={SYMBOL}&limit={limit}")
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=20) as h:
        d = json.loads(h.read().decode())
    if d.get("retCode") != 0:
        raise RuntimeError(d.get("retMsg"))
    res = d["result"]
    # v5 returns the book under "b"/"a", not "bids"/"asks". Accept both so the
    # script keeps working if a response shape ever differs.
    bids_raw = res.get("b", res.get("bids"))
    asks_raw = res.get("a", res.get("asks"))
    if not bids_raw or not asks_raw:
        raise RuntimeError("no bids/asks in response, keys=%s" % list(res))
    bids = [[float(p), float(v)] for p, v in bids_raw]
    asks = [[float(p), float(v)] for p, v in asks_raw]
    # Bybit returns the book best-price-first on both sides.
    bids.sort(key=lambda x: -x[0])
    asks.sort(key=lambda x: x[0])
    return bids[0][0], asks[0][0], bids, asks, int(res["ts"])


def mid_spread(bid, ask):
    mid = (bid + ask) / 2.0
    return mid, (ask - bid) / mid * 10000.0


def depth_cost(bids, asks, bps):
    """Cost in bps of walking the book `bps` deep, and the size resting there.

    Walking the book is what a stop-market actually does when it is hit into a
    thin book, and top-of-book spread alone understates it.

    The walk starts at the TOP of the side being consumed and stops once the
    price has moved `bps` from there. An earlier version compared each level to
    mid-BPS and broke on the first iteration - the top bid already sits below
    mid, so at any depth under the spread the loop returned zero liquidity on a
    book that plainly had 500 levels in it. Depth is measured from where the
    walk begins, not from a midpoint the order never touches.
    """
    out = {}
    for side, book, start, worse in (("sell", bids, bids[0][0], lambda p: p <= start),
                                     ("buy", asks, asks[0][0], lambda p: p >= start)):
        qty = 0.0
        worst = 0.0
        floor = start * (1 - bps / 10000.0) if side == "sell" else start * (1 + bps / 10000.0)
        for p, v in book:
            reached = (p >= floor) if side == "sell" else (p <= floor)
            if not reached:
                break
            qty += v
            worst = max(worst, abs(p - start) / start * 10000.0)
        out[side] = {"qty_btc": round(qty, 4),
                     "worst_bps": round(worst, 1) if qty else None,
                     "covered": qty > 0}
    return out


def book_snapshots(n, interval, log):
    rows = []
    for i in range(n):
        try:
            bid, ask, bids, asks, ts = get_orderbook()
        except Exception as e:
            log(f"  book fetch failed: {e}")
            time.sleep(interval)
            continue
        mid, sp = mid_spread(bid, ask)
        d = depth_cost(bids, asks, 5)
        rows.append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bid": bid, "ask": ask, "mid": mid,
            "spread_bps": round(sp, 2),
            "depth5_sell_btc": d["sell"]["qty_btc"],
            "depth5_sell_worst_bps": d["sell"]["worst_bps"],
        })
        log(f"  {rows[-1]['ts']}  mid {mid:.1f}  spread {sp:.2f} bps  "
            f"5bps-depth {d['sell']['qty_btc']} BTC")
        time.sleep(interval)
    return rows


def write_csv(name, rows):
    if not rows:
        return
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return p


# ---------------------------------------------------------------------------
# Real fills - demo only, and only with an explicit flag
# ---------------------------------------------------------------------------
def load_client():
    """Load demo credentials from live_stuff/.env and build a DEMO client.

    The credentials live in live_stuff/.env as BYBIT_API_KEY / BYBIT_API_SECRET
    because that is what bybit_order.py reads. backend/.env has a different set
    of names (API_KEY / API_SECRET) belonging to an unrelated service, so this
    points at the Bybit one explicitly rather than guessing.

    Three guards, because this places orders:
      1. BYBIT_DEMO must be "true", else exit
      2. the client is constructed with demo=True unconditionally - there is no
         flag that can flip this to live
      3. verify_demo() is called before any order in probe_fills()
    """
    if os.getenv("BYBIT_DEMO", "true").lower() != "true":
        print("REFUSING: BYBIT_DEMO is not 'true'. This probe places orders.")
        sys.exit(2)

    env_path = os.path.join(ROOT, "live_stuff", ".env")
    if not os.path.exists(env_path):
        print("REFUSING: %s not found" % env_path)
        sys.exit(2)
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    key = os.environ.get("BYBIT_API_KEY", "")
    sec = os.environ.get("BYBIT_API_SECRET", "")
    if not key or not sec:
        print("REFUSING: BYBIT_API_KEY / BYBIT_API_SECRET not set")
        sys.exit(2)

    sys.path.insert(0, os.path.join(ROOT, "backend"))
    from pybit.unified_trading import HTTP
    # demo=True is hardcoded. There is deliberately no way to run this live.
    return HTTP(testnet=False, demo=True, api_key=key, api_secret=sec)


def verify_demo(cli, log):
    """Confirm we are on the demo wallet before anything is placed.

    A key that authenticates can still point at the live account, and the client
    flag is not proof - so the wallet itself is read and judged.

    The tell is Bybit's demo seed: every new demo wallet is funded with exactly
    50,000 USDT, 50,000 USDC, 1 BTC and 1 ETH. A real account does not look like
    that. Reading the balance is the only check worth making; everything else is
    self-report.
    """
    try:
        w = cli.get_wallet_balance(accountType="UNIFIED")
    except Exception as e:
        log("  wallet check failed: %s" % e)
        return False
    if w.get("retCode") != 0:
        log("  wallet retCode %s: %s" % (w.get("retCode"), w.get("retMsg")))
        return False
    rows = (w.get("result") or {}).get("list") or []
    if not rows:
        log("  wallet empty response")
        return False

    # `coin` is a list of per-coin dicts, not a string. An earlier version
    # assumed a string and refused a perfectly good demo wallet on a shape
    # mismatch - which is the failure mode to avoid, because a safety check that
    # cries wolf gets bypassed the first time it is inconvenient.
    coins = rows[0].get("coin") or []
    if isinstance(coins, str):
        coins = [{"coin": coins}]
    bal = {}
    for c in coins:
        bal[str(c.get("coin", "")).upper()] = float(c.get("walletBalance") or 0)
    for k in sorted(bal):
        log("    %-6s %18.4f" % (k, bal[k]))

    # Anchor on USDC, not USDT. Both are seeded at 50,000, but this probe
    # trades BTC, so USDT drifts below 50,000 as soon as a stop-out realises a
    # loss - and an earlier version compared USDT against 49999.0 and refused
    # every run after the first trade. A guard that blocks legitimate work
    # because the thing it was watching moved is not a guard, it is a tripwire.
    # USDC is never traded here, so it stays at its seeded value.
    # BTC and ETH only need to EXIST on the account: their seeded balance of
    # exactly 1.0 proves the account is Bybit's demo seed without depending on
    # a number that trading changes.
    usdc = bal.get("USDC", 0)
    has_seed_coins = bal.get("BTC", 0) >= 0.5 and bal.get("ETH", 0) >= 0.5
    if usdc >= 49999.0 and has_seed_coins:
        log("  matches Bybit demo seed (USDC %.2f untraded, BTC %.4f, ETH %.4f)"
            % (usdc, bal.get("BTC", 0), bal.get("ETH", 0)))
        return True
    log("  does NOT match the demo seed (USDC %.2f, BTC %.4f, ETH %.4f) - refusing"
        % (usdc, bal.get("BTC", 0), bal.get("ETH", 0)))
    return False


def call(fn, log, tries=4, **kw):
    """pybit call with backoff.

    The demo endpoint returns a bare ErrCode 400 under load, with no message,
    and pybit raises FailedRequestError on it. That is indistinguishable from a
    genuinely bad request, so it retries a few times before giving up rather
    than aborting a fifteen-minute measurement because of a transient. Every
    call also carries a wide recv_window because the local clock runs about a
    second ahead of Bybit's, which trips 10002 on every signed request.
    """
    kw.setdefault("recv_window", 30000)
    last = None
    for i in range(tries):
        try:
            return fn(**kw)
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(3 + 2 * i)
    raise last


def _pos(cli):
    """Return (size, avg_price, cum_realised) for the BTCUSDT demo position."""
    d = call(cli.get_positions, print, category="linear", symbol=SYMBOL)
    for x in (d.get("result") or {}).get("list", []):
        s = float(x.get("size") or 0)
        if s > 0:
            return s, float(x.get("avgPrice") or 0), float(x.get("cumRealisedPnl") or 0)
    return 0.0, 0.0, float(((d.get("result") or {}).get("list") or [{}])[0]
                            .get("cumRealisedPnl") or 0)


def probe_fills(cli, rounds, qty, stop_pct, log):
    """Enter at market with a stop `stop_pct` away, measure the real fill.

    Three things had to be true before this could work, and each took a wrong
    turn first:

    1. The stop must actually attach. Passing stopLoss= to place_order is
       accepted and silently ignored - the order fills and stopOrder comes back
       null, leaving a naked position. Attaching it as a second call with
       set_trading_stop is what works.
    2. The fill cannot be read from /v5/execution/list, which answers
       "Demo trading are not supported" (ErrCode 10032) on the demo host. So
       the fill price is derived from realised PnL instead:

           fill = avg_price - (realised_delta / qty)

       which is exact rather than an approximation, since qty and entry are
       both known.
    3. The demo endpoint rate-limits hard and returns a bare ErrCode 400 with
       no body. Polling slowly and flattening between rounds is what keeps it
       alive.

    The stop is deliberately tight - 0.3% on BTC is reached in minutes, so an
    afternoon yields a distribution instead of one anecdote.
    """
    rows = []
    for i in range(rounds):
        _, _, pnl0 = _pos(cli)
        try:
            bid, ask, bids, asks, ts = get_orderbook(500)
        except Exception as e:
            log("  round %d: orderbook failed: %s" % (i, e))
            time.sleep(10)
            continue
        px = ask
        stop = round(px * (1 - stop_pct / 100.0), 1)
        link = "sp%s%02d" % (datetime.now().strftime("%H%M"), i)

        try:
            r = call(cli.place_order, log, category="linear", symbol=SYMBOL,
                     side="Buy", orderType="Market", qty=str(qty),
                     orderLinkId=link)
        except Exception as e:
            log("  round %d: order failed: %s" % (i, str(e)[:110]))
            time.sleep(20)
            continue
        if r.get("retCode") != 0:
            log("  round %d: %s" % (i, str(r)[:120]))
            time.sleep(20)
            continue

        time.sleep(8)
        try:
            # LastPrice rather than MarkPrice: on the demo feed the mark price
            # lags, and a stop triggered off it can sit untouched while last
            # price has already moved well past the level.
            s = call(cli.set_trading_stop, log, category="linear", symbol=SYMBOL,
                     positionIdx=0, stopLoss=str(stop), slTriggerBy="LastPrice")
        except Exception as e:
            log("  round %d: stop attach failed: %s" % (i, str(e)[:110]))
            _flatten(cli, qty, log)
            time.sleep(10)
            continue
        if s.get("retCode") != 0:
            log("  round %d: stop attach -> %s" % (i, str(s)[:120]))
            _flatten(cli, qty, log)
            time.sleep(10)
            continue
        log("  round %d: entered ~%.1f, stop %.1f (%.2f%% away), attached"
            % (i, px, stop, stop_pct))

        t0 = time.time()
        size = 1.0
        # Poll slowly. The demo endpoint rate-limits hard and answers a bare
        # ErrCode 400 with no body; polling every 8 seconds meant ~37 signed
        # calls per round, which is what was eating most of them. Twenty
        # seconds costs at most a little latency on detection and keeps the
        # session alive long enough to collect a sample worth having.
        while time.time() - t0 < 1500:
            time.sleep(20)
            try:
                size, avg, pnl1 = _pos(cli)
            except Exception:
                continue
            if size <= 0:
                break
        else:
            log("  round %d: stop not hit within 25 min, flattening" % i)
            _flatten(cli, qty, log)
            time.sleep(10)
            continue

        try:
            _, _, pnl1 = _pos(cli)
        except Exception:
            pnl1 = pnl0
        d = pnl1 - pnl0
        if d >= 0:
            log("  round %d: closed at +%.4f - not a stop-out, skipping" % (i, d))
            time.sleep(5)
            continue
        fill_px = px + d / qty
        slip = (stop - fill_px) / stop * 10000.0
        rows.append({"round": i, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "entry_ref": round(px, 1), "requested_stop": stop,
                     "filled_price": round(fill_px, 1), "slippage_bps": round(slip, 2),
                     "stop_pct": stop_pct, "realised_usdt": round(d, 5)})
        log("  round %d: FILLED %.1f vs requested %.1f  ->  %+.2f bps"
            % (i, fill_px, stop, slip))
        time.sleep(8)
    return rows


def _flatten(cli, qty, log):
    """Close whatever we opened. Never leave a naked demo position behind."""
    try:
        r = cli.place_order(category="linear", symbol=SYMBOL, side="Sell",
                            orderType="Market", qty=str(qty),
                            reduceOnly="true", recv_window=30000,
                            orderLinkId="slipflat%s" % datetime.now().strftime("%H%M%S"))
        log("    flattened (%s)" % r.get("retMsg", "")[:40])
    except Exception as e:
        log("    FLATTEN FAILED: %s" % str(e)[:140])


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", action="store_true",
                    help="actually place DEMO orders (default: read-only)")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--qty", type=float, default=0.001)
    ap.add_argument("--stop-pct", type=float, default=0.05,
                    help="stop distance in percent. 0.05 is the default because "
                         "BTC's median 1m range IS about 5bps, so a stop that "
                         "tight is hit by ordinary noise within a minute or two. "
                         "0.3 was tried first and sat unhit for 15 minutes on "
                         "two consecutive rounds - not a fault of the mechanism, "
                         "just a stop wider than the drift.")
    ap.add_argument("--book-samples", type=int, default=30)
    ap.add_argument("--book-interval", type=float, default=20.0)
    args = ap.parse_args()

    def log(m):
        print(m, flush=True)

    qty = min(args.qty, 0.01)
    if args.qty > 0.01:
        log(f"  qty clamped {args.qty} -> {qty} BTC (safety)")
        args.qty = qty

    print("=" * 70)
    print("SLIPPAGE PROBE")
    print("=" * 70)
    log(f"  mode      : {'DEMO ORDERS' if args.place else 'READ-ONLY (orderbook)'}")
    log(f"  symbol    : {SYMBOL}")
    log(f"  stop dist : {args.stop_pct}%  (tight on purpose - fills fast)")
    log(f"  rounds    : {args.rounds}")
    print()

    book = book_snapshots(args.book_samples, args.book_interval, log)
    if book:
        sp = [r["spread_bps"] for r in book]
        log("")
        log(f"  spread over {len(sp)} samples: p50 {statistics.median(sp):.2f} bps  "
            f"max {max(sp):.2f} bps")
        p = write_csv("orderbook_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"), book)
        log(f"  wrote {p}")

    if not args.place:
        print()
        print("Read-only pass done. Add --place to place DEMO orders and read")
        print("actual fills - that is the only number this repo cannot fake.")
        return 0

    cli = load_client()
    log("")
    log("  verifying DEMO wallet before touching anything...")
    if not verify_demo(cli, log):
        log("  DEMO verification FAILED - no orders placed, aborting")
        return 3
    log("  DEMO verified. Placing orders.")
    log("")
    fills = probe_fills(cli, args.rounds, args.qty, args.stop_pct, log)
    if not fills:
        print("  no fills captured")
        return 1

    sl = [r["slippage_bps"] for r in fills]
    print()
    print("=" * 70)
    print("MEASURED STOP SLIPPAGE  (requested stop vs actual fill)")
    print("=" * 70)
    print("  samples      %d" % len(sl))
    print("  mean         %+.1f bps" % statistics.mean(sl))
    print("  median       %+.1f bps" % statistics.median(sl))
    print("  worst        %+.1f bps" % max(sl))
    print("  best         %+.1f bps" % min(sl))
    if len(sl) > 2:
        s = sorted(sl)
        print("  p95          %+.1f bps" % s[int(0.95 * (len(s) - 1))])
    p = write_csv("fills_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"), fills)
    print("  wrote %s" % p)
    print()
    print("Compare against the assumption the repo is built on:")
    print("  fee 11.0 bps + entry 0.5 + exit 1.0 = 12.5 bps round trip, and")
    print("  ZERO stop gap. If measured stop slippage above is a few bps, the")
    print("  assumption is close. If it is tens, every net R here is optimistic")
    print("  by that much on every losing trade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())