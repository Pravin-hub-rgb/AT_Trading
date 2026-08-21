"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  DataStatus,
  IntervalStatus,
  OperationStatus,
  Settings,
  TokenStatus,
  getDataStatus,
  getOperationStatus,
  getSettings,
  getTokenStatus,
  putSettings,
  startDownload,
  updateData,
  validateToken,
} from "@/lib/api";
import TokenDialog from "./TokenDialog";

const badgeStyles: Record<IntervalStatus["badge"], { pill: string; bar: string }> = {
  fresh: { pill: "bg-[#10b981]/20 text-[#10b981]", bar: "bg-[#10b981]" },
  stale: { pill: "bg-[#f59e0b]/20 text-[#f59e0b]", bar: "bg-[#f59e0b]" },
  partial: { pill: "bg-[#60a5fa]/20 text-[#60a5fa]", bar: "bg-[#60a5fa]" },
  no_data: { pill: "bg-[#64748b]/20 text-[#64748b]", bar: "bg-[#64748b]" },
};

const intervalLabels: Record<string, string> = { daily: "Daily", "5min": "5-min" };

export default function DownloadPanel() {
  const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null);
  const [op, setOp] = useState<OperationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [validating, setValidating] = useState(false);
  const [interval, setInterval] = useState("both");
  const [years, setYears] = useState(1);
  const pollRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refresh = useCallback(() => {
    getDataStatus().then(setDataStatus).catch(() => {});
    getSettings().then(setSettings).catch(() => {});
    getTokenStatus().then(setTokenStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    return stopPolling;
  }, [refresh, stopPolling]);

  const pollOperation = (operationId: string) => {
    setError(null);
    const tick = () => {
      getOperationStatus(operationId)
        .then((s) => {
          setOp(s);
          if (s.status === "done" || s.status === "error") {
            stopPolling();
            if (s.status === "error") setError(s.error || s.message);
            refresh();
          }
        })
        .catch((e) => {
          stopPolling();
          setError(e instanceof Error ? e.message : String(e));
        });
    };
    tick();
    pollRef.current = window.setInterval(tick, 1000);
  };

  const handleUpdate = async () => {
    try {
      const res = await updateData();
      setOp({ ...res, progress: 0, message: "Updating...", log: [], intervals: ["daily", "5min"], years: 0, done_months: 0, total_months: 0, error: null, mode: "update" });
      pollOperation(res.operation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleFullDownload = async () => {
    try {
      const res = await startDownload(interval, years);
      setOp({ ...res, progress: 0, message: "Downloading...", log: [], intervals: interval === "both" ? ["daily", "5min"] : [interval], years, done_months: 0, total_months: 0, error: null, mode: "download" });
      pollOperation(res.operation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleValidate = async () => {
    if (!tokenStatus?.configured) {
      setTokenOpen(true);
      return;
    }
    setValidating(true);
    try {
      const res = await validateToken({ token: "", api_key: "", api_secret: "" });
      refresh();
      if (!res.valid) setError(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setValidating(false);
    }
  };

  const toggleAutoUpdate = async (enabled: boolean) => {
    try {
      const s = await putSettings({ auto_update: enabled });
      setSettings(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const busy = op?.status === "running";

  return (
    <div className="space-y-4">
      {/* Token status */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <div className="text-sm">
          <span className="text-[#8b949e]">Token: </span>
          {tokenStatus?.configured ? (
            <span className="font-mono text-[#e6edf3]">{tokenStatus.masked_token}</span>
          ) : (
            <span className="text-[#ef4444]">not configured</span>
          )}
          <span className="ml-3 text-[#8b949e]">
            Key: {tokenStatus?.api_key_configured ? "✓" : "✗"} · Secret: {tokenStatus?.api_secret_configured ? "✓" : "✗"}
          </span>
          <span
            className={`ml-3 rounded-full px-2 py-0.5 text-xs font-medium ${
              tokenStatus?.valid ? "bg-[#10b981]/20 text-[#10b981]"
              : tokenStatus?.valid === false ? "bg-[#ef4444]/20 text-[#ef4444]"
              : "bg-[#f59e0b]/20 text-[#f59e0b]"
            }`}
          >
            {tokenStatus?.valid ? "valid" : tokenStatus?.valid === false ? "invalid" : "not checked"}
          </span>
          {tokenStatus?.last_price != null && (
            <span className="ml-3 text-xs text-[#8b949e]">Nifty LTP {tokenStatus.last_price}</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setTokenOpen(true)}
            className="rounded-md border border-[#30363d] px-3 py-1.5 text-sm text-[#e6edf3] hover:bg-[#21262d]"
          >
            Edit
          </button>
          <button
            onClick={handleValidate}
            disabled={validating || busy}
            className="rounded-md border border-[#6366f1] px-3 py-1.5 text-sm text-[#6366f1] hover:bg-[#6366f1]/10 disabled:opacity-50"
          >
            {validating ? "Checking..." : "Validate"}
          </button>
        </div>
      </div>

      {/* Status cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {(["daily", "5min"] as const).map((key) => {
          const s = dataStatus?.[key];
          const badge = s ? badgeStyles[s.badge] : badgeStyles.no_data;
          return (
            <div key={key} className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold text-[#e6edf3]">{intervalLabels[key]}</span>
                {s ? (
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.pill}`}>
                    {s.badge === "fresh" ? "Up to date" : s.badge === "stale" ? `Stale ${s.days_behind}d` : s.badge === "partial" ? "Partial" : "No data"}
                  </span>
                ) : (
                  <span className="text-xs text-[#8b949e]">...</span>
                )}
              </div>
              {s ? (
                <>
                  <div className="mb-1 h-2 w-full overflow-hidden rounded-full bg-[#21262d]">
                    <div className={`h-full rounded-full ${badge.bar}`} style={{ width: `${s.coverage}%` }} />
                  </div>
                  <p className="mb-2 text-xs text-[#8b949e]">
                    {s.coverage}% of requested window · {s.row_count.toLocaleString()} candles
                    {s.first_ts && s.last_ts ? ` · ${s.first_ts.slice(0, 10)} → ${s.last_ts.slice(0, 10)}` : ""}
                  </p>
                  <p className="text-sm text-[#e6edf3]">{s.message}</p>
                  {s.missing_months.length > 0 && (
                    <p className="mt-1 text-xs text-[#f59e0b]">Missing months: {s.missing_months.join(", ")}</p>
                  )}
                </>
              ) : (
                <p className="text-sm text-[#8b949e]">Loading status...</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-[#e6edf3]">Update now</h3>
            <p className="text-xs text-[#8b949e]">
              Smart sync — fills gaps and appends today&apos;s candles. Shows &quot;already up to date&quot; when fresh.
            </p>
          </div>
          <button
            onClick={handleUpdate}
            disabled={busy || tokenStatus?.valid === false}
            className="rounded-md bg-[#10b981] px-5 py-2 text-sm font-medium text-white hover:bg-[#34d399] disabled:opacity-50"
          >
            {op?.mode === "update" && busy ? "Updating..." : "Update now"}
          </button>
        </div>
        <div className="mt-4 border-t border-[#21262d] pt-4">
          <h3 className="font-semibold text-[#e6edf3]">Full download</h3>
          <p className="mb-3 text-xs text-[#8b949e]">Initial 1-year fetch (or re-download a wider window).</p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex gap-1">
              {[
                { value: "both", label: "Daily + 5-min" },
                { value: "daily", label: "Daily" },
                { value: "5min", label: "5-min" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setInterval(opt.value)}
                  disabled={busy}
                  className={`rounded-md border px-3 py-1.5 text-sm transition-colors disabled:opacity-50 ${
                    interval === opt.value
                      ? "border-[#6366f1] bg-[#6366f1]/20 text-[#e6edf3]"
                      : "border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[#8b949e]">Years</label>
              <input
                type="number"
                min={1}
                max={5}
                value={years}
                onChange={(e) => setYears(Math.max(1, Math.min(5, Number(e.target.value) || 1)))}
                disabled={busy}
                className="w-24 rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-1.5 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1] disabled:opacity-50"
              />
            </div>
            <button
              onClick={handleFullDownload}
              disabled={busy || tokenStatus?.valid === false}
              className="rounded-md bg-[#6366f1] px-5 py-2 text-sm font-medium text-white hover:bg-[#7c7ff7] disabled:opacity-50"
            >
              {op?.mode === "download" && busy ? "Downloading..." : "Full download"}
            </button>
          </div>
        </div>
        {/* Auto-update */}
        <div className="mt-4 flex flex-wrap items-center justify-between border-t border-[#21262d] pt-4">
          <div>
            <h3 className="font-semibold text-[#e6edf3]">Auto-update</h3>
            <p className="text-xs text-[#8b949e]">
              Backend checks after <span className="text-[#e6edf3]">{settings?.update_time ?? "19:00"}</span> IST on
              weekdays and updates if stale.
            </p>
          </div>
          <button
            onClick={() => toggleAutoUpdate(!settings?.auto_update)}
            disabled={busy}
            className={`relative h-6 w-12 rounded-full transition-colors disabled:opacity-50 ${
              settings?.auto_update ? "bg-[#10b981]" : "bg-[#30363d]"
            }`}
            aria-pressed={settings?.auto_update}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
                settings?.auto_update ? "left-6" : "left-0.5"
              }`}
            />
          </button>
        </div>
      </div>

      {/* Progress + log */}
      {error && (
        <div className="rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-4 py-3 text-sm text-[#ef4444]">{error}</div>
      )}
      {op && (
        <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-[#e6edf3]">{op.message}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                op.status === "done"
                  ? "bg-[#10b981]/20 text-[#10b981]"
                  : op.status === "error"
                    ? "bg-[#ef4444]/20 text-[#ef4444]"
                    : "bg-[#6366f1]/20 text-[#6366f1]"
              }`}
            >
              {op.status}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[#21262d]">
            <div
              className={`h-full rounded-full transition-all ${op.status === "error" ? "bg-[#ef4444]" : "bg-[#6366f1]"}`}
              style={{ width: `${op.progress}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-[#8b949e]">
            {op.done_months}/{op.total_months} months · {op.progress}%
          </p>
          {op.log.length > 0 && (
            <div className="mt-3 max-h-48 overflow-y-auto rounded-md border border-[#21262d] bg-[#0d1117] p-3 font-mono text-xs text-[#8b949e]">
              {op.log.slice(-50).map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <TokenDialog open={tokenOpen} onClose={() => { setTokenOpen(false); refresh(); }} />
    </div>
  );
}