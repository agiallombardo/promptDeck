import { useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { apiLogout } from "../lib/api";
import { useAuthStore } from "../stores/auth";

const IDLE_SIGN_OUT_MS = 4 * 60 * 60 * 1000;

const ACTIVITY_EVENTS = [
  "mousedown",
  "mousemove",
  "keydown",
  "scroll",
  "touchstart",
  "click",
  "wheel",
] as const;

/**
 * After this long without user input, calls logout and clears client state.
 */
export function IdleSessionWatcher({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!accessToken) return;

    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const arm = () => {
      if (timeoutId != null) window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        void (async () => {
          try {
            await apiLogout();
          } catch {
            /* still clear local session */
          }
          queryClient.clear();
          clear();
          navigate("/login", { replace: true });
        })();
      }, IDLE_SIGN_OUT_MS);
    };

    arm();
    const onActivity = () => {
      arm();
    };

    for (const ev of ACTIVITY_EVENTS) {
      window.addEventListener(ev, onActivity, { passive: true });
    }
    return () => {
      if (timeoutId != null) window.clearTimeout(timeoutId);
      for (const ev of ACTIVITY_EVENTS) {
        window.removeEventListener(ev, onActivity);
      }
    };
  }, [accessToken, clear, navigate, queryClient]);

  return children;
}
