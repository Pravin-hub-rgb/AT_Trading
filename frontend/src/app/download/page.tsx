import DownloadPanel from "@/components/DownloadPanel";

export default function DownloadPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">Download Data</h1>
        <p className="text-sm text-[#8b949e]">
          Fetch Nifty 50 daily + 5-min OHLCV history from Upstox. Saved to{" "}
          <code className="text-[#6366f1]">data/nifty_daily.csv</code> and{" "}
          <code className="text-[#6366f1]">data/nifty_5min.csv</code>.
        </p>
      </div>
      <DownloadPanel />
    </div>
  );
}