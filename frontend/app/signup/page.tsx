"use client";

import { useState, useEffect, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import RegMarks from "@/components/RegMarks";
import BrandMark from "@/components/BrandMark";
import { api, ApiError, isAuthenticated } from "@/lib/api-client";

export default function SignupPage() {
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) router.replace("/dashboard");
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.signup(email, password, orgName, fullName || undefined);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="flex justify-center mb-8">
          <BrandMark size="lg" />
        </div>
        <div className="relative bg-white border border-stone-200 rounded p-8">
          <RegMarks />
          <h1 className="text-lg font-bold tracking-tight mb-1">Create your account</h1>
          <p className="text-sm text-stone-500 mb-6">
            The first person on a new team becomes its admin.
          </p>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-widest text-stone-400 mb-1">
                Organization name
              </label>
              <input
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full border border-stone-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-stone-400 mb-1">
                Full name
              </label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full border border-stone-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-stone-400 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-stone-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-stone-400 mb-1">
                Password
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-stone-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>
            {error && <p className="text-sm text-red-700">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full bg-blue-700 text-white text-sm py-2 rounded hover:bg-blue-800 disabled:opacity-50"
            >
              {busy ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="text-sm text-stone-500 mt-6 text-center">
            Already have an account?{" "}
            <Link href="/login" className="text-blue-700 underline decoration-dotted">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
