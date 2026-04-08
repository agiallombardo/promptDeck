const API = "/api/v1";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
};

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

function authHeaders(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

export async function apiLogin(email: string, password: string) {
  const r = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{
    access_token: string;
    user: AuthUser;
  }>;
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

export type PresentationSummary = {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
  current_version: unknown | null;
};

export async function apiPresentationsList(accessToken: string) {
  const r = await fetch(`${API}/presentations`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{ items: PresentationSummary[] }>;
}

export async function apiPresentationCreate(
  accessToken: string,
  title: string,
  description?: string,
) {
  const r = await fetch(`${API}/presentations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify({ title, description: description ?? null }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<PresentationSummary>;
}

export async function apiPresentationGet(accessToken: string, presentationId: string) {
  const r = await fetch(`${API}/presentations/${presentationId}`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<PresentationSummary>;
}

export async function apiPresentationEmbed(accessToken: string, presentationId: string) {
  const r = await fetch(`${API}/presentations/${presentationId}/embed`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{ iframe_src: string; version_id: string; slide_count: number }>;
}

export type CommentDto = {
  id: string;
  author_id: string;
  author_display_name: string | null;
  body: string;
  body_format: string;
  created_at: string;
  edited_at: string | null;
};

export type ThreadDto = {
  id: string;
  presentation_id: string;
  version_id: string;
  slide_index: number;
  anchor_x: number;
  anchor_y: number;
  status: string;
  created_by: string;
  created_at: string;
  resolved_at: string | null;
  comments: CommentDto[];
};

export async function apiThreadsList(
  accessToken: string,
  presentationId: string,
  versionId?: string | null,
) {
  const params = new URLSearchParams();
  if (versionId) params.set("version_id", versionId);
  const qs = params.toString();
  const r = await fetch(`${API}/presentations/${presentationId}/threads${qs ? `?${qs}` : ""}`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{ items: ThreadDto[] }>;
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
  const r = await fetch(`${API}/presentations/${presentationId}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ThreadDto>;
}

export async function apiCommentCreate(accessToken: string, threadId: string, body: string) {
  const r = await fetch(`${API}/threads/${threadId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify({ body }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<CommentDto>;
}

export async function apiThreadPatch(
  accessToken: string,
  threadId: string,
  status: "open" | "resolved",
) {
  const r = await fetch(`${API}/threads/${threadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify({ status }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ThreadDto>;
}

export async function apiCommentDelete(accessToken: string, commentId: string) {
  const r = await fetch(`${API}/comments/${commentId}`, {
    method: "DELETE",
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
}

export async function apiVersionUpload(accessToken: string, presentationId: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API}/presentations/${presentationId}/versions`, {
    method: "POST",
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
    body: fd,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{
    id: string;
    slides: Array<{ slide_index: number; selector: string; title: string | null }>;
  }>;
}

export async function apiShareExchange(plaintextToken: string) {
  const r = await fetch(`${API}/shares/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ token: plaintextToken }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{
    access_token: string;
    expires_in: number;
    presentation_id: string;
    role: string;
  }>;
}

export type ShareLinkDto = {
  id: string;
  presentation_id: string;
  role: string;
  expires_at: string | null;
  revoked_at: string | null;
  note: string | null;
  created_at: string;
};

export async function apiSharesList(accessToken: string, presentationId: string) {
  const r = await fetch(`${API}/presentations/${presentationId}/shares`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{ items: ShareLinkDto[] }>;
}

export async function apiShareCreate(
  accessToken: string,
  presentationId: string,
  body: { role: string; expires_at?: string | null; note?: string | null },
) {
  const r = await fetch(`${API}/presentations/${presentationId}/shares`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ShareLinkDto & { token: string }>;
}

export async function apiShareRevoke(accessToken: string, presentationId: string, shareId: string) {
  const r = await fetch(`${API}/presentations/${presentationId}/shares/${shareId}`, {
    method: "DELETE",
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
}

export type ExportJobDto = {
  id: string;
  presentation_id: string;
  version_id: string;
  format: string;
  status: string;
  output_path: string | null;
  error: string | null;
  progress: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export async function apiExportCreate(
  accessToken: string,
  presentationId: string,
  body: { format?: string; version_id?: string | null },
) {
  const r = await fetch(`${API}/presentations/${presentationId}/exports`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(accessToken) },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ExportJobDto>;
}

export async function apiExportGet(accessToken: string, jobId: string) {
  const r = await fetch(`${API}/exports/${jobId}`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ExportJobDto>;
}

export async function apiAdminLogs(accessToken: string, channel?: string | null) {
  const params = new URLSearchParams({ limit: "100" });
  if (channel) params.set("channel", channel);
  const r = await fetch(`${API}/admin/logs?${params.toString()}`, {
    headers: { ...authHeaders(accessToken) },
    credentials: "include",
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<{
    items: Array<{
      id: number;
      ts: string;
      level: string;
      event: string | null;
      channel: string;
      request_id: string | null;
      path: string;
      method: string;
      status_code: number | null;
      latency_ms: number | null;
    }>;
    next_cursor: number | null;
  }>;
}
