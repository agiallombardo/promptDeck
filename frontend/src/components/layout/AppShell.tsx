import { Link, Outlet, useNavigate } from "react-router-dom";
import { apiLogout } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";

export function AppShell() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);

  async function onSignOut() {
    try {
      await apiLogout();
    } catch {
      /* still clear local session */
    }
    clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-dvh bg-bg-void text-text-main">
      <header className="border-b border-border bg-bg-recessed px-6 py-4">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <Link
            to="/files"
            className="font-mono text-xs uppercase tracking-wide text-primary hover:underline"
          >
            promptDeck
          </Link>
          <nav className="flex flex-wrap items-center gap-4 font-mono text-sm text-text-muted">
            <Link className="hover:text-primary" to="/files">
              Files
            </Link>
            <Link className="hover:text-primary" to="/settings">
              Settings
            </Link>
            {user?.role === "admin" ? (
              <Link className="hover:text-primary" to="/admin">
                Admin
              </Link>
            ) : null}
            <button type="button" className="hover:text-primary" onClick={() => void onSignOut()}>
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
