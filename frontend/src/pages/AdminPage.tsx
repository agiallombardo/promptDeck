import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  apiAdminAudit,
  apiAdminJobs,
  apiAdminLogs,
  apiAdminPresentations,
  apiAdminSetup,
  apiAdminStats,
  apiAdminUsers,
} from "../lib/api";
import { useAuthStore } from "../stores/auth";

const CHANNELS = ["", "http", "auth", "audit", "script"] as const;

type Tab = "setup" | "stats" | "logs" | "jobs" | "presentations" | "users" | "audit";

export default function AdminPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [tab, setTab] = useState<Tab>("setup");
  const [channel, setChannel] = useState<string>("");
  const [level, setLevel] = useState("");
  const [pathPrefix, setPathPrefix] = useState("");
  const [eventContains, setEventContains] = useState("");
  const [since, setSince] = useState("");

  const logFilters = useMemo(
    () => ({
      channel: channel || null,
      level: level || null,
      path_prefix: pathPrefix || null,
      event_contains: eventContains || null,
      since: since || null,
    }),
    [channel, level, pathPrefix, eventContains, since],
  );

  const stats = useQuery({
    queryKey: ["admin", "stats", accessToken],
    enabled: Boolean(accessToken) && tab === "stats",
    queryFn: () => apiAdminStats(accessToken!),
  });

  const setup = useQuery({
    queryKey: ["admin", "setup", accessToken],
    enabled: Boolean(accessToken) && tab === "setup",
    queryFn: () => apiAdminSetup(accessToken!),
  });

  const logs = useQuery({
    queryKey: ["admin", "logs", accessToken, logFilters],
    enabled: Boolean(accessToken) && tab === "logs",
    queryFn: () => apiAdminLogs(accessToken!, { limit: 100, ...logFilters }),
  });

  const jobs = useQuery({
    queryKey: ["admin", "jobs", accessToken],
    enabled: Boolean(accessToken) && tab === "jobs",
    queryFn: () => apiAdminJobs(accessToken!),
  });

  const presentations = useQuery({
    queryKey: ["admin", "presentations", accessToken],
    enabled: Boolean(accessToken) && tab === "presentations",
    queryFn: () => apiAdminPresentations(accessToken!),
  });

  const users = useQuery({
    queryKey: ["admin", "users", accessToken],
    enabled: Boolean(accessToken) && tab === "users",
    queryFn: () => apiAdminUsers(accessToken!),
  });

  const audit = useQuery({
    queryKey: ["admin", "audit", accessToken],
    enabled: Boolean(accessToken) && tab === "audit",
    queryFn: () => apiAdminAudit(accessToken!),
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: "setup", label: "Setup" },
    { id: "stats", label: "Stats" },
    { id: "logs", label: "Logs" },
    { id: "jobs", label: "Jobs" },
    { id: "presentations", label: "Decks" },
    { id: "users", label: "Users" },
    { id: "audit", label: "Audit" },
  ];

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 text-text-main">
      <header>
        <p className="font-mono text-sm text-primary">Admin</p>
        <h1 className="font-heading text-3xl font-semibold">Operations</h1>
        <p className="mt-1 text-sm text-text-muted">
          Jobs, decks, users, security audit trail, aggregates, and API request logs (event +
          payload from the server). Browser-only errors do not appear here unless you add a client
          reporter.
        </p>
      </header>

      <nav className="mt-8 flex flex-wrap gap-2 border-b border-border pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`rounded-sharp px-3 py-1.5 font-mono text-xs ${
              tab === t.id ? "bg-primary/15 text-primary" : "text-text-muted hover:bg-bg-elevated"
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "setup" ? (
        setup.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : setup.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(setup.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 space-y-5">
            <div className="rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Entra setup checklist
              </p>
              <ul className="mt-3 space-y-2 font-mono text-xs">
                {(
                  [
                    ["ENTRA_ENABLED", setup.data!.entra_enabled],
                    ["ENTRA_TENANT_ID", setup.data!.entra_tenant_id_configured],
                    ["ENTRA_CLIENT_ID", setup.data!.entra_client_id_configured],
                    ["ENTRA_CLIENT_SECRET", setup.data!.entra_client_secret_configured],
                  ] as const
                ).map(([label, ok]) => (
                  <li key={label} className="flex items-center justify-between gap-3">
                    <span className="text-text-muted">{label}</span>
                    <span className={ok ? "text-primary" : "text-accent-warning"}>
                      {ok ? "OK" : "MISSING"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                App values
              </p>
              <dl className="mt-3 grid gap-2 font-mono text-xs">
                <div className="grid gap-1">
                  <dt className="text-text-muted">PUBLIC_APP_URL</dt>
                  <dd className="break-all text-text-main">{setup.data!.public_app_url}</dd>
                </div>
                <div className="grid gap-1">
                  <dt className="text-text-muted">PUBLIC_API_URL</dt>
                  <dd className="break-all text-text-main">{setup.data!.public_api_url}</dd>
                </div>
                <div className="grid gap-1">
                  <dt className="text-text-muted">Redirect URI (register in Entra)</dt>
                  <dd className="break-all text-primary">{setup.data!.entra_redirect_uri}</dd>
                </div>
                <div className="grid gap-1">
                  <dt className="text-text-muted">Local password auth</dt>
                  <dd className="text-text-main">
                    {setup.data!.local_password_auth_enabled ? "Enabled" : "Disabled"}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        )
      ) : tab === "stats" ? (
        stats.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : stats.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(stats.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(
              [
                ["Users", stats.data!.users],
                ["Presentations", stats.data!.presentations],
                ["Versions", stats.data!.versions],
                ["Export jobs", stats.data!.export_jobs],
                ["Audit (24h)", stats.data!.audit_events_24h],
                ["App logs (24h)", stats.data!.app_log_rows_24h],
              ] as const
            ).map(([label, n]) => (
              <div
                key={label}
                className="rounded-sharp border border-border bg-bg-elevated px-4 py-3 shadow-elevated"
              >
                <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                  {label}
                </p>
                <p className="font-heading text-2xl font-semibold tabular-nums">{n}</p>
              </div>
            ))}
          </div>
        )
      ) : tab === "logs" ? (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-text-muted">
            Persisted <span className="font-mono text-text-main">app_logs</span> across channels:{" "}
            <span className="font-mono text-text-main">http</span> (requests),{" "}
            <span className="font-mono text-text-main">auth</span>,{" "}
            <span className="font-mono text-text-main">audit</span> (admin and security-adjacent
            events), and <span className="font-mono text-text-main">script</span> (jobs/smoke).
            Leave channel on <span className="font-mono text-text-main">All</span> for everything.
            Filter by event substring (e.g. <span className="font-mono">login</span>,{" "}
            <span className="font-mono">upload</span>).
          </p>
          <div className="flex flex-wrap gap-3 font-mono text-xs text-text-muted">
            <label className="flex items-center gap-2">
              Channel
              <select
                className="rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
              >
                {CHANNELS.map((c) => (
                  <option key={c || "all"} value={c}>
                    {c === "" ? "All" : c}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2">
              Level
              <input
                className="w-24 rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                placeholder="info"
              />
            </label>
            <label className="flex min-w-[200px] flex-1 items-center gap-2">
              Path prefix
              <input
                className="min-w-0 flex-1 rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                value={pathPrefix}
                onChange={(e) => setPathPrefix(e.target.value)}
                placeholder="/api/v1/admin"
              />
            </label>
            <label className="flex min-w-[160px] flex-1 items-center gap-2">
              Event contains
              <input
                className="min-w-0 flex-1 rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                value={eventContains}
                onChange={(e) => setEventContains(e.target.value)}
                placeholder="auth.login"
              />
            </label>
            <label className="flex min-w-[180px] items-center gap-2">
              Since (ISO)
              <input
                className="min-w-0 flex-1 rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                value={since}
                onChange={(e) => setSince(e.target.value)}
                placeholder="2026-04-01T00:00:00Z"
              />
            </label>
          </div>
          {logs.isLoading ? (
            <p className="font-mono text-sm text-text-muted">Loading…</p>
          ) : logs.isError ? (
            <p className="text-accent-warning" role="alert">
              {(logs.error as Error).message}
            </p>
          ) : (
            <div className="overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase tracking-wide text-text-muted">
                  <tr>
                    <th className="px-3 py-2">Time</th>
                    <th className="px-3 py-2">Channel</th>
                    <th className="px-3 py-2">Level</th>
                    <th className="px-3 py-2">Event</th>
                    <th className="px-3 py-2">Method</th>
                    <th className="px-3 py-2">Path</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="min-w-[200px] px-3 py-2">Payload</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono text-xs text-text-main">
                  {logs.data?.items.length ? (
                    logs.data.items.map((row) => {
                      const payloadStr =
                        row.payload && Object.keys(row.payload).length > 0
                          ? JSON.stringify(row.payload)
                          : "";
                      const payloadPreview =
                        payloadStr.length > 160 ? `${payloadStr.slice(0, 160)}…` : payloadStr;
                      return (
                        <tr key={row.id} className="align-top hover:bg-bg-recessed/60">
                          <td className="whitespace-nowrap px-3 py-2 text-text-muted">{row.ts}</td>
                          <td className="px-3 py-2 text-primary">{row.channel}</td>
                          <td className="px-3 py-2">{row.level}</td>
                          <td
                            className="max-w-[180px] truncate px-3 py-2 text-text-muted"
                            title={row.event ?? ""}
                          >
                            {row.event ?? "—"}
                          </td>
                          <td className="px-3 py-2">{row.method || "—"}</td>
                          <td className="max-w-[200px] truncate px-3 py-2" title={row.path}>
                            {row.path || "—"}
                          </td>
                          <td className="px-3 py-2">{row.status_code ?? "—"}</td>
                          <td
                            className="max-w-[min(40vw,28rem)] break-all px-3 py-2 text-text-muted"
                            title={payloadStr || undefined}
                          >
                            {payloadPreview || "—"}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td className="px-3 py-6 text-text-muted" colSpan={8}>
                        No log rows match the current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : tab === "jobs" ? (
        jobs.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : jobs.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(jobs.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
            <table className="w-full min-w-[800px] border-collapse text-left text-sm">
              <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase text-text-muted">
                <tr>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Deck</th>
                  <th className="px-3 py-2">Format</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Progress</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs">
                {jobs.data?.items.length ? (
                  jobs.data.items.map((j) => (
                    <tr key={j.id}>
                      <td className="px-3 py-2 text-text-muted">{j.created_at}</td>
                      <td className="px-3 py-2">{j.presentation_title}</td>
                      <td className="px-3 py-2">{j.format}</td>
                      <td className="px-3 py-2">{j.status}</td>
                      <td className="px-3 py-2">{j.progress}%</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-text-muted" colSpan={5}>
                      No export jobs yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )
      ) : tab === "presentations" ? (
        presentations.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : presentations.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(presentations.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
            <table className="w-full min-w-[800px] border-collapse text-left text-sm">
              <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase text-text-muted">
                <tr>
                  <th className="px-3 py-2">Updated</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Owner</th>
                  <th className="px-3 py-2">Versions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs">
                {presentations.data?.items.length ? (
                  presentations.data.items.map((p) => (
                    <tr key={p.id}>
                      <td className="px-3 py-2 text-text-muted">{p.updated_at}</td>
                      <td className="px-3 py-2">{p.title}</td>
                      <td className="px-3 py-2">{p.owner_email}</td>
                      <td className="px-3 py-2">{p.version_count}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-text-muted" colSpan={4}>
                      No presentations.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )
      ) : tab === "users" ? (
        users.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : users.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(users.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase text-text-muted">
                <tr>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Last login</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs">
                {users.data?.items.length ? (
                  users.data.items.map((u) => (
                    <tr key={u.id}>
                      <td className="px-3 py-2">{u.email}</td>
                      <td className="px-3 py-2">{u.role}</td>
                      <td className="px-3 py-2 text-text-muted">{u.last_login_at ?? "—"}</td>
                      <td className="px-3 py-2 text-text-muted">{u.created_at}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-text-muted" colSpan={4}>
                      No users.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )
      ) : tab === "audit" ? (
        audit.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : audit.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(audit.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
            <table className="w-full min-w-[900px] border-collapse text-left text-sm">
              <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase text-text-muted">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Action</th>
                  <th className="px-3 py-2">Actor</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs">
                {audit.data?.items.length ? (
                  audit.data.items.map((a) => (
                    <tr key={a.id}>
                      <td className="whitespace-nowrap px-3 py-2 text-text-muted">{a.ts}</td>
                      <td className="px-3 py-2">{a.action}</td>
                      <td className="max-w-[120px] truncate px-3 py-2" title={a.actor_id ?? ""}>
                        {a.actor_id ?? "—"}
                      </td>
                      <td className="max-w-[200px] truncate px-3 py-2">
                        {a.target_kind ?? "—"} {a.target_id ?? ""}
                      </td>
                      <td className="px-3 py-2">{a.ip ?? "—"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-text-muted" colSpan={5}>
                      No audit events yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </main>
  );
}
