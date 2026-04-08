import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiShareExchange } from "../lib/api";
import { useShareAccessStore } from "../stores/shareAccess";

export default function ShareEntryPage() {
  const { token: secret } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const setShare = useShareAccessStore((s) => s.setShare);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!secret) {
      setError("Missing link");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const out = await apiShareExchange(secret);
        if (cancelled) return;
        setShare(out.access_token, out.presentation_id, out.role);
        navigate(`/p/${out.presentation_id}`, { replace: true });
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Invalid or expired link");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [secret, navigate, setShare]);

  if (error) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-bg-void px-4 text-center">
        <p className="font-mono text-sm text-accent-warning">{error}</p>
        <button
          type="button"
          className="rounded-sharp border border-border px-4 py-2 font-mono text-xs hover:bg-bg-elevated"
          onClick={() => navigate("/login", { replace: true })}
        >
          Go to login
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg-void font-mono text-sm text-text-muted">
      Opening shared deck…
    </div>
  );
}
