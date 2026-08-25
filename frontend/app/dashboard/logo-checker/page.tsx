"use client";

import { useRef, useState } from "react";
import { Shirt, Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import AppShell from "@/components/AppShell";
import RegMarks from "@/components/RegMarks";
import StatusStamp, { type StampStatus } from "@/components/StatusStamp";
import { useAuthGuard } from "@/lib/useAuth";
import { api, ApiError, type LogoOut } from "@/lib/api-client";

const METHODS = [
  { value: "unspecified", label: "Not specified" },
  { value: "screen_print", label: "Screen print" },
  { value: "dtg", label: "Direct-to-garment (DTG)" },
  { value: "sublimation", label: "Sublimation" },
  { value: "embroidery", label: "Embroidery" },
];

function verdictStamp(v: LogoOut["verdict"]): StampStatus {
  if (v === "suitable") return "pass";
  if (v === "unsuitable") return "fail";
  return "review";
}

export default function LogoCheckerPage() {
  const { user, loading } = useAuthGuard();
  const [method, setMethod] = useState("unspecified");
  const [result, setResult] = useState<LogoOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-400">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  async function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const logo = await api.checkLogo(file, method);
      setResult(logo);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Check failed");
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <AppShell user={user}>
      <div className="max-w-xl mx-auto p-10">
        <h1 className="text-lg font-bold tracking-tight mb-1">Logo Checker</h1>
        <p className="text-sm text-stone-500 mb-6">
          Upload a logo to get an apparel-printing suitability verdict.
        </p>

        <div className="mb-6">
          <label className="block text-xs uppercase tracking-widest text-stone-400 mb-1">
            Intended print method
          </label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full border border-stone-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500 bg-white"
          >
            {METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.svg"
          className="hidden"
          onChange={onFilePicked}
        />

        <div className="relative border-2 border-dashed border-stone-300 rounded-lg p-10 text-center bg-white">
          <RegMarks />
          {busy ? (
            <Loader2 className="w-8 h-8 text-blue-700 mx-auto mb-3 animate-spin" />
          ) : (
            <Shirt className="w-8 h-8 text-stone-400 mx-auto mb-3" />
          )}
          <p className="text-sm font-medium mb-1">
            {busy ? "Analyzing…" : "Drop a logo to check apparel suitability"}
          </p>
          <p className="text-xs text-stone-500 mb-4">
            SVG, PNG, or JPEG · checks DPI, color count, transparency
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={busy}
            className="bg-stone-900 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
          >
            Choose file
          </button>
        </div>

        {error && <p className="text-sm text-red-700 mt-4">{error}</p>}

        {result && (
          <div className="relative bg-white border border-stone-200 rounded p-6 mt-6">
            <RegMarks />
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-sm font-bold break-all">{result.original_name}</h2>
              <StatusStamp status={verdictStamp(result.verdict)} />
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <p className="text-xs text-stone-400 uppercase tracking-widest mb-1">Type</p>
                <p>{result.is_vector ? "Vector" : "Raster"}</p>
              </div>
              <div>
                <p className="text-xs text-stone-400 uppercase tracking-widest mb-1">DPI</p>
                <p>{result.dpi_value ?? "n/a"}</p>
              </div>
              <div>
                <p className="text-xs text-stone-400 uppercase tracking-widest mb-1">Colors</p>
                <p>{result.color_count ?? "n/a"}</p>
              </div>
              <div>
                <p className="text-xs text-stone-400 uppercase tracking-widest mb-1">Transparency</p>
                <p>{result.has_transparency == null ? "n/a" : result.has_transparency ? "Yes" : "No"}</p>
              </div>
            </div>

            <p className="text-xs uppercase tracking-widest text-stone-400 mb-2">Reasons</p>
            {result.reasons.length === 0 ? (
              <p className="text-sm text-emerald-700 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> No issues found — ready for print.
              </p>
            ) : (
              <ul className="space-y-1.5">
                {result.reasons.map((r) => (
                  <li key={r} className="text-sm text-stone-700 flex items-start gap-2">
                    {result.verdict === "unsuitable" ? (
                      <XCircle className="w-4 h-4 text-red-700 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    )}
                    {r}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
