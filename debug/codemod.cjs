const fs = require("fs");

// ── 1) upstox_fetcher.py: intraday fetch fn + merge in _sync_interval ──
{
  const p = "backend/src/upstox_fetcher.py";
  let s = fs.readFileSync(p, "utf8");
  const reps = [];

  // add fetch_intraday_candles before build_url
  reps.push([
`def build_url(instrument_key: str, api_interval: str, to_date: str, from_date: str) -> str:`,
`def fetch_intraday_candles(token: str, instrument_key: str, api_interval: str) -> list:
    """CURRENT trading day's candles. The dated historical endpoint excludes
    today's session entirely — Upstox serves it via this /intraday route."""
    key = quote(instrument_key, safe="")
    url = f"{BASE_URL}/intraday/{key}/{api_interval}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code == 401:
        raise RuntimeError("Invalid/expired access token (401)")
    resp.raise_for_status()
    return ((resp.json() or {}).get("data") or {}).get("candles") or []


def build_url(instrument_key: str, api_interval: str, to_date: str, from_date: str) -> str:`]);

  // merge intraday into _sync_interval tail
  reps.push([
`    return {
        "rows_fetched": total_fetched,
        "months_fetched": fetched_months,
        "months_scanned": total,
        "up_to_date": total_fetched == 0,
    }`,
`    # TODAY's candles live on the /intraday route — the dated historical API
    # excludes the current session entirely. Merge them when the requested
    # window reaches today.
    if requested_to >= _ist_now().date():
        try:
            candles = fetch_intraday_candles(token, NIFTY_INDEX_KEY, api_interval)
        except Exception:
            candles = []
        if candles:
            rows = [process_candle(c) for c in candles]
            day_df = pd.DataFrame(rows)
            day_df["timestamp"] = pd.to_datetime(day_df["timestamp"])
            existing_ts = set(df["timestamp"]) if not df.empty else set()
            new_rows_today = int((~day_df["timestamp"].isin(existing_ts)).sum())
            df = pd.concat([df, day_df], ignore_index=True)
            df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp")
            df.to_csv(path, index=False)
            total_fetched += new_rows_today

    return {
        "rows_fetched": total_fetched,
        "months_fetched": fetched_months,
        "months_scanned": total,
        "up_to_date": total_fetched == 0,
    }`]);

  let fails = [];
  for (const [i, [a, b]] of reps.entries()) {
    if (!s.includes(a)) { fails.push(i); continue; }
    s = s.split(a).join(b);
  }
  if (fails.length) { console.error("upstox_fetcher FAILED blocks:", fails); process.exit(1); }
  fs.writeFileSync(p, s, "utf8");
  console.log("upstox_fetcher.py patched ✓");
}
