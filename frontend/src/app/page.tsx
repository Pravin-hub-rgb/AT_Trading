import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center">
      <h1 className="text-3xl font-bold text-[#e6edf3]">
        AT <span className="text-[#6366f1]">Trading</span> Bot
      </h1>
      <p className="max-w-xl text-[#8b949e]">
        Chart-based trading assistant following the six-session theory. Start by
        downloading Nifty 50 historical data from Upstox, then view it on a live chart.
      </p>
      <div className="flex gap-3">
        <Link
          href="/download"
          className="rounded-md bg-[#6366f1] px-5 py-2 text-sm font-medium text-white hover:bg-[#7c7ff7]"
        >
          Download data
        </Link>
        <Link
          href="/chart"
          className="rounded-md border border-[#30363d] px-5 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]"
        >
          View chart
        </Link>
      </div>
    </div>
  );
}