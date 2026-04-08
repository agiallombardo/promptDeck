import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  apiAdminAudit,
  apiAdminJobs,
  apiAdminLogs,
  apiAdminPresentations,
  apiAdminStats,
  apiAdminUsers,
} from "../lib/api";
import { useAuthStore } from "../stores/auth";

const CHANNELS = ["", "http", "auth", "audit", "script"] as const;

type Tab = "stats" | "logs" | "jobs" | "presentations" | "users" | "audit";

export default function AdminPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [tab, setTab] = useState<Tab>("stats");
  const [channel, setChannel] = useState<string>("");
  const [requestId, setRequestId] = useState("");
  const [level, setLevel] = useState("");
  const [pathPrefix, setPathPrefix] = useState("");
  const [since, setSince] = useState("");

  const logFilters = useMemo(
    () => ({
      channel: channel || null,
      request_id: requestId || null,
      level: level || null,
      path_prefix: pathPrefix || null,
      since: since || null,
    }),
    [channel, requestId, level, pathPrefix, since],
  );

  const stats = useQuery({
    queryKey: ["admin", "stats", accessToken],
    enabled: Boolean(accessToken) && tab === "stats",
    queryFn: () => apiAdminStats(accessToken!),
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

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "stats", label: "Stats" },
    { id: "logs", label: "Logs" },
    { id: "jobs", label: "Jobs" },
    { id: "presentations", label: "Decks" },
    { id: "users", label: "Users" },
    { id: "audit", label: "Audit" },
  ];

  return (
    <div className="min-h-dvh bg-bg-void px-4 py-10 text-text-main">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-sm text-primary">Admin</p>
            <h1 className="font-heading text-3xl font-semibold">Operations</h1>
            <p className="mt-1 text-sm text-text-muted">
              Jobs, decks, users, security audit trail, aggregates, and request logs (with
              request-ID search).
            </p>
          </div>
          <Link
            to="/"
            className="font-mono text-sm text-text-muted underline decoration-border hover:text-primary"
          >
            Home
          </Link>
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

        {!accessToken ? (
          <p className="mt-10 text-text-muted">
            No session.{" "}
            <Link className="text-primary underline" to="/login">
              Sign in
            </Link>
            .
          </p>
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
                Request ID
                <input
                  className="min-w-0 flex-1 rounded-sharp border border-border bg-bg-recessed px-2 py-1 text-text-main"
                  value={requestId}
                  onChange={(e) => setRequestId(e.target.value)}
                  placeholder="paste from toast"
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
                <table className="w-full min-w-[900px] border-collapse text-left text-sm">
                  <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase tracking-wide text-text-muted">
                    <tr>
                      <th className="px-3 py-2">Time</th>
                      <th className="px-3 py-2">Channel</th>
                      <th className="px-3 py-2">Level</th>
                      <th className="px-3 py-2">Method</th>
                      <th className="px-3 py-2">Path</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Request ID</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border font-mono text-xs text-text-main">
                    {logs.data?.items.map((row) => (
                      <tr key={row.id} className="align-top hover:bg-bg-recessed/60">
                        <td className="whitespace-nowrap px-3 py-2 text-text-muted">{row.ts}</td>
                        <td className="px-3 py-2 text-primary">{row.channel}</td>
                        <td className="px-3 py-2">{row.level}</td>
                        <td className="px-3 py-2">{row.method}</td>
                        <td className="max-w-[220px] truncate px-3 py-2" title={row.path}>
                          {row.path}
                        </td>
                        <td className="px-3 py-2">{row.status_code ?? "—"}</td>
                        <td
                          className="max-w-[160px] truncate px-3 py-2"
                          title={row.request_id ?? ""}
                        >
                          {row.request_id ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          {row.request_id ? (
                            <button
                              type="button"
                              className="text-primary underline"
                              onClick={() => void copyText(row.request_id!)}
                            >
                              Copy
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
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
                  {jobs.data?.items.map((j) => (
                    <tr key={j.id}>
                      <td className="px-3 py-2 text-text-muted">{j.created_at}</td>
                      <td className="px-3 py-2">{j.presentation_title}</td>
                      <td className="px-3 py-2">{j.format}</td>
                      <td className="px-3 py-2">{j.status}</td>
                      <td className="px-3 py-2">{j.progress}%</td>
                    </tr>
                  ))}
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
                  {presentations.data?.items.map((p) => (
                    <tr key={p.id}>
                      <td className="px-3 py-2 text-text-muted">{p.updated_at}</td>
                      <td className="px-3 py-2">{p.title}</td>
                      <td className="px-3 py-2">{p.owner_email}</td>
                      <td className="px-3 py-2">{p.version_count}</td>
                    </tr>
                  ))}
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
                  {users.data?.items.map((u) => (
                    <tr key={u.id}>
                      <td className="px-3 py-2">{u.email}</td>
                      <td className="px-3 py-2">{u.role}</td>
                      <td className="px-3 py-2 text-text-muted">{u.last_login_at ?? "—"}</td>
                      <td className="px-3 py-2 text-text-muted">{u.created_at}</td>
                    </tr>
                  ))}
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
                  {audit.data?.items.map((a) => (
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
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}
