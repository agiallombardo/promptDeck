import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiLogin } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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

  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg-void px-4 text-text-main">
      <div className="w-full max-w-md rounded-sharp border border-border bg-bg-elevated p-8 shadow-elevated">
        <h1 className="font-heading text-2xl font-semibold">Sign in</h1>
        <p className="mt-2 text-sm text-text-muted">PresCollab · local account</p>
        <form className="mt-8 flex flex-col gap-4" onSubmit={onSubmit}>
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
          {error ? (
            <p className="text-sm text-accent-warning" role="alert">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={pending}
            className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
          >
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
