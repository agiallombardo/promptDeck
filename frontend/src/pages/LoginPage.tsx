import { useCallback, useEffect, useState } from "react";
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
  const [configLoading, setConfigLoading] = useState(true);

  const loadAuthConfig = useCallback(async () => {
    setConfigError(null);
    setConfigLoading(true);
    try {
      const data = await apiAuthConfig();
      setConfig(data);
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Failed to load auth");
    } finally {
      setConfigLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      navigate("/files", { replace: true });
    }
  }, [navigate, token]);

  useEffect(() => {
    void loadAuthConfig();
  }, [loadAuthConfig]);

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
          <div className="mt-4 space-y-2">
            <p className="text-sm text-accent-warning" role="alert">
              {configError}
            </p>
            <button
              type="button"
              className="rounded-sharp border border-border px-3 py-1 font-mono text-xs hover:bg-bg-recessed disabled:opacity-50"
              disabled={configLoading}
              onClick={() => void loadAuthConfig()}
            >
              {configLoading ? "Retrying…" : "Retry loading sign-in options"}
            </button>
          </div>
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
        ) : config && !config.entra_enabled ? null : configLoading ? (
          <p className="mt-6 font-mono text-sm text-text-muted">Loading sign-in options…</p>
        ) : null}

        {(config?.local_password_auth_enabled ?? true) || configError ? (
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

        {configError && !(config?.local_password_auth_enabled ?? true) ? (
          <p className="mt-4 text-xs text-text-muted">
            If local sign-in is enabled on the server, you can still try the form above; otherwise
            fix the network issue and refresh the page.
          </p>
        ) : null}
      </div>
    </div>
  );
}
