import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { deckAccessToken } from "../lib/deckAuth";
import { useAuthStore } from "../stores/auth";
import { useShareAccessStore } from "../stores/shareAccess";

export function RequireDeckAccess({
  presentationId,
  children,
}: {
  presentationId: string;
  children: React.ReactNode;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const shareToken = useShareAccessStore((s) => s.token);
  const sharePresentationId = useShareAccessStore((s) => s.presentationId);
  const navigate = useNavigate();
  const token = deckAccessToken(presentationId, accessToken, {
    token: shareToken,
    presentationId: sharePresentationId,
  });

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
    }
  }, [navigate, token]);

  if (!token) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-void font-mono text-sm text-text-muted">
        Redirecting…
      </div>
    );
  }

  return children;
}
