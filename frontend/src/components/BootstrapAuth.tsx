import { useEffect, useState } from "react";
import { apiRefresh } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export function BootstrapAuth({ children }: { children: React.ReactNode }) {
  const setSession = useAuthStore((s) => s.setSession);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const data = await apiRefresh();
      if (!cancelled && data?.access_token && data.user) {
        setSession(data.access_token, data.user);
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [setSession]);

  if (!ready) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-void font-mono text-sm text-text-muted">
        Loading…
      </div>
    );
  }
  return children;
}
