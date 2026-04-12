import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  apiAdminAudit,
  apiAdminEntraGet,
  apiAdminEntraPatch,
  apiAdminDeckPromptJobs,
  apiAdminJobs,
  apiAdminLogs,
  apiAdminLlmGet,
  apiAdminLlmPatch,
  apiAdminPresentations,
  apiAdminSetup,
  apiAdminSmtpGet,
  apiAdminSmtpPatch,
  apiAdminSmtpTest,
  apiAdminStats,
  apiAdminUsers,
  type AdminEntraSettingsDto,
  type AdminLlmSettings,
  type AdminSmtpSettings,
} from "../lib/api";
import type { components } from "../lib/api/schema";
import { useAuthStore } from "../stores/auth";

const CHANNELS = ["", "http", "auth", "audit", "script"] as const;

type Tab =
  | "setup"
  | "identity"
  | "email"
  | "llm"
  | "stats"
  | "logs"
  | "jobs"
  | "presentations"
  | "users"
  | "audit";

export default function AdminPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
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

  const deckPromptJobs = useQuery({
    queryKey: ["admin", "deck-prompt-jobs", accessToken],
    enabled: Boolean(accessToken) && tab === "jobs",
    queryFn: () => apiAdminDeckPromptJobs(accessToken!),
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

  const entra = useQuery({
    queryKey: ["admin", "entra", accessToken],
    enabled: Boolean(accessToken) && tab === "identity",
    queryFn: () => apiAdminEntraGet(accessToken!),
  });

  const entraPatch = useMutation({
    mutationFn: (body: Parameters<typeof apiAdminEntraPatch>[1]) =>
      apiAdminEntraPatch(accessToken!, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "entra", accessToken] });
      await qc.invalidateQueries({ queryKey: ["admin", "setup", accessToken] });
    },
  });

  const smtp = useQuery({
    queryKey: ["admin", "smtp", accessToken],
    enabled: Boolean(accessToken) && tab === "email",
    queryFn: () => apiAdminSmtpGet(accessToken!),
  });

  const smtpPatch = useMutation({
    mutationFn: (body: Parameters<typeof apiAdminSmtpPatch>[1]) =>
      apiAdminSmtpPatch(accessToken!, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "smtp", accessToken] });
      await qc.invalidateQueries({ queryKey: ["admin", "setup", accessToken] });
    },
  });

  const smtpTest = useMutation({
    mutationFn: (to?: string | null) => apiAdminSmtpTest(accessToken!, to),
  });

  const llm = useQuery({
    queryKey: ["admin", "llm", accessToken],
    enabled: Boolean(accessToken) && tab === "llm",
    queryFn: () => apiAdminLlmGet(accessToken!),
  });

  const llmPatch = useMutation({
    mutationFn: (body: components["schemas"]["AdminLlmSettingsPatch"]) =>
      apiAdminLlmPatch(accessToken!, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "llm", accessToken] });
    },
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: "setup", label: "Setup" },
    { id: "identity", label: "Identity / Entra" },
    { id: "email", label: "Email / SMTP" },
    { id: "llm", label: "LLM / LiteLLM" },
    { id: "stats", label: "Stats" },
    { id: "logs", label: "Logs" },
    { id: "jobs", label: "Jobs" },
    { id: "presentations", label: "Decks" },
    { id: "users", label: "Users" },
    { id: "audit", label: "Audit" },
  ];

  return (
    <main className="mx-auto w-full max-w-[min(100%,72rem)] px-3 py-8 text-text-main sm:px-4 sm:py-10">
      <header>
        <p className="font-mono text-sm text-primary">Admin</p>
        <h1 className="font-heading text-[clamp(1.5rem,1.2rem+1.4vw,1.875rem)] font-semibold">
          Operations
        </h1>
      </header>

      <nav className="mt-6 flex flex-wrap gap-1.5 border-b border-border pb-2 sm:mt-8 sm:gap-2">
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
                    ["OIDC login ready", setup.data!.entra_login_ready],
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

            <div className="rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Outbound email (SMTP)
              </p>
              <ul className="mt-3 space-y-2 font-mono text-xs">
                <li className="flex items-center justify-between gap-3">
                  <span className="text-text-muted">SMTP enabled</span>
                  <span className={setup.data!.smtp_enabled ? "text-primary" : "text-text-muted"}>
                    {setup.data!.smtp_enabled ? "Yes" : "No"}
                  </span>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span className="text-text-muted">Ready to send</span>
                  <span className={setup.data!.smtp_ready ? "text-primary" : "text-accent-warning"}>
                    {setup.data!.smtp_ready ? "OK" : "Incomplete"}
                  </span>
                </li>
              </ul>
              <p className="mt-3 text-xs text-text-muted">
                Configure relay on the{" "}
                <span className="font-mono text-text-main">Email / SMTP</span> tab (e.g. Microsoft
                365: <span className="font-mono text-text-main">smtp.office365.com</span>, port{" "}
                <span className="font-mono text-text-main">587</span>, STARTTLS on).
              </p>
            </div>
          </div>
        )
      ) : tab === "identity" ? (
        <AdminEntraPanel entra={entra} entraPatch={entraPatch} />
      ) : tab === "email" ? (
        <AdminSmtpPanel smtp={smtp} smtpPatch={smtpPatch} smtpTest={smtpTest} />
      ) : tab === "llm" ? (
        <AdminLlmPanel llm={llm} llmPatch={llmPatch} />
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
                ["Deck prompt jobs", stats.data!.deck_prompt_jobs],
                ["Deck prompt jobs (24h)", stats.data!.deck_prompt_jobs_24h],
                ["LLM prompt tokens (24h)", stats.data!.llm_prompt_tokens_24h],
                ["LLM completion tokens (24h)", stats.data!.llm_completion_tokens_24h],
                ["LLM total tokens (24h)", stats.data!.llm_total_tokens_24h],
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
        jobs.isLoading || deckPromptJobs.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : jobs.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(jobs.error as Error).message}
          </p>
        ) : deckPromptJobs.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(deckPromptJobs.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 space-y-10">
            <div>
              <h3 className="font-heading text-sm font-semibold text-text-main">Export jobs</h3>
              <div className="mt-3 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
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
            </div>
            <div>
              <h3 className="font-heading text-sm font-semibold text-text-main">
                Deck prompt (LLM) jobs
              </h3>
              <p className="mt-1 text-xs text-text-muted">
                Token counts are recorded when the provider returns usage in the chat completion
                response. Summaries for the last 24 hours appear on the Stats tab.
              </p>
              <div className="mt-3 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
                <table className="w-full min-w-[1040px] border-collapse text-left text-sm">
                  <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase text-text-muted">
                    <tr>
                      <th className="px-3 py-2">Created</th>
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Deck</th>
                      <th className="px-3 py-2">Prompt preview</th>
                      <th className="px-3 py-2">Model</th>
                      <th className="px-3 py-2">Tokens (p/c/t)</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">By</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border font-mono text-xs">
                    {deckPromptJobs.data?.items.length ? (
                      deckPromptJobs.data.items.map((j) => (
                        <tr key={j.id}>
                          <td className="px-3 py-2 text-text-muted">{j.created_at}</td>
                          <td className="px-3 py-2">
                            <span
                              className={
                                j.is_generation
                                  ? "rounded-sharp border border-primary/40 bg-primary/10 px-2 py-0.5 text-primary"
                                  : "rounded-sharp border border-border bg-bg-recessed px-2 py-0.5 text-text-muted"
                              }
                            >
                              {j.is_generation ? "Generate" : "Edit"}
                            </span>
                          </td>
                          <td className="px-3 py-2">{j.presentation_title}</td>
                          <td
                            className="max-w-[14rem] truncate px-3 py-2 text-text-muted"
                            title={j.prompt_preview || undefined}
                          >
                            {j.prompt_preview || "—"}
                          </td>
                          <td className="px-3 py-2">{j.llm_model ?? "—"}</td>
                          <td className="px-3 py-2 tabular-nums">
                            {j.prompt_tokens != null ||
                            j.completion_tokens != null ||
                            j.total_tokens != null
                              ? `${j.prompt_tokens ?? "—"} / ${j.completion_tokens ?? "—"} / ${j.total_tokens ?? "—"}`
                              : "—"}
                          </td>
                          <td className="px-3 py-2">{j.status}</td>
                          <td className="px-3 py-2">{j.creator_email}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td className="px-3 py-6 text-text-muted" colSpan={8}>
                          No deck prompt jobs yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
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
                      <td className="max-w-[min(100%,280px)] px-3 py-2">
                        {a.actor_email ? (
                          <div className="space-y-0.5">
                            <p
                              className="truncate font-mono text-[11px] text-text-main"
                              title={a.actor_email}
                            >
                              {a.actor_email}
                            </p>
                            {a.actor_display_name ? (
                              <p
                                className="truncate text-[10px] text-text-muted"
                                title={a.actor_display_name}
                              >
                                {a.actor_display_name}
                              </p>
                            ) : null}
                            {a.actor_id ? (
                              <p
                                className="truncate font-mono text-[10px] text-text-muted"
                                title={a.actor_id}
                              >
                                {a.actor_id}
                              </p>
                            ) : null}
                          </div>
                        ) : a.actor_id ? (
                          <span
                            className="font-mono text-[10px] text-text-muted"
                            title={a.actor_id}
                          >
                            {a.actor_id}
                          </span>
                        ) : (
                          "—"
                        )}
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

function AdminEntraPanel({
  entra,
  entraPatch,
}: {
  entra: UseQueryResult<AdminEntraSettingsDto, Error>;
  entraPatch: UseMutationResult<
    AdminEntraSettingsDto,
    Error,
    Parameters<typeof apiAdminEntraPatch>[1]
  >;
}) {
  const [enabled, setEnabled] = useState(false);
  const [tenantId, setTenantId] = useState("");
  const [clientId, setClientId] = useState("");
  const [authorityHost, setAuthorityHost] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [clearSecret, setClearSecret] = useState(false);

  useEffect(() => {
    if (!entra.data) return;
    setEnabled(entra.data.entra_enabled);
    setTenantId(entra.data.entra_tenant_id ?? "");
    setClientId(entra.data.entra_client_id ?? "");
    setAuthorityHost(entra.data.entra_authority_host ?? "");
    setClientSecret("");
    setClearSecret(false);
  }, [entra.data]);

  const fieldClass =
    "w-full rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-mono text-sm text-text-main outline-none ring-primary focus:ring-1";

  if (entra.isLoading) {
    return <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>;
  }
  if (entra.isError) {
    return (
      <p className="mt-10 text-accent-warning" role="alert">
        {(entra.error as Error).message}
      </p>
    );
  }

  return (
    <div className="mt-8 max-w-xl space-y-6">
      <p className="text-sm text-text-muted">
        Values here are stored in the database and merged with environment variables (env wins when
        set). Use the redirect URI below when registering the app in Microsoft Entra. See also{" "}
        <span className="font-mono text-text-main">scripts/azure-entra-app-registration.sh</span>.
      </p>

      <form
        className="space-y-4 rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated"
        onSubmit={(e) => {
          e.preventDefault();
          entraPatch.mutate({
            entra_enabled: enabled,
            entra_tenant_id: tenantId.trim() || null,
            entra_client_id: clientId.trim() || null,
            entra_authority_host: authorityHost.trim() || null,
            entra_client_secret: clientSecret.trim() || null,
            clear_entra_client_secret: clearSecret,
          });
        }}
      >
        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enable Microsoft Entra (OIDC) login
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Tenant ID</span>
          <input
            className={fieldClass}
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          />
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Application (client) ID</span>
          <input
            className={fieldClass}
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder="Client ID from app registration"
          />
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Authority host</span>
          <input
            className={fieldClass}
            value={authorityHost}
            onChange={(e) => setAuthorityHost(e.target.value)}
            placeholder="https://login.microsoftonline.com"
          />
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Client secret (write-only)</span>
          <input
            className={fieldClass}
            type="password"
            autoComplete="off"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            placeholder={
              entra.data?.entra_client_secret_configured
                ? "Leave blank to keep existing secret"
                : "Paste client secret"
            }
          />
        </label>

        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
          <input
            type="checkbox"
            checked={clearSecret}
            onChange={(e) => setClearSecret(e.target.checked)}
          />
          Remove stored client secret
        </label>

        <div className="rounded-sharp border border-border bg-bg-recessed p-3 font-mono text-xs">
          <p className="text-text-muted">Redirect URI (register in Entra)</p>
          <p className="mt-1 break-all text-primary">{entra.data?.entra_redirect_uri}</p>
          <p className="mt-2 text-text-muted">Public API URL</p>
          <p className="mt-1 break-all text-text-main">{entra.data?.public_api_url}</p>
        </div>

        <button
          type="submit"
          className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-xs text-primary ring-1 ring-primary/40 disabled:opacity-50"
          disabled={entraPatch.isPending}
        >
          {entraPatch.isPending ? "Saving…" : "Save Entra settings"}
        </button>
      </form>
    </div>
  );
}

function AdminSmtpPanel({
  smtp,
  smtpPatch,
  smtpTest,
}: {
  smtp: UseQueryResult<AdminSmtpSettings, Error>;
  smtpPatch: UseMutationResult<AdminSmtpSettings, Error, Parameters<typeof apiAdminSmtpPatch>[1]>;
  smtpTest: UseMutationResult<{ ok: boolean; to: string }, Error, string | null | undefined>;
}) {
  const [enabled, setEnabled] = useState(false);
  const [host, setHost] = useState("");
  const [port, setPort] = useState("587");
  const [username, setUsername] = useState("");
  const [from, setFrom] = useState("");
  const [starttls, setStarttls] = useState(true);
  const [implicitTls, setImplicitTls] = useState(false);
  const [validateCerts, setValidateCerts] = useState(true);
  const [authMode, setAuthMode] = useState<"login" | "none">("login");
  const [password, setPassword] = useState("");
  const [clearPassword, setClearPassword] = useState(false);
  const [testTo, setTestTo] = useState("");

  useEffect(() => {
    if (!smtp.data) {
      return;
    }
    setEnabled(smtp.data.smtp_enabled);
    setHost(smtp.data.smtp_host ?? "");
    setPort(String(smtp.data.smtp_port));
    setUsername(smtp.data.smtp_username ?? "");
    setFrom(smtp.data.smtp_from ?? "");
    setStarttls(smtp.data.smtp_starttls);
    setImplicitTls(smtp.data.smtp_implicit_tls);
    setValidateCerts(smtp.data.smtp_validate_certs);
    setAuthMode(smtp.data.smtp_auth_mode);
    setPassword("");
    setClearPassword(false);
  }, [smtp.data]);

  const fieldClass =
    "w-full rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-mono text-sm text-text-main outline-none ring-primary focus:ring-1";

  if (smtp.isLoading) {
    return <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>;
  }
  if (smtp.isError) {
    return (
      <p className="mt-10 text-accent-warning" role="alert">
        {(smtp.error as Error).message}
      </p>
    );
  }

  return (
    <div className="mt-8 max-w-xl space-y-6">
      <p className="text-sm text-text-muted">
        Passwords are never shown again after save: they are encrypted at rest (same Fernet key as
        Entra token secrets). TLS is required whenever SMTP is enabled—plain SMTP is blocked.
        Typical{" "}
        <a
          className="text-primary underline-offset-2 hover:underline"
          href="https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365"
          rel="noreferrer"
          target="_blank"
        >
          Microsoft 365 SMTP client submission
        </a>
        : host <span className="font-mono text-text-main">smtp.office365.com</span>, port{" "}
        <span className="font-mono text-text-main">587</span>, enable STARTTLS, disable implicit
        TLS, authenticate with a licensed mailbox (username is usually the full email address).
      </p>

      <form
        className="space-y-4 rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated"
        onSubmit={(e) => {
          e.preventDefault();
          const parsedPort = Number.parseInt(port, 10);
          smtpPatch.mutate({
            smtp_enabled: enabled,
            smtp_host: host.trim() || null,
            smtp_port: Number.isFinite(parsedPort) ? parsedPort : 587,
            smtp_username: authMode === "login" ? username.trim() || null : null,
            smtp_from: from.trim() || null,
            smtp_starttls: starttls,
            smtp_implicit_tls: implicitTls,
            smtp_validate_certs: validateCerts,
            smtp_auth_mode: authMode,
            ...(password.trim() ? { smtp_password: password.trim() } : {}),
            ...(clearPassword ? { clear_smtp_password: true } : {}),
          });
        }}
      >
        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enable outbound SMTP
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Host</span>
          <input
            className={fieldClass}
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="smtp.office365.com"
          />
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Port</span>
          <input
            className={fieldClass}
            inputMode="numeric"
            value={port}
            onChange={(e) => setPort(e.target.value)}
          />
        </label>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">From address</span>
          <input
            className={fieldClass}
            type="email"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            placeholder="same as username for many tenants"
            autoComplete="off"
          />
        </label>

        <div className="border-t border-border pt-3">
          <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Transport security
          </p>
          <p className="mt-1 text-xs text-text-muted">
            Enable exactly one of STARTTLS or implicit TLS. Server certificates are verified by
            default (turn off only for private CAs you trust).
          </p>
          <label className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
            <input
              type="checkbox"
              checked={starttls}
              onChange={(e) => {
                setStarttls(e.target.checked);
                if (e.target.checked) {
                  setImplicitTls(false);
                }
              }}
            />
            STARTTLS (recommended for port 587)
          </label>
          <label className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
            <input
              type="checkbox"
              checked={implicitTls}
              onChange={(e) => {
                setImplicitTls(e.target.checked);
                if (e.target.checked) {
                  setStarttls(false);
                }
              }}
            />
            Implicit TLS (SSL on connect, e.g. port 465)
          </label>
          <label className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
            <input
              type="checkbox"
              checked={validateCerts}
              onChange={(e) => setValidateCerts(e.target.checked)}
            />
            Validate server TLS certificate (recommended)
          </label>
        </div>

        <div className="border-t border-border pt-3">
          <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Authentication
          </p>
          <label className="mt-2 grid gap-1 font-mono text-xs">
            <span className="text-text-muted">SMTP AUTH</span>
            <select
              className={fieldClass}
              value={authMode}
              onChange={(e) => setAuthMode(e.target.value as "login" | "none")}
            >
              <option value="login">Username and password (Microsoft 365, most providers)</option>
              <option value="none">No login — trusted relay only (still uses TLS)</option>
            </select>
          </label>
          {authMode === "login" ? (
            <>
              <label className="mt-3 grid gap-1 font-mono text-xs">
                <span className="text-text-muted">Username</span>
                <input
                  className={fieldClass}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="mailbox@yourtenant.onmicrosoft.com"
                  autoComplete="off"
                />
              </label>
              <label className="mt-3 grid gap-1 font-mono text-xs">
                <span className="text-text-muted">SMTP password (encrypted when stored)</span>
                <input
                  className={fieldClass}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    smtp.data?.smtp_password_configured
                      ? "Leave blank to keep current"
                      : "App password or mailbox password"
                  }
                  autoComplete="new-password"
                />
              </label>
              <label className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearPassword}
                  onChange={(e) => setClearPassword(e.target.checked)}
                />
                Remove stored password
              </label>
            </>
          ) : (
            <p className="mt-2 text-xs text-accent-warning">
              Without SMTP AUTH, the relay must trust this host by IP or other policy. Do not expose
              port 25 to the internet.
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="submit"
            disabled={smtpPatch.isPending}
            className="rounded-sharp bg-primary/15 px-3 py-1.5 font-mono text-xs text-primary ring-1 ring-primary/40 disabled:opacity-40"
          >
            {smtpPatch.isPending ? "Saving…" : "Save settings"}
          </button>
        </div>
        {smtpPatch.isError ? (
          <p className="text-sm text-accent-warning" role="alert">
            {(smtpPatch.error as Error).message}
          </p>
        ) : null}
        {smtpPatch.isSuccess ? (
          <p className="text-sm text-primary" role="status">
            Saved. Ready to send: {smtpPatch.data.smtp_ready ? "yes" : "no"}.
          </p>
        ) : null}
      </form>

      <div className="rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Test send</p>
        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Send test to (optional)</span>
          <input
            className={fieldClass}
            type="email"
            value={testTo}
            onChange={(e) => setTestTo(e.target.value)}
            placeholder="Defaults to your admin email"
            autoComplete="email"
          />
        </label>
        <button
          type="button"
          disabled={smtpTest.isPending || !smtp.data?.smtp_ready}
          className="rounded-sharp border border-border px-3 py-1.5 font-mono text-xs hover:bg-bg-recessed disabled:opacity-40"
          onClick={() => smtpTest.mutate(testTo.trim() || null)}
        >
          {smtpTest.isPending ? "Sending…" : "Send test email"}
        </button>
        {!smtp.data?.smtp_ready ? (
          <p className="text-xs text-text-muted">Save a complete configuration before testing.</p>
        ) : null}
        {smtpTest.isError ? (
          <p className="text-sm text-accent-warning" role="alert">
            {(smtpTest.error as Error).message}
          </p>
        ) : null}
        {smtpTest.isSuccess ? (
          <p className="text-sm text-primary" role="status">
            Sent to {smtpTest.data.to}.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function emptyAdminLlmPatch(): components["schemas"]["AdminLlmSettingsPatch"] {
  return {
    clear_litellm_api_base: false,
    clear_litellm_api_key: false,
    clear_openai_api_base: false,
    clear_openai_api_key: false,
    clear_anthropic_api_base: false,
    clear_anthropic_api_key: false,
  };
}

function AdminLlmPanel({
  llm,
  llmPatch,
}: {
  llm: UseQueryResult<AdminLlmSettings, Error>;
  llmPatch: UseMutationResult<
    AdminLlmSettings,
    Error,
    components["schemas"]["AdminLlmSettingsPatch"]
  >;
}) {
  const [deckProvider, setDeckProvider] = useState<string>("litellm");
  const [providerDirty, setProviderDirty] = useState(false);
  const [litellmBase, setLitellmBase] = useState("");
  const [litellmBaseDirty, setLitellmBaseDirty] = useState(false);
  const [litellmKey, setLitellmKey] = useState("");
  const [clearLitellmKey, setClearLitellmKey] = useState(false);
  const [clearLitellmBase, setClearLitellmBase] = useState(false);
  const [openaiBase, setOpenaiBase] = useState("");
  const [openaiBaseDirty, setOpenaiBaseDirty] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  const [clearOpenaiKey, setClearOpenaiKey] = useState(false);
  const [clearOpenaiBase, setClearOpenaiBase] = useState(false);
  const [anthropicBase, setAnthropicBase] = useState("");
  const [anthropicBaseDirty, setAnthropicBaseDirty] = useState(false);
  const [anthropicKey, setAnthropicKey] = useState("");
  const [clearAnthropicKey, setClearAnthropicKey] = useState(false);
  const [clearAnthropicBase, setClearAnthropicBase] = useState(false);

  useEffect(() => {
    if (!llm.data) return;
    setDeckProvider(llm.data.deck_llm_provider ?? "litellm");
    setProviderDirty(false);
    setLitellmBase(llm.data.litellm_api_base ?? "");
    setLitellmBaseDirty(false);
    setLitellmKey("");
    setClearLitellmKey(false);
    setClearLitellmBase(false);
    setOpenaiBase(llm.data.openai_api_base ?? "");
    setOpenaiBaseDirty(false);
    setOpenaiKey("");
    setClearOpenaiKey(false);
    setClearOpenaiBase(false);
    setAnthropicBase(llm.data.anthropic_api_base ?? "");
    setAnthropicBaseDirty(false);
    setAnthropicKey("");
    setClearAnthropicKey(false);
    setClearAnthropicBase(false);
  }, [llm.data]);

  const fieldClass =
    "w-full rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-mono text-sm text-text-main outline-none ring-primary focus:ring-1";

  if (llm.isLoading) {
    return <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>;
  }
  if (llm.isError) {
    return (
      <p className="mt-10 text-accent-warning" role="alert">
        {(llm.error as Error).message}
      </p>
    );
  }

  const active = deckProvider;

  return (
    <div className="mt-8 max-w-xl space-y-6">
      <p className="text-sm text-text-muted">
        Choose how deck AI edits call the model:{" "}
        <span className="font-mono text-text-main">OpenAI</span> and{" "}
        <span className="font-mono text-text-main">Claude</span> use the official Python SDKs.{" "}
        <span className="font-mono text-text-main">LiteLLM</span> uses an OpenAI-compatible HTTP
        endpoint (your proxy or gateway). Environment variables still apply as fallbacks; database
        values override where noted. Keys are encrypted and never returned. Model ids default per
        provider (see <span className="font-mono text-text-main">DECK_LLM_MODEL_OPENAI</span>,{" "}
        <span className="font-mono text-text-main">DECK_LLM_MODEL_ANTHROPIC</span>,{" "}
        <span className="font-mono text-text-main">DECK_LLM_MODEL_LITELLM</span>, or a single{" "}
        <span className="font-mono text-text-main">DECK_LLM_MODEL</span> for all).
      </p>

      <form
        className="space-y-4 rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated"
        onSubmit={(e) => {
          e.preventDefault();
          const body = emptyAdminLlmPatch();
          if (providerDirty) {
            body.deck_llm_provider = deckProvider;
          }
          if (clearLitellmBase) {
            body.clear_litellm_api_base = true;
          } else if (litellmBaseDirty) {
            body.litellm_api_base = litellmBase.trim();
          }
          if (clearLitellmKey) {
            body.clear_litellm_api_key = true;
          } else if (litellmKey.trim()) {
            body.litellm_api_key = litellmKey.trim();
          }
          if (clearOpenaiBase) {
            body.clear_openai_api_base = true;
          } else if (openaiBaseDirty) {
            body.openai_api_base = openaiBase.trim();
          }
          if (clearOpenaiKey) {
            body.clear_openai_api_key = true;
          } else if (openaiKey.trim()) {
            body.openai_api_key = openaiKey.trim();
          }
          if (clearAnthropicBase) {
            body.clear_anthropic_api_base = true;
          } else if (anthropicBaseDirty) {
            body.anthropic_api_base = anthropicBase.trim();
          }
          if (clearAnthropicKey) {
            body.clear_anthropic_api_key = true;
          } else if (anthropicKey.trim()) {
            body.anthropic_api_key = anthropicKey.trim();
          }
          llmPatch.mutate(body);
        }}
      >
        <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Summary</p>
        <p className="font-mono text-xs text-text-main">
          Active backend:{" "}
          <span className="text-primary">{llm.data?.deck_llm_provider ?? "litellm"}</span>
        </p>
        <p className="font-mono text-[10px] text-text-muted">
          LiteLLM base: {llm.data?.litellm_api_base?.trim() ? llm.data.litellm_api_base : "—"} ·
          key: {llm.data?.litellm_api_key_configured ? "set" : "not set"}
        </p>
        <p className="font-mono text-[10px] text-text-muted">
          OpenAI base: {llm.data?.openai_api_base?.trim() ? llm.data.openai_api_base : "—"} · key:{" "}
          {llm.data?.openai_api_key_configured ? "set" : "not set"}
        </p>
        <p className="font-mono text-[10px] text-text-muted">
          Anthropic base: {llm.data?.anthropic_api_base?.trim() ? llm.data.anthropic_api_base : "—"}{" "}
          · key: {llm.data?.anthropic_api_key_configured ? "set" : "not set"}
        </p>

        <label className="grid gap-1 font-mono text-xs">
          <span className="text-text-muted">Active provider for deck jobs</span>
          <select
            className={fieldClass}
            value={deckProvider}
            onChange={(e) => {
              setDeckProvider(e.target.value);
              setProviderDirty(true);
            }}
          >
            <option value="litellm">LiteLLM / OpenAI-compatible (HTTP)</option>
            <option value="openai">OpenAI (SDK)</option>
            <option value="claude">Claude (Anthropic SDK)</option>
          </select>
        </label>

        {active === "litellm" ? (
          <div className="space-y-3 border-t border-border pt-3">
            <p className="font-mono text-[10px] uppercase text-text-muted">LiteLLM</p>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">OpenAI-compatible base URL</span>
              <input
                className={fieldClass}
                value={litellmBase}
                onChange={(e) => {
                  setLitellmBase(e.target.value);
                  setLitellmBaseDirty(true);
                }}
                placeholder="https://litellm.example.com/v1"
                autoComplete="off"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearLitellmBase}
                onChange={(e) => setClearLitellmBase(e.target.checked)}
              />
              Remove database base URL (fall back to LITELLM_API_BASE env only)
            </label>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">API key (write-only)</span>
              <input
                className={fieldClass}
                type="password"
                autoComplete="off"
                value={litellmKey}
                onChange={(e) => setLitellmKey(e.target.value)}
                placeholder={
                  llm.data?.litellm_api_key_configured
                    ? "Leave blank to keep existing key"
                    : "sk-… or virtual key"
                }
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearLitellmKey}
                onChange={(e) => setClearLitellmKey(e.target.checked)}
              />
              Remove stored LiteLLM key
            </label>
          </div>
        ) : null}

        {active === "openai" ? (
          <div className="space-y-3 border-t border-border pt-3">
            <p className="font-mono text-[10px] uppercase text-text-muted">OpenAI</p>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">API base URL (optional)</span>
              <input
                className={fieldClass}
                value={openaiBase}
                onChange={(e) => {
                  setOpenaiBase(e.target.value);
                  setOpenaiBaseDirty(true);
                }}
                placeholder="Default: https://api.openai.com/v1"
                autoComplete="off"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearOpenaiBase}
                onChange={(e) => setClearOpenaiBase(e.target.checked)}
              />
              Remove database OpenAI base override
            </label>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">API key (write-only)</span>
              <input
                className={fieldClass}
                type="password"
                autoComplete="off"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder={
                  llm.data?.openai_api_key_configured ? "Leave blank to keep existing key" : "sk-…"
                }
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearOpenaiKey}
                onChange={(e) => setClearOpenaiKey(e.target.checked)}
              />
              Remove stored OpenAI key
            </label>
          </div>
        ) : null}

        {active === "claude" ? (
          <div className="space-y-3 border-t border-border pt-3">
            <p className="font-mono text-[10px] uppercase text-text-muted">Anthropic</p>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">API base URL (optional)</span>
              <input
                className={fieldClass}
                value={anthropicBase}
                onChange={(e) => {
                  setAnthropicBase(e.target.value);
                  setAnthropicBaseDirty(true);
                }}
                placeholder="Default: https://api.anthropic.com"
                autoComplete="off"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearAnthropicBase}
                onChange={(e) => setClearAnthropicBase(e.target.checked)}
              />
              Remove database Anthropic base override
            </label>
            <label className="grid gap-1 font-mono text-xs">
              <span className="text-text-muted">API key (write-only)</span>
              <input
                className={fieldClass}
                type="password"
                autoComplete="off"
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                placeholder={
                  llm.data?.anthropic_api_key_configured
                    ? "Leave blank to keep existing key"
                    : "sk-ant-…"
                }
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
              <input
                type="checkbox"
                checked={clearAnthropicKey}
                onChange={(e) => setClearAnthropicKey(e.target.checked)}
              />
              Remove stored Anthropic key
            </label>
          </div>
        ) : null}

        <button
          type="submit"
          className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-xs text-primary ring-1 ring-primary/40 disabled:opacity-50"
          disabled={llmPatch.isPending}
        >
          {llmPatch.isPending ? "Saving…" : "Save LLM settings"}
        </button>

        {llmPatch.isError ? (
          <p className="text-sm text-accent-warning" role="alert">
            {(llmPatch.error as Error).message}
          </p>
        ) : null}
        {llmPatch.isSuccess ? (
          <p className="text-sm text-primary" role="status">
            Saved.
          </p>
        ) : null}
      </form>
    </div>
  );
}
