"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, isAuthenticated, type UserOut } from "./api-client";

/** Redirects to /login if not authenticated; loads the current user. */
export function useAuthGuard(requireAdmin = false) {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    api
      .me()
      .then((u) => {
        if (cancelled) return;
        if (requireAdmin && u.role !== "admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { user, loading };
}
