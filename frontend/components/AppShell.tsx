"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutGrid, Shirt, Shield, LogOut } from "lucide-react";
import BrandMark from "./BrandMark";
import { api, type UserOut } from "@/lib/api-client";

const NAV = [
  { key: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { key: "/dashboard/logo-checker", label: "Logo Checker", icon: Shirt },
];

export default function AppShell({
  user,
  children,
  headerRight,
}: {
  user: UserOut;
  children: React.ReactNode;
  headerRight?: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  const nav = [...NAV, ...(user.role === "admin" ? [{ key: "/admin", label: "Admin", icon: Shield }] : [])];

  return (
    <div className="flex h-screen bg-stone-50 text-stone-900">
      <aside className="w-56 shrink-0 border-r border-stone-200 bg-white flex flex-col">
        <div className="px-5 py-5 border-b border-stone-200">
          <BrandMark />
        </div>
        <nav className="flex-1 py-3">
          {nav.map((n) => {
            const active = pathname === n.key || (n.key !== "/admin" && pathname?.startsWith(n.key + "/"));
            return (
              <Link
                key={n.key}
                href={n.key}
                className={`w-full flex items-center gap-2.5 px-5 py-2.5 text-sm text-left ${
                  active
                    ? "bg-blue-50 text-blue-700 border-r-2 border-blue-700 font-medium"
                    : "text-stone-600 hover:bg-stone-50"
                }`}
              >
                <n.icon className="w-4 h-4" />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-5 py-4 border-t border-stone-200 text-xs text-stone-500">
          <div className="flex items-center justify-between mb-2">
            <span>Signed in as</span>
            <span className="font-mono text-stone-700 truncate max-w-[7rem]" title={user.email}>
              {user.email}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="uppercase tracking-widest text-[10px] text-stone-400">{user.role}</span>
            <button
              onClick={() => {
                api.logout();
                router.replace("/login");
              }}
              className="flex items-center gap-1 text-stone-500 hover:text-red-700"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0">
        {headerRight && (
          <header className="border-b border-stone-200 bg-white px-6 py-4 flex items-center justify-end">
            {headerRight}
          </header>
        )}
        <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}
