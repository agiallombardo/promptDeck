import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiAuthConfig, apiLogin } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.accessToken);
  const setSession = useAuthStore((s) => s.setSession);
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(searchParams.get("error"));
  const [pending, setPending] = useState(false);
  const [config, setConfig] = useState<Awaited<ReturnType<typeof apiAuthConfig>> | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      navigate("/files", { replace: true });
    }
  }, [navigate, token]);

  useEffect(() => {
    let cancelled = false;
    void apiAuthConfig()
      .then((data) => {
        if (!cancelled) setConfig(data);
      })
      .catch((err) => {
        if (!cancelled) setConfigError(err instanceof Error ? err.message : "Failed to load auth");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const data = await apiLogin(email, password);
      setSession(data.access_token, data.user);
      navigate("/files", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setPending(false);
    }
  }

  const entraHref = config?.entra_login_url ? `${config.entra_login_url}?next=/files` : null;

  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg-void px-[max(1rem,env(safe-area-inset-left))] py-6 text-text-main sm:px-4">
      <div className="w-full max-w-[min(100%,28rem)] rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated sm:p-8">
        <h1 className="font-heading text-[clamp(1.35rem,1.1rem+1vw,1.5rem)] font-semibold">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-text-muted">
          Use your organization account to open and collaborate on decks.
        </p>

        {configError ? (
          <p className="mt-4 text-sm text-accent-warning" role="alert">
            {configError}
          </p>
        ) : null}
        {error ? (
          <p className="mt-4 text-sm text-accent-warning" role="alert">
            {error}
          </p>
        ) : null}

        {config?.entra_enabled && entraHref ? (
          <a
            href={entraHref}
            className="mt-6 inline-flex w-full items-center justify-center rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25"
          >
            Sign in with Microsoft
          </a>
        ) : (
          <p className="mt-6 font-mono text-sm text-text-muted">Loading sign-in options…</p>
        )}

        {config?.local_password_auth_enabled ? (
          <form
            className="mt-8 flex flex-col gap-4 border-t border-border pt-6"
            onSubmit={onSubmit}
          >
            <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
              Local dev sign-in
            </p>
            <label className="flex flex-col gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Email
              <input
                className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(ev) => setEmail(ev.target.value)}
                required
              />
            </label>
            <label className="flex flex-col gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Password
              <input
                className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(ev) => setPassword(ev.target.value)}
                required
              />
            </label>
            <button
              type="submit"
              disabled={pending}
              className="rounded-sharp border border-border px-4 py-2 font-mono text-sm hover:bg-bg-recessed disabled:opacity-50"
            >
              {pending ? "Signing in…" : "Sign in with local account"}
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}
