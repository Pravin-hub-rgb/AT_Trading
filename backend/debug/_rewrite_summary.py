import io

p = "backend/src/btc/btc_routes.py"
s = io.open(p, encoding="utf-8").read()

# find the btc_summary function
i = s.find("def btc_summary")
assert i > 0, "btc_summary not found"
# find the end of the function (next @router or end of file)
j = s.find("\n@router", i + 1)
if j < 0:
    j = len(s)
old_fn = s[i:j]

# build the new function
new_fn = '''def btc_summary(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    fee_pct: float = 0.05,
    slippage_pts: float = 2.0,
    entry_selection: str = "stream",
):
    """\\'Konsi best hai\\' table - every master preset on its OWN reference TF.

    Each preset is evaluated on the timeframe it was designed for (bestTf),
    with its own minBars/swing config, then reports base R (zero cost) AND
    net R after fee_pct %/side + slippage_pts. `best` = highest net_r row.
    """
    if entry_selection not in ("stream", "final"):
        return JSONResponse(status_code=400, content={"detail": "entry_selection must be stream | final"})
    if not (0 <= float(fee_pct) <= 0.5):
        return JSONResponse(status_code=400, content={"detail": "fee_pct must be 0..0.5 (% per side)"})
    if not (0 <= float(slippage_pts) <= 1000):
        return JSONResponse(status_code=400, content={"detail": "slippage_pts must be 0..1000"})

    # group presets by their reference TF, load each TF\\'s data once
    by_tf: dict = {}
    for p in _MASTER_PRESETS:
        ptf = p.get("bestTf", tf)
        by_tf.setdefault(ptf, []).append(p)

    rows = []
    for ptf, presets in by_tf.items():
        win_p, err_p = _load_window(ptf, None)
        if err_p:
            continue
        candles_p, flow_p = win_p

        # 15m bias timeline (only for presets on lower TFs)
        bias_timeline = None
        if ptf in ("1m", "5m"):
            htf, htf_err = _load_window("15m", None)
            if htf_err is None:
                htf_candles, htf_flow = htf
                htf_swings = _compute_swings(htf_flow, mode)
                bias_timeline = sorted(
                    (
                        int(htf_candles[s["confirmed_at_idx"]]["ts"]),
                        s["dir"],
                    )
                    for s in htf_swings
                    if 0 <= int(s.get("confirmed_at_idx", -1)) < len(htf_candles)
                )

        # 1m-precise exit fills
        fine = None
        if ptf != "1m":
            fine = _load_fine_1m(candles_p[0]["ts"], candles_p[-1]["ts"]) or None

        for p in presets:
            sw_p = _compute_swings(flow_p, mode, min_bars=p["min_bars"])
            row = _run_preset(
                candles_p, sw_p, p, fee_pct, slippage_pts,
                bias_timeline=bias_timeline if p["bias"] == "15m" else None,
                day_gate=_streak_regime_gate(candles_p) if p["regime"] == "streak_311" else None,
                fine=fine,
                entry_selection=entry_selection,
            )
            row["tf"] = ptf
            rows.append(row)

    rows.sort(key=lambda r: r["net_r"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    return {
        "fee_pct": float(fee_pct),
        "slippage_pts": float(slippage_pts),
        "entry_selection": entry_selection,
        "rows": rows,
        "best": rows[0]["key"] if rows else None,
    }
'''

# add @router.get("/summary") decorator if the old function had it
if "@router.get(" in old_fn.split("\n")[0]:
    decorator_line = old_fn.split("\n")[0]
    new_fn = decorator_line + "\n" + new_fn

s = s[:i] + new_fn + s[j:]
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("btc_summary rewritten with per-preset bestTf")
