"use client";

import { useEffect, useState } from "react";
import { Loader2, Shield, UserX, UserCheck } from "lucide-react";
import AppShell from "@/components/AppShell";
import RegMarks from "@/components/RegMarks";
import { useAuthGuard } from "@/lib/useAuth";
import { api, ApiError, type UserOut, type ThresholdsOut, type AuditLogOut } from "@/lib/api-client";

export default function AdminPage() {
  const { user, loading } = useAuthGuard(true);
  const [users, setUsers] = useState<UserOut[]>([]);
  const [thresholds, setThresholds] = useState<ThresholdsOut | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingThresholds, setSavingThresholds] = useState(false);

  async function refreshAll() {
    try {
      const [u, t, a] = await Promise.all([api.listUsers(), api.getThresholds(), api.listAuditLog()]);
      setUsers(u);
      setThresholds(t);
      setAuditLog(a);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load admin data");
    }
  }

  useEffect(() => {
    if (user) refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-400">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  async function toggleRole(target: UserOut) {
    try {
      await api.setUserRole(target.id, target.role === "admin" ? "user" : "admin");
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update role");
    }
  }

  async function toggleActive(target: UserOut) {
    try {
      if (target.is_active) await api.deactivateUser(target.id);
      else await api.reactivateUser(target.id);
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update user");
    }
  }

  async function onSaveThresholds(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!thresholds) return;
    setSavingThresholds(true);
    try {
      const updated = await api.updateThresholds({
        min_dpi: thresholds.min_dpi,
        min_bleed_mm: thresholds.min_bleed_mm,
        require_crop_marks: thresholds.require_crop_marks,
      });
      setThresholds(updated);
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save thresholds");
    } finally {
      setSavingThresholds(false);
    }
  }

  return (
    <AppShell user={user}>
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        <div>
          <h1 className="text-lg font-bold tracking-tight mb-1 flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-700" /> Admin
          </h1>
          <p className="text-sm text-stone-500">Full control over users, thresholds, and the audit trail.</p>
        </div>

        {error && <p className="text-sm text-red-700">{error}</p>}

        {/* Users */}
        <section className="relative bg-white border border-stone-200 rounded p-6">
          <RegMarks />
          <p className="text-xs uppercase tracking-widest text-stone-400 mb-4">Users</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-widest text-stone-400 border-b border-stone-200">
                  <th className="py-2 pr-4">Email</th>
                  <th className="py-2 pr-4">Role</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Joined</th>
                  <th className="py-2 pr-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-stone-100 last:border-0">
                    <td className="py-2 pr-4">{u.email}</td>
                    <td className="py-2 pr-4">
                      <span className="font-mono text-xs">{u.role}</span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={u.is_active ? "text-emerald-700" : "text-red-700"}>
                        {u.is_active ? "active" : "deactivated"}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-stone-500">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => toggleRole(u)}
                          disabled={u.id === user.id}
                          className="text-blue-700 underline decoration-dotted text-xs disabled:opacity-40 disabled:no-underline"
                        >
                          Make {u.role === "admin" ? "user" : "admin"}
                        </button>
                        <button
                          onClick={() => toggleActive(u)}
                          disabled={u.id === user.id}
                          className="flex items-center gap-1 text-xs text-stone-500 hover:text-stone-800 disabled:opacity-40"
                        >
                          {u.is_active ? (
                            <>
                              <UserX className="w-3.5 h-3.5" /> Deactivate
                            </>
                          ) : (
                            <>
                              <UserCheck className="w-3.5 h-3.5" /> Reactivate
                            </>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Thresholds */}
        <section className="relative bg-white border border-stone-200 rounded p-6 max-w-md">
          <RegMarks />
          <p className="text-xs uppercase tracking-widest text-stone-400 mb-4">Org QA thresholds</p>
          {thresholds && (
            <form onSubmit={onSaveThresholds} className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Minimum DPI</span>
                <input
                  type="number"
                  value={thresholds.min_dpi}
                  onChange={(e) => setThresholds({ ...thresholds, min_dpi: Number(e.target.value) })}
                  className="w-24 text-right font-mono text-sm border border-stone-300 rounded px-2 py-1"
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Minimum bleed (mm)</span>
                <input
                  type="number"
                  step="0.1"
                  value={thresholds.min_bleed_mm}
                  onChange={(e) => setThresholds({ ...thresholds, min_bleed_mm: Number(e.target.value) })}
                  className="w-24 text-right font-mono text-sm border border-stone-300 rounded px-2 py-1"
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Require crop marks</span>
                <input
                  type="checkbox"
                  checked={thresholds.require_crop_marks}
                  onChange={(e) => setThresholds({ ...thresholds, require_crop_marks: e.target.checked })}
                  className="w-4 h-4"
                />
              </div>
              <button
                type="submit"
                disabled={savingThresholds}
                className="w-full bg-blue-700 text-white text-sm py-2 rounded hover:bg-blue-800 disabled:opacity-50"
              >
                {savingThresholds ? "Saving…" : "Save thresholds"}
              </button>
            </form>
          )}
        </section>

        {/* Audit log */}
        <section className="relative bg-white border border-stone-200 rounded p-6">
          <RegMarks />
          <p className="text-xs uppercase tracking-widest text-stone-400 mb-4">Audit log</p>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {auditLog.length === 0 && <p className="text-sm text-stone-400">No admin actions yet.</p>}
            {auditLog.map((entry) => (
              <div key={entry.id} className="text-sm border-b border-stone-100 pb-2 last:border-0">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-blue-700">{entry.action}</span>
                  <span className="text-xs text-stone-400">
                    {new Date(entry.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-stone-500">
                  {entry.target_type}
                  {entry.target_id ? ` · ${entry.target_id}` : ""}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
