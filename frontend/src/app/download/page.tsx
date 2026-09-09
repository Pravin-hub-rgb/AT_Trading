import DownloadPanel from "@/components/DownloadPanel";
import BtcFetchPanel from "@/components/BtcFetchPanel";

export default function DownloadPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-[#e6edf3]">Download Data</h1>
        <p className="text-sm text-[#8b949e]">
          Fetch OHLCV history from exchanges. Data is saved to CSV files in the{" "}
          <code className="text-[#6366f1]">data/</code> directory.
        </p>
      </div>

      {/* BTC / USDT — Binance */}
      <BtcFetchPanel />

      {/* Nifty 50 — Upstox */}
      <div>
        <h2 className="mb-2 text-base font-semibold text-[#e6edf3]">Nifty 50</h2>
        <DownloadPanel />
      </div>
    </div>
  );
}