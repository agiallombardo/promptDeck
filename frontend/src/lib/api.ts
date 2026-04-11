import type { components } from "./api/schema";
import { pushToastFromApiError } from "../stores/toasts";

const API = "/api/v1";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  auth_provider: "local" | "entra";
};

export type AuthConfig = {
  local_password_auth_enabled: boolean;
  entra_enabled: boolean;
  entra_login_url: string | null;
};

export type PresentationSummary = components["schemas"]["PresentationRead"];
export type ThreadDto = components["schemas"]["ThreadRead"];
export type CommentDto = components["schemas"]["CommentRead"];
export type ExportJobDto = components["schemas"]["ExportJobRead"];

export type DirectoryUserDto = {
  entra_object_id: string;
  email: string;
  display_name: string | null;
  user_type: string | null;
};

export type PresentationMemberDto = {
  id: string;
  presentation_id: string;
  role: "editor" | "user";
  principal_tenant_id: string;
  principal_entra_object_id: string;
  principal_email: string;
  principal_display_name: string | null;
  principal_user_type: string | null;
  user_id: string | null;
  granted_by: string;
  created_at: string;
  updated_at: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | undefined;
  readonly requestId: string | null;

  constructor(args: { status: number; detail?: string; requestId: string | null }) {
    super(args.detail?.trim() ? args.detail : `Request failed (${args.status})`);
    this.name = "ApiError";
    this.status = args.status;
    this.detail = args.detail;
    this.requestId = args.requestId;
  }
}

function authHeaders(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

type JsonFetchOpts = {
  skipErrorToast?: boolean;
};

async function jsonFetch<T>(
  path: string,
  init: RequestInit = {},
  opts?: JsonFetchOpts,
): Promise<T> {
  const r = await fetch(path, { credentials: "include", ...init });
  const requestId = r.headers.get("x-request-id");
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail;
    const err = new ApiError({ status: r.status, detail, requestId });
    if (!opts?.skipErrorToast) {
      pushToastFromApiError(err);
    }
    throw err;
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export function iframeSrcForDev(iframeSrc: string): string {
  if (!import.meta.env.DEV) return iframeSrc;
  try {
    const u = new URL(iframeSrc);
    if (u.hostname === "127.0.0.1" || u.hostname === "localhost") {
      return `${u.pathname}${u.search}`;
    }
  } catch {
    /* ignore */
  }
  return iframeSrc;
}

export async function apiAuthConfig() {
  return jsonFetch<AuthConfig>(`${API}/auth/config`, undefined, { skipErrorToast: true });
}

export async function apiLogin(email: string, password: string) {
  return jsonFetch<{
    access_token: string;
    user: AuthUser;
  }>(
    `${API}/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    },
    { skipErrorToast: true },
  );
}

export async function apiRefresh() {
  const r = await fetch(`${API}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!r.ok) return null;
  return r.json() as Promise<{
    access_token: string;
    user: AuthUser;
    expires_in: number;
  }>;
}

export async function apiLogout() {
  await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" });
}

export async function apiPresentationsList(accessToken: string) {
  return jsonFetch<{ items: PresentationSummary[] }>(`${API}/presentations`, {
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiPresentationCreate(
  accessToken: string,
  title: string,
  description?: string,
) {
  return jsonFetch<PresentationSummary>(`${API}/presentations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify({ title, description: description ?? null }),
  });
}

export async function apiPresentationGet(accessToken: string, presentationId: string) {
  return jsonFetch<PresentationSummary>(`${API}/presentations/${presentationId}`, {
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiPresentationDelete(accessToken: string, presentationId: string) {
  await jsonFetch<void>(`${API}/presentations/${presentationId}`, {
    method: "DELETE",
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiPresentationEmbed(accessToken: string, presentationId: string) {
  return jsonFetch<{ iframe_src: string; version_id: string; slide_count: number }>(
    `${API}/presentations/${presentationId}/embed`,
    {
      headers: { ...authHeaders(accessToken) },
    },
  );
}

export async function apiThreadsList(
  accessToken: string,
  presentationId: string,
  versionId?: string | null,
) {
  const params = new URLSearchParams();
  if (versionId) params.set("version_id", versionId);
  const qs = params.toString();
  return jsonFetch<{ items: ThreadDto[] }>(
    `${API}/presentations/${presentationId}/threads${qs ? `?${qs}` : ""}`,
    {
      headers: { ...authHeaders(accessToken) },
    },
  );
}

export async function apiThreadCreate(
  accessToken: string,
  presentationId: string,
  body: {
    version_id: string;
    slide_index: number;
    anchor_x: number;
    anchor_y: number;
    first_comment: string;
  },
) {
  return jsonFetch<ThreadDto>(`${API}/presentations/${presentationId}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify(body),
  });
}

export async function apiCommentCreate(accessToken: string, threadId: string, body: string) {
  return jsonFetch<CommentDto>(`${API}/threads/${threadId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify({ body }),
  });
}

export async function apiThreadPatch(
  accessToken: string,
  threadId: string,
  status: "open" | "resolved",
) {
  return jsonFetch<ThreadDto>(`${API}/threads/${threadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify({ status }),
  });
}

export async function apiCommentDelete(accessToken: string, commentId: string) {
  await jsonFetch<void>(`${API}/comments/${commentId}`, {
    method: "DELETE",
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiVersionUpload(accessToken: string, presentationId: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return jsonFetch<{
    id: string;
    slides: Array<{ slide_index: number; selector: string; title: string | null }>;
  }>(`${API}/presentations/${presentationId}/versions`, {
    method: "POST",
    headers: { ...authHeaders(accessToken) },
    body: fd,
  });
}

export async function apiDirectoryUsers(accessToken: string, query: string) {
  const params = new URLSearchParams({ q: query });
  return jsonFetch<{ items: DirectoryUserDto[] }>(
    `${API}/directory/users?${params.toString()}`,
    {
      headers: { ...authHeaders(accessToken) },
    },
    { skipErrorToast: true },
  );
}

export async function apiMembersList(accessToken: string, presentationId: string) {
  return jsonFetch<{ items: PresentationMemberDto[] }>(
    `${API}/presentations/${presentationId}/members`,
    {
      headers: { ...authHeaders(accessToken) },
    },
  );
}

export async function apiMemberCreate(
  accessToken: string,
  presentationId: string,
  body: {
    entra_object_id: string;
    email: string;
    display_name?: string | null;
    user_type?: string | null;
    role: "editor" | "user";
  },
) {
  return jsonFetch<PresentationMemberDto>(`${API}/presentations/${presentationId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify(body),
  });
}

export async function apiMemberUpdate(
  accessToken: string,
  presentationId: string,
  memberId: string,
  role: "editor" | "user",
) {
  return jsonFetch<PresentationMemberDto>(
    `${API}/presentations/${presentationId}/members/${memberId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
      body: JSON.stringify({ role }),
    },
  );
}

export async function apiMemberDelete(
  accessToken: string,
  presentationId: string,
  memberId: string,
) {
  await jsonFetch<void>(`${API}/presentations/${presentationId}/members/${memberId}`, {
    method: "DELETE",
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiExportCreate(
  accessToken: string,
  presentationId: string,
  body: { format?: string; version_id?: string | null },
) {
  return jsonFetch<ExportJobDto>(`${API}/presentations/${presentationId}/exports`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify(body),
  });
}

export async function apiExportGet(accessToken: string, jobId: string) {
  return jsonFetch<ExportJobDto>(`${API}/exports/${jobId}`, {
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiExportDownloadFile(accessToken: string, jobId: string): Promise<Blob> {
  const r = await fetch(`${API}/exports/${jobId}/file`, {
    credentials: "include",
    headers: { ...authHeaders(accessToken) },
  });
  const requestId = r.headers.get("x-request-id");
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail;
    throw new ApiError({ status: r.status, detail, requestId });
  }
  return r.blob();
}

export type AdminAppLogRow = {
  id: number;
  ts: string;
  level: string;
  event: string | null;
  channel: string;
  request_id: string | null;
  user_id: string | null;
  path: string;
  method: string;
  status_code: number | null;
  latency_ms: number | null;
  payload: Record<string, unknown> | null;
};

export async function apiAdminLogs(
  accessToken: string,
  opts?: {
    limit?: number;
    channel?: string | null;
    request_id?: string | null;
    level?: string | null;
    path_prefix?: string | null;
    event_contains?: string | null;
    since?: string | null;
    cursor?: number | null;
  },
) {
  const params = new URLSearchParams({ limit: String(opts?.limit ?? 100) });
  if (opts?.channel) params.set("channel", opts.channel);
  if (opts?.request_id?.trim()) params.set("request_id", opts.request_id.trim());
  if (opts?.level?.trim()) params.set("level", opts.level.trim());
  if (opts?.path_prefix?.trim()) params.set("path_prefix", opts.path_prefix.trim());
  if (opts?.event_contains?.trim()) params.set("event_contains", opts.event_contains.trim());
  if (opts?.since?.trim()) params.set("since", opts.since.trim());
  if (opts?.cursor != null) params.set("cursor", String(opts.cursor));
  return jsonFetch<{ items: AdminAppLogRow[]; next_cursor: number | null }>(
    `${API}/admin/logs?${params.toString()}`,
    { headers: { ...authHeaders(accessToken) } },
  );
}

export async function apiAdminStats(accessToken: string) {
  return jsonFetch<{
    users: number;
    presentations: number;
    versions: number;
    export_jobs: number;
    audit_events_24h: number;
    app_log_rows_24h: number;
  }>(`${API}/admin/stats`, { headers: { ...authHeaders(accessToken) } });
}

export async function apiAdminSetup(accessToken: string) {
  return jsonFetch<{
    local_password_auth_enabled: boolean;
    entra_enabled: boolean;
    entra_tenant_id_configured: boolean;
    entra_client_id_configured: boolean;
    entra_client_secret_configured: boolean;
    entra_login_ready: boolean;
    smtp_enabled: boolean;
    smtp_ready: boolean;
    public_app_url: string;
    public_api_url: string;
    entra_redirect_uri: string;
  }>(`${API}/admin/setup`, { headers: { ...authHeaders(accessToken) } });
}

export type AdminSmtpSettings = {
  smtp_enabled: boolean;
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  smtp_from: string | null;
  smtp_starttls: boolean;
  smtp_implicit_tls: boolean;
  smtp_password_configured: boolean;
  smtp_ready: boolean;
};

export async function apiAdminSmtpGet(accessToken: string) {
  return jsonFetch<AdminSmtpSettings>(`${API}/admin/settings/smtp`, {
    headers: { ...authHeaders(accessToken) },
  });
}

export async function apiAdminSmtpPatch(
  accessToken: string,
  body: {
    smtp_enabled?: boolean;
    smtp_host?: string | null;
    smtp_port?: number;
    smtp_username?: string | null;
    smtp_from?: string | null;
    smtp_starttls?: boolean;
    smtp_implicit_tls?: boolean;
    smtp_password?: string | null;
    clear_smtp_password?: boolean;
  },
) {
  return jsonFetch<AdminSmtpSettings>(`${API}/admin/settings/smtp`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify(body),
  });
}

export async function apiAdminSmtpTest(accessToken: string, to?: string | null) {
  return jsonFetch<{ ok: boolean; to: string }>(`${API}/admin/settings/smtp/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    body: JSON.stringify(to ? { to } : {}),
  });
}

export async function apiAdminAudit(accessToken: string, limit = 100) {
  return jsonFetch<{
    items: Array<{
      id: number;
      ts: string;
      actor_id: string | null;
      action: string;
      target_kind: string | null;
      target_id: string | null;
      metadata: Record<string, unknown> | null;
      ip: string | null;
    }>;
  }>(`${API}/admin/audit?limit=${limit}`, { headers: { ...authHeaders(accessToken) } });
}

export async function apiAdminUsers(accessToken: string) {
  return jsonFetch<{
    items: Array<{
      id: string;
      email: string;
      display_name: string | null;
      role: string;
      last_login_at: string | null;
      created_at: string;
    }>;
  }>(`${API}/admin/users`, { headers: { ...authHeaders(accessToken) } });
}

export async function apiAdminPresentations(accessToken: string) {
  return jsonFetch<{
    items: Array<{
      id: string;
      title: string;
      owner_id: string;
      owner_email: string;
      current_version_id: string | null;
      version_count: number;
      updated_at: string;
    }>;
  }>(`${API}/admin/presentations`, { headers: { ...authHeaders(accessToken) } });
}

export async function apiAdminJobs(accessToken: string) {
  return jsonFetch<{
    items: Array<{
      id: string;
      presentation_id: string;
      presentation_title: string;
      version_id: string;
      format: string;
      status: string;
      progress: number;
      error: string | null;
      created_by: string;
      created_at: string;
      finished_at: string | null;
    }>;
  }>(`${API}/admin/jobs`, { headers: { ...authHeaders(accessToken) } });
}
