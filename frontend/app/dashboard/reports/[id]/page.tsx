"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Download, Loader2, CheckCircle2, XCircle } from "lucide-react";
import AppShell from "@/components/AppShell";
import RegMarks from "@/components/RegMarks";
import StatusStamp from "@/components/StatusStamp";
import CheckRow from "@/components/CheckRow";
import { useAuthGuard } from "@/lib/useAuth";
import { api, ApiError, type ReportOut } from "@/lib/api-client";

export default function ReportDetailPage() {
  const { user, loading } = useAuthGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<ReportOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .getReport(params.id)
      .then(setReport)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load report"));
  }, [user, params.id]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-400">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  async function downloadPdf() {
    if (!report) return;
    setDownloading(true);
    try {
      const { url } = await api.getReportPdfUrl(report.id);
      window.open(url, "_blank");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not fetch PDF");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <AppShell user={user}>
      <div className="max-w-3xl mx-auto p-6">
        <button
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-800 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </button>

        {error && <p className="text-sm text-red-700 mb-4">{error}</p>}

        {!report && !error && (
          <div className="flex items-center gap-2 text-stone-400">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading report…
          </div>
        )}

        {report && (
          <>
            <div className="relative bg-white border border-stone-200 rounded p-6 mb-6">
              <RegMarks />
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs uppercase tracking-widest text-stone-400 mb-1">QA Report</p>
                  <h1 className="text-lg font-bold tracking-tight">
                    {report.file_format} · {report.page_count} page{report.page_count === 1 ? "" : "s"}
                  </h1>
                </div>
                <StatusStamp status={report.overall_pass ? "pass" : "fail"} />
              </div>
              <button
                onClick={downloadPdf}
                disabled={downloading}
                className="flex items-center gap-2 border border-stone-300 rounded px-4 py-2 text-sm hover:bg-stone-50 disabled:opacity-50"
              >
                {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Download PDF report
              </button>
            </div>

            <div className="relative bg-white border border-stone-200 rounded p-6 mb-6">
              <RegMarks />
              <p className="text-xs uppercase tracking-widest text-stone-400 mb-3">Checklist</p>
              <CheckRow
                label="DPI / Resolution"
                pass={report.dpi_pass}
                detail={report.dpi_value != null ? `${report.dpi_value} dpi` : "n/a"}
              />
              <CheckRow
                label="Crop marks"
                pass={report.crop_marks_pass}
                detail={report.crop_marks_present ? "present" : "missing"}
              />
              <CheckRow
                label="Bleed"
                pass={report.bleed_pass}
                detail={report.bleed_margin_mm != null ? `${report.bleed_margin_mm}mm` : "n/a"}
              />
              <CheckRow
                label="White edges"
                pass={report.white_edges_pass}
                detail={report.white_edges_detected ? "detected" : "none"}
              />
              <CheckRow
                label="Color mode"
                pass={null}
                detail={report.color_mode ?? "n/a"}
              />
              <p className="text-xs text-stone-400 mt-4">{report.multi_page_note}</p>
            </div>

            <div className="relative bg-white border border-stone-200 rounded p-6 mb-6">
              <RegMarks />
              <p className="text-xs uppercase tracking-widest text-stone-400 mb-3">Fonts</p>
              {report.fonts.length === 0 ? (
                <p className="text-sm text-stone-500">No fonts detected (image file or vector-only page).</p>
              ) : (
                <div className="space-y-1.5">
                  {report.fonts.map((f) => (
                    <div key={f.name} className="flex items-center justify-between text-sm">
                      <span className="text-stone-700">{f.name}</span>
                      <span
                        className={`flex items-center gap-1.5 text-xs font-mono ${
                          f.embedded ? "text-emerald-700" : "text-red-700 font-semibold"
                        }`}
                      >
                        {f.embedded ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        {f.embedded ? "embedded" : "NOT EMBEDDED"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="relative bg-white border border-stone-200 rounded p-6">
              <RegMarks />
              <p className="text-xs uppercase tracking-widest text-stone-400 mb-3">
                Dominant colors — closest color reference
              </p>
              <p className="text-[11px] text-stone-400 mb-4">
                Open Delta-E approximation, not licensed Pantone® data.
              </p>
              <div className="space-y-3">
                {report.color_palette.map((entry) => {
                  const match = report.pantone_matches.find((m) => m.source_hex === entry.hex);
                  return (
                    <div key={entry.hex} className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded border border-stone-200 shrink-0"
                        style={{ backgroundColor: entry.hex }}
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-mono">
                          {entry.hex} · {entry.coverage_pct}% coverage
                        </p>
                        {match && (
                          <p className="text-xs text-stone-500 truncate">
                            {match.reference_label} (ΔE {match.delta_e})
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
