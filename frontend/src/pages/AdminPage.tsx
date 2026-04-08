import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiAdminLogs } from "../lib/api";
import { useAuthStore } from "../stores/auth";

const CHANNELS = ["", "http", "auth", "audit", "script"] as const;

export default function AdminPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [channel, setChannel] = useState<string>("");

  const logs = useQuery({
    queryKey: ["admin", "logs", accessToken, channel],
    enabled: Boolean(accessToken),
    queryFn: () => apiAdminLogs(accessToken!, channel || null),
  });

  return (
    <div className="min-h-dvh bg-bg-void px-4 py-10 text-text-main">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-sm text-primary">Admin</p>
            <h1 className="font-heading text-3xl font-semibold">Request logs</h1>
            <p className="mt-1 text-sm text-text-muted">
              Channels: web traffic (http), auth events, audit (admin actions), scripts (CLI).
              Filter by request ID in later milestones.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 font-mono text-xs text-text-muted">
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
            <Link
              to="/"
              className="font-mono text-sm text-text-muted underline decoration-border hover:text-primary"
            >
              Home
            </Link>
          </div>
        </header>

        {!accessToken ? (
          <p className="mt-10 text-text-muted">
            No session.{" "}
            <Link className="text-primary underline" to="/login">
              Sign in
            </Link>
            .
          </p>
        ) : logs.isLoading ? (
          <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
        ) : logs.isError ? (
          <p className="mt-10 text-accent-warning" role="alert">
            {(logs.error as Error).message}
          </p>
        ) : (
          <div className="mt-8 overflow-x-auto rounded-sharp border border-border bg-bg-elevated">
            <table className="w-full min-w-[800px] border-collapse text-left text-sm">
              <thead className="border-b border-border bg-bg-recessed font-mono text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Channel</th>
                  <th className="px-3 py-2">Level</th>
                  <th className="px-3 py-2">Method</th>
                  <th className="px-3 py-2">Path</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">ms</th>
                  <th className="px-3 py-2">Request ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs text-text-main">
                {logs.data?.items.map((row) => (
                  <tr key={row.id} className="hover:bg-bg-recessed/60">
                    <td className="whitespace-nowrap px-3 py-2 text-text-muted">{row.ts}</td>
                    <td className="px-3 py-2 text-primary">{row.channel}</td>
                    <td className="px-3 py-2">{row.level}</td>
                    <td className="px-3 py-2">{row.method}</td>
                    <td className="max-w-[240px] truncate px-3 py-2" title={row.path}>
                      {row.path}
                    </td>
                    <td className="px-3 py-2">{row.status_code ?? "—"}</td>
                    <td className="px-3 py-2">{row.latency_ms ?? "—"}</td>
                    <td className="max-w-[200px] truncate px-3 py-2" title={row.request_id ?? ""}>
                      {row.request_id ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
