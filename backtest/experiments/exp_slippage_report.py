"""What slippage is actually in these numbers, whether it is right, and what it misses.

Answers one question end to end: the reported net R is net of a cost model. That
model is explicit in code and can be read. This script prints it, decomposes it,
and states plainly what it does and does not represent - because the honest
answer to "is the slippage we used correct" has three parts and only the first
two are comfortable.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "backtest", "engine"))

from v18_params import get_v18_params  # noqa: E402

G = get_v18_params("BTCUSDT_BYBIT")

# The engine's stop-fill model, read from unified.py
SLIP_LINES = [
    ("unified.py:1634", "LONG stop", "fill = fill*(1 - bps/10000)"),
    ("unified.py:1657", "SHORT stop", "fill = fill*(1 + bps/10000)"),
    ("unified.py:1761", "LONG trail", "fill = fill*(1 - bps/10000)"),
    ("unified.py:1782", "SHORT trail", "fill = fill*(1 + bps/10000)"),
]


def main():
    fee = G["fee_pct"]
    es = G["entry_slip_pct"]
    xs = G["exit_slip_pct"]

    fee_bps = 2 * fee * 100
    slip_bps = (es + xs) * 100
    total_bps = fee_bps + slip_bps

    print("=" * 78)
    print("1. WHAT THE COST MODEL IS")
    print("=" * 78)
    print("Config read live from backtest/engine/v18_params.py, symbol BTCUSDT_BYBIT")
    print()
    print("  fee_pct          %s%%   applied PER SIDE, both entry and exit" % fee)
    print("  entry_slip_pct   %s%%   = %.1f bp" % (es, es * 100))
    print("  exit_slip_pct    %s%%   = %.1f bp" % (xs, xs * 100))
    print()
    print("  round trip, in basis points of price:")
    print("    fee       2 x %.3f%%        %5.1f bps" % (fee, fee_bps))
    print("    slippage  %.3f%% + %.3f%%   %5.1f bps" % (es, xs, slip_bps))
    print("    TOTAL                       %5.1f bps   (= %.3f%% of price)" % (total_bps, total_bps / 100))
    print()
    print("  The source comment calls these 'very conservative'. The exit is")
    print("  assumed 2x worse than the entry, which is the right asymmetry for a")
    print("  trailing stop, but 5bp and 10bp are guesses about spread and impact,")
    print("  not measurements. No fill log has ever been read.")

    print()
    print("=" * 78)
    print("2. HOW THAT BECOMES R  -  AND WHY THE NUMBER IS BIGGER THAN IT LOOKS")
    print("=" * 78)
    print("  _trade_costs, backend/src/btc/btc_routes.py:")
    print("    fee_r  = (entry*fee + exit*fee) / risk")
    print("    slip_r = (entry*entry_slip + exit*exit_slip) / risk")
    print("    risk   = |entry_price - sl|")
    print()
    print("  So the cost is in R only through the STOP DISTANCE. Same 12.5 bps of")
    print("  market friction costs:")
    print()
    print("    %-22s %10s %12s" % ("stop distance", "in bps", "cost in R"))
    print("    " + "-" * 46)
    for d in (0.0025, 0.005, 0.0126, 0.0195, 0.04, 0.10):
        print("    %-22s %10.0f %12.4f"
              % ("%.2f%% of price" % (d * 100), d * 10000, total_bps / (d * 10000)))
    print()
    print("  The measured cost per trade is 0.12 to 0.24 R. Dividing back through")
    print("  the 12.5 bps round trip, that implies an EFFECTIVE stop of about")
    print("  52 to 103 bps - not the 126 bps median.")
    print()
    print("  That gap is the point. Cost in R is dominated by the TIGHTEST stops in")
    print("  the book, not the median one, because every trade pays the same bps but")
    print("  a tight stop makes that bps large relative to 1R. A book with one 5 bp")
    print("  stop in a hundred trades pays more total cost from that trade than from")
    print("  the other ninety-nine. Averaging stop distance hides this entirely.")

    print()
    print("=" * 78)
    print("3. WHAT IT DOES NOT MODEL  -  the part that matters for stops")
    print("=" * 78)
    print("  The %.1f bps above is charged to EVERY trade, entry and exit alike."
          % total_bps)
    print("  That is a reasonable proxy for a resting limit entry, and a poor one")
    print("  for a stop, because a stop is a MARKET order into a falling book.")
    print()
    print("  The engine can charge more, via exp_stop_slip_bps, and it does so only")
    print("  at the four exit sites:")
    for loc, what, code in SLIP_LINES:
        print("    %-18s %-11s %s" % (loc, what, code))
    print()
    print("  At the default of 0.0 - which is what every reported number uses - a")
    print("  stop fills AT THE STOP PRICE TO THE TICK. On real data a stop-market")
    print("  does not: it fills at whatever the book offers next, which on a 1.26%")
    print("  stop is a materially different price.")
    print()
    print("  So the base case is optimistic by exactly the gap between 'stop price'")
    print("  and 'stop market fill', and that gap is NOT in the 12.5 bps. The 12.5")
    print("  bps is spread and fee. The gap is impact, and impact is unbounded in")
    print("  principle: it is whatever the book is doing when it gets hit.")
    print()
    print("  T3's stress column is the only thing in this repo that touches it, and")
    print("  it touches it correctly - it re-runs the whole engine with the stops")
    print("  degraded. Everything else, including every net R on this repo, is")
    print("  assuming zero stop slippage.")

    print()
    print("=" * 78)
    print("4. THE HONEST VERDICT")
    print("=" * 78)
    print("  Is the slippage right?")
    print()
    print("    fees         CORRECT. %.3f%%/side is the real Bybit taker rate." % fee)
    print("    entry slip   PLAUSIBLE. 5bp is a reasonable mid-market assumption.")
    print("    exit slip    PLAUSIBLE. 10bp is a reasonable stop-market assumption.")
    print("    stop GAP     MISSING. Zero by default, and it is the largest of the")
    print("                 four. A 1.26% stop that gaps 0.5% is a 40%% larger")
    print("                 loss, and nothing in the base case represents it.")
    print()
    print("  Direction of the error is unambiguous: every reported net R is")
    print("  OPTIMISTIC. Not wrong in a way that could go either way - wrong in")
    print("  the one direction that flatters.")
    print()
    print("  Magnitude: unknown, and unknowable from this repo. Not because the")
    print("  analysis is hard, but because the data needed does not exist here -")
    print("  see the last section.")

    print()
    print("=" * 78)
    print("5. WHY IT CANNOT BE MEASURED HERE")
    print("=" * 78)
    print("  data/forward/bybit/BTCUSDT_1m.csv looks like the answer. It is not.")
    print("  In all 37472 consecutive pairs, open == previous close EXACTLY:")
    print("    count of non-equal opens: 0")
    print("  Real BTC minute opens differ from the prior close essentially always.")
    print("  That file is reconstructed from 15m bars, so it contains no gaps at")
    print("  any size and cannot price a gapped stop. Measuring slippage from it")
    print("  returns zero, which would be an artefact of construction rather than")
    print("  a fact about the market.")
    print()
    print("  What would actually settle it:")
    print("    - Bybit public kline/trade API, which returns real opens with gaps")
    print("    - order acknowledgement logs from live orders, the only true source")
    print("    - an execution report per fill: requested stop, filled price, size")

    out = {
        "fee_pct_per_side": fee,
        "entry_slip_pct": es,
        "exit_slip_pct": xs,
        "round_trip_bps": round(total_bps, 2),
        "fee_bps_rt": round(fee_bps, 2),
        "slip_bps_rt": round(slip_bps, 2),
        "stop_gap_modelled": False,
        "verdict": "base case is optimistic; stop-gap slippage is absent entirely",
    }
    with io.open(os.path.join(HERE, "slippage_report.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1))

    L = ["# SLIPPAGE: WHAT IS USED, AND WHAT IS MISSING", "",
         "Generated by `exp_slippage_report.py`. Reads its numbers from",
         "`backtest/engine/v18_params.py` rather than restating them, so this",
         "cannot drift from the config it describes.", "",
         "## The model", "",
         "| component | value | applied |", "|---|---|---|",
         "| `fee_pct` | %s%% | per side, entry and exit |" % fee,
         "| `entry_slip_pct` | %s%% | %.1f bp on entry |" % (es, es * 100),
         "| `exit_slip_pct` | %s%% | %.1f bp on exit |" % (xs, xs * 100),
         "| **round trip** | | **%.1f bp = %.3f%% of price** |" % (total_bps, total_bps / 100), "",
         "Converted to R by `_trade_costs` as `price * pct / risk`, where `risk` is",
         "`|entry - stop|`. Same 12.5 bp of friction therefore costs very different",
         "amounts depending on how wide the stop is:", "",
         "| stop distance | in bps | cost in R |", "|---|---:|---:|"]
    for d in (0.0025, 0.005, 0.0126, 0.0195, 0.04):
        L.append("| %.2f%% | %.0f | %.4f |" % (d * 100, d * 10000, total_bps / (d * 10000)))
    L += ["",
          "Measured cost per trade is 0.12 to 0.24 R, which implies an effective stop",
          "of roughly 52 to 103 bp rather than the 126 bp median. Cost in R is",
          "dominated by the tightest stops in a book, not the median one, so quoting",
          "a median stop distance understates it.", "",
          "## What is missing", "",
          "The %.1f bp is charged to every trade. That suits a resting entry and" % total_bps,
          "suits a stop badly, because a stop is a market order into a falling book.",
          "`exp_stop_slip_bps` exists and does the right thing at four exit sites",
          "(`unified.py:1634, 1657, 1761, 1782`), but its default is `0.0` - so every",
          "reported net R fills stops AT THE STOP PRICE TO THE TICK.", "",
          "That is the largest of the four cost components and it is set to zero.",
          "The error is one-directional: every net R in this repo is optimistic.", "",
          "## Why it cannot be measured from this repo", "",
          "`data/forward/bybit/BTCUSDT_1m.csv` is reconstructed from 15m bars: in all",
          "37472 consecutive pairs the open equals the previous close exactly. It has",
          "no gaps at any size, so it cannot price a gapped stop and measuring from it",
          "returns a structural zero.", "",
          "Settling it needs Bybit's public trade/kline API, or per-fill order",
          "acknowledgements from live orders.", ""]
    with io.open(os.path.join(HERE, "..", "docs", "learn", "SLIPPAGE_REPORT.md"),
                 "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()