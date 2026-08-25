"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Upload, ChevronRight, X, Loader2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import RegMarks from "@/components/RegMarks";
import StatusStamp, { type StampStatus } from "@/components/StatusStamp";
import CheckRow from "@/components/CheckRow";
import { useAuthGuard } from "@/lib/useAuth";
import { api, ApiError, type FileWithStatusOut } from "@/lib/api-client";

function fileStamp(f: FileWithStatusOut): StampStatus {
  if (f.job_status === "failed") return "fail";
  if (f.job_status === "queued" || f.job_status === "running" || !f.job_status) return "pending";
  if (f.report?.overall_pass === true) return "pass";
  if (f.report?.overall_pass === false) return "fail";
  return "review";
}

export default function DashboardPage() {
  const { user, loading } = useAuthGuard();
  const router = useRouter();
  const [files, setFiles] = useState<FileWithStatusOut[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listMyFiles();
      setFiles(data);
    } catch {
      // transient — next poll will retry
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user, refresh]);

  useEffect(() => {
    if (!user) return;
    const hasPending = files.some((f) => f.job_status === "queued" || f.job_status === "running");
    if (!hasPending) return;
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [user, files, refresh]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-400">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  const selected = files.find((f) => f.id === selectedId) ?? null;

  async function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const result = await api.uploadFile(file);
      await refresh();
      setSelectedId(result.file_id);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const needAttention = files.filter((f) => f.report?.overall_pass === false).length;

  return (
    <AppShell
      user={user}
      headerRight={
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 bg-stone-900 text-white text-sm px-4 py-2 rounded hover:bg-stone-800 disabled:opacity-50"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? "Uploading…" : "Upload file"}
        </button>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"
        className="hidden"
        onChange={onFilePicked}
      />

      <div className="flex min-h-full">
        <div className="flex-1 overflow-y-auto p-6">
          <h1 className="text-lg font-bold tracking-tight mb-1">Your files</h1>
          <p className="text-sm text-stone-500 mb-6">
            {files.length} file{files.length === 1 ? "" : "s"}
            {needAttention > 0 && ` · ${needAttention} need attention`}
          </p>
          {uploadError && <p className="text-sm text-red-700 mb-4">{uploadError}</p>}

          {files.length === 0 ? (
            <div className="relative border-2 border-dashed border-stone-300 rounded-lg p-16 text-center bg-white">
              <RegMarks />
              <FileText className="w-8 h-8 text-stone-400 mx-auto mb-3" />
              <p className="text-sm font-medium mb-1">No files yet</p>
              <p className="text-xs text-stone-500">Upload a print-ready PDF or image to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {files.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setSelectedId(f.id)}
                  className={`relative text-left bg-white border rounded p-4 hover:border-blue-400 transition-colors ${
                    selected?.id === f.id ? "border-blue-500" : "border-stone-200"
                  }`}
                >
                  <RegMarks />
                  <div className="flex items-start justify-between mb-3">
                    <FileText className="w-5 h-5 text-stone-400" />
                    <StatusStamp status={fileStamp(f)} />
                  </div>
                  <p className="text-sm font-medium truncate mb-1">{f.original_name}</p>
                  <p className="text-xs font-mono text-stone-500">
                    {f.report?.dpi_value ? `${f.report.dpi_value} DPI · ` : ""}
                    {f.report?.page_count ? `${f.report.page_count}pg · ` : ""}
                    {new Date(f.created_at).toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <div className="w-80 shrink-0 border-l border-stone-200 bg-white p-6 overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-stone-400 mb-1">QA Report</p>
                <h2 className="text-sm font-bold break-all">{selected.original_name}</h2>
              </div>
              <button onClick={() => setSelectedId(null)} className="text-stone-400 hover:text-stone-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mb-5">
              <StatusStamp status={fileStamp(selected)} />
            </div>

            {(selected.job_status === "queued" || selected.job_status === "running") && (
              <p className="text-sm text-stone-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Analysis {selected.job_status}…
              </p>
            )}

            {selected.job_status === "failed" && (
              <p className="text-sm text-red-700">Analysis failed. Try re-uploading the file.</p>
            )}

            {selected.report && (
              <>
                <div className="mb-5">
                  <p className="text-xs uppercase tracking-widest text-stone-400 mb-2">Summary</p>
                  <CheckRow
                    label="DPI / Resolution"
                    pass={selected.report.dpi_value ? selected.report.dpi_value >= 300 : null}
                    detail={selected.report.dpi_value ? `${selected.report.dpi_value} dpi` : "n/a"}
                  />
                  <CheckRow
                    label="Pages"
                    pass={null}
                    detail={`${selected.report.page_count ?? "n/a"}`}
                  />
                </div>
                <button
                  onClick={() => router.push(`/dashboard/reports/${selected.report!.id}`)}
                  className="w-full flex items-center justify-center gap-1.5 border border-stone-300 rounded py-2 text-sm hover:bg-stone-50"
                >
                  Full report <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
