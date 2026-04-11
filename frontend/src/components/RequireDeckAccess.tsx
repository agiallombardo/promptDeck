import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export function RequireDeckAccess({
  children,
}: {
  presentationId: string;
  children: React.ReactNode;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const shareToken = searchParams.get("share");

  useEffect(() => {
    if (!accessToken && !shareToken) {
      navigate("/login", { replace: true });
    }
  }, [accessToken, navigate, shareToken]);

  if (!accessToken && !shareToken) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-void font-mono text-sm text-text-muted">
        Redirecting…
      </div>
    );
  }

  return children;
}
