"use client";

import { useEffect, useState } from "react";
import { validateToken } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function TokenDialog({ open, onClose }: Props) {
  const [token, setToken] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ valid: boolean; message: string } | null>(null);

  useEffect(() => {
    if (open) {
      setToken("");
      setApiKey("");
      setApiSecret("");
      setError(null);
      setResult(null);
    }
  }, [open]);

  if (!open) return null;

  const save = async () => {
    if (!token.trim()) {
      setError("Access token is required");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await validateToken({ token: token.trim(), api_key: apiKey.trim(), api_secret: apiSecret.trim() });
      setResult({ valid: res.valid, message: res.message });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-lg border border-[#30363d] bg-[#161b22] p-6 shadow-xl">
        <h2 className="mb-1 text-lg font-semibold text-[#e6edf3]">Upstox Credentials</h2>
        <p className="mb-4 text-sm text-[#8b949e]">
          Stored in <code className="text-[#6366f1]">backend/.env</code>. Token is validated against the live Nifty
          LTP quote before saving.
        </p>
        <div className="space-y-3">
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Access token"
            className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1]"
          />
          <input
            type="text"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="API Key (optional)"
            className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1]"
          />
          <input
            type="password"
            value={apiSecret}
            onChange={(e) => setApiSecret(e.target.value)}
            placeholder="API Secret (optional)"
            className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1]"
          />
        </div>
        {error && <p className="mt-3 text-sm text-[#ef4444]">{error}</p>}
        {result && (
          <p className={`mt-3 text-sm ${result.valid ? "text-[#10b981]" : "text-[#ef4444]"}`}>
            {result.valid ? "✓ " : "✗ "}
            {result.message}
          </p>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-[#30363d] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]"
          >
            Close
          </button>
          <button
            onClick={save}
            disabled={busy}
            className="rounded-md bg-[#6366f1] px-4 py-2 text-sm font-medium text-white hover:bg-[#7c7ff7] disabled:opacity-50"
          >
            {busy ? "Validating..." : "Save & Validate"}
          </button>
        </div>
      </div>
    </div>
  );
}