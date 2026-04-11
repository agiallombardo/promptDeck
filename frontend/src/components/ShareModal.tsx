import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  apiDirectoryUsers,
  apiMemberCreate,
  apiMemberDelete,
  apiMembersList,
  apiMemberUpdate,
  apiShareLinkCreate,
  apiShareLinkRevoke,
  apiShareLinksList,
  type DirectoryUserDto,
  type PresentationMemberDto,
  type ShareLinkCreateDto,
  type ShareLinkDto,
} from "../lib/api";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useAuthStore } from "../stores/auth";

const MEMBER_ROLE_OPTIONS = [
  { value: "user" as const, label: "Viewer" },
  { value: "editor" as const, label: "Editor" },
] as const;
const SHARE_LINK_ROLE_OPTIONS = [
  { value: "viewer" as const, label: "Viewer" },
  { value: "commenter" as const, label: "Commenter" },
] as const;

function roleLabel(role: "editor" | "user"): string {
  return MEMBER_ROLE_OPTIONS.find((o) => o.value === role)?.label ?? role;
}

function shareRoleLabel(role: "viewer" | "commenter" | "editor"): string {
  return SHARE_LINK_ROLE_OPTIONS.find((o) => o.value === role)?.label ?? role;
}

type Props = {
  open: boolean;
  onClose: () => void;
  accessToken: string;
  presentationId: string;
};

export function ShareModal({ open, onClose, accessToken, presentationId }: Props) {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const directorySearchAvailable = user?.auth_provider === "entra";
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 450);
  const [role, setRole] = useState<"editor" | "user">("user");
  const [selected, setSelected] = useState<DirectoryUserDto | null>(null);
  const [shareRole, setShareRole] = useState<"viewer" | "commenter" | "editor">("viewer");
  const [shareExpiryHours, setShareExpiryHours] = useState("24");
  const [shareNote, setShareNote] = useState("");
  const [createdLink, setCreatedLink] = useState<ShareLinkCreateDto | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setSelected(null);
      setShareRole("viewer");
      setShareExpiryHours("24");
      setShareNote("");
      setCreatedLink(null);
    }
  }, [open]);

  const list = useQuery({
    queryKey: ["members", presentationId, accessToken],
    queryFn: () => apiMembersList(accessToken, presentationId),
    enabled: open,
  });

  const trimmedDebounced = debouncedQuery.trim();
  const search = useQuery({
    queryKey: ["directory-users", accessToken, trimmedDebounced],
    queryFn: () => apiDirectoryUsers(accessToken, trimmedDebounced),
    enabled: open && directorySearchAvailable && trimmedDebounced.length >= 2,
  });

  const create = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("Choose a member first");
      return apiMemberCreate(accessToken, presentationId, {
        entra_object_id: selected.entra_object_id,
        email: selected.email,
        display_name: selected.display_name,
        user_type: selected.user_type,
        role,
      });
    },
    onSuccess: async () => {
      setSelected(null);
      setQuery("");
      await qc.invalidateQueries({ queryKey: ["members", presentationId, accessToken] });
    },
  });

  const update = useMutation({
    mutationFn: ({ memberId, nextRole }: { memberId: string; nextRole: "editor" | "user" }) =>
      apiMemberUpdate(accessToken, presentationId, memberId, nextRole),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["members", presentationId, accessToken] });
    },
  });

  const revoke = useMutation({
    mutationFn: (memberId: string) => apiMemberDelete(accessToken, presentationId, memberId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["members", presentationId, accessToken] });
    },
  });

  const links = useQuery({
    queryKey: ["share-links", presentationId, accessToken],
    queryFn: () => apiShareLinksList(accessToken, presentationId),
    enabled: open,
  });

  const createLink = useMutation({
    mutationFn: () => {
      const parsed = Number.parseInt(shareExpiryHours, 10);
      return apiShareLinkCreate(accessToken, presentationId, {
        role: shareRole,
        expires_in_hours: Number.isFinite(parsed) ? parsed : null,
        note: shareNote.trim() || null,
      });
    },
    onSuccess: async (resp) => {
      setCreatedLink(resp);
      await qc.invalidateQueries({ queryKey: ["share-links", presentationId, accessToken] });
    },
  });

  const revokeLink = useMutation({
    mutationFn: (shareLinkId: string) =>
      apiShareLinkRevoke(accessToken, presentationId, shareLinkId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["share-links", presentationId, accessToken] });
    },
  });

  const results = useMemo(() => search.data?.items ?? [], [search.data]);
  const activeLinks = useMemo(
    () => (links.data?.items ?? []).filter((row) => row.revoked_at == null),
    [links.data?.items],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-modal-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="share-modal-title" className="font-heading text-lg font-semibold">
              Share deck
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Invited editors and viewers are listed below; the owner always has access. Search your
              directory to add someone new.
            </p>
          </div>
          <button
            type="button"
            className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-recessed"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <h3 className="mt-6 font-mono text-xs uppercase tracking-wide text-text-muted">
          Current members
        </h3>
        <div className="mt-2 rounded-sharp border border-border bg-bg-recessed p-3">
          {list.isLoading ? (
            <p className="font-mono text-sm text-text-muted">Loading…</p>
          ) : list.isError ? (
            <p className="text-sm text-accent-warning">{(list.error as Error).message}</p>
          ) : (list.data?.items ?? []).length === 0 ? (
            <p className="text-sm text-text-muted">No one else has access yet.</p>
          ) : (
            <ul className="space-y-2">
              {(list.data?.items ?? []).map((row: PresentationMemberDto) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-sharp border border-border bg-bg-elevated px-3 py-2"
                >
                  <div>
                    <p className="text-sm text-text-main">
                      {row.principal_display_name ?? row.principal_email}
                    </p>
                    <p className="font-mono text-xs text-text-muted">{row.principal_email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      className="min-w-[9rem] rounded-sharp border border-border bg-bg-recessed px-2 py-1 font-mono text-xs text-text-main outline-none ring-primary focus:ring-1"
                      value={row.role}
                      title={roleLabel(row.role)}
                      onChange={(e) =>
                        update.mutate({
                          memberId: row.id,
                          nextRole: e.target.value as "editor" | "user",
                        })
                      }
                      disabled={update.isPending}
                    >
                      {MEMBER_ROLE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="rounded-sharp border border-border px-2 py-1 font-mono text-xs uppercase tracking-wide hover:bg-bg-recessed disabled:opacity-40"
                      disabled={revoke.isPending}
                      onClick={() => revoke.mutate(row.id)}
                    >
                      Revoke
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mt-6 border-t border-border pt-6">
          <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Share links</h3>
          <p className="mt-1 text-sm text-text-muted">
            Create link-based access for external reviewers. Link tokens are revocable and never
            stored in plaintext.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <label className="grid gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Role
              <select
                className="rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                value={shareRole}
                onChange={(e) => setShareRole(e.target.value as "viewer" | "commenter" | "editor")}
              >
                {SHARE_LINK_ROLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Expires (hours)
              <input
                className="rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                inputMode="numeric"
                value={shareExpiryHours}
                onChange={(e) => setShareExpiryHours(e.target.value)}
              />
            </label>
            <label className="grid gap-1 font-mono text-xs uppercase tracking-wide text-text-muted md:col-span-2">
              Note (optional)
              <input
                className="rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                value={shareNote}
                onChange={(e) => setShareNote(e.target.value)}
                maxLength={500}
              />
            </label>
          </div>
          <div className="mt-3">
            <button
              type="button"
              className="rounded-sharp bg-primary/15 px-3 py-1.5 font-mono text-xs text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-40"
              disabled={createLink.isPending}
              onClick={() => createLink.mutate()}
            >
              {createLink.isPending ? "Creating link…" : "Create share link"}
            </button>
          </div>
          {createLink.error ? (
            <p className="mt-2 text-sm text-accent-warning" role="alert">
              {(createLink.error as Error).message}
            </p>
          ) : null}
          {createdLink ? (
            <div className="mt-3 rounded-sharp border border-border bg-bg-recessed p-3">
              <p className="font-mono text-xs text-text-muted">New link (copy now)</p>
              <p className="mt-1 break-all font-mono text-xs text-text-main">
                {createdLink.share_url}
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
                  onClick={() => void navigator.clipboard?.writeText(createdLink.share_url)}
                >
                  Copy URL
                </button>
                <button
                  type="button"
                  className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
                  onClick={() => setCreatedLink(null)}
                >
                  Dismiss
                </button>
              </div>
            </div>
          ) : null}
          <div className="mt-3 rounded-sharp border border-border bg-bg-recessed p-3">
            <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
              Active links
            </p>
            {links.isLoading ? (
              <p className="mt-2 text-sm text-text-muted">Loading links…</p>
            ) : links.isError ? (
              <p className="mt-2 text-sm text-accent-warning">{(links.error as Error).message}</p>
            ) : activeLinks.length === 0 ? (
              <p className="mt-2 text-sm text-text-muted">No active links.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {activeLinks.map((row: ShareLinkDto) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-sharp border border-border bg-bg-elevated px-3 py-2"
                  >
                    <div>
                      <p className="font-mono text-xs text-text-main">{shareRoleLabel(row.role)}</p>
                      <p className="font-mono text-[10px] text-text-muted">
                        Expires: {row.expires_at ?? "never"}
                        {row.note ? ` · ${row.note}` : ""}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded-sharp border border-border px-2 py-1 font-mono text-xs uppercase tracking-wide hover:bg-bg-recessed disabled:opacity-40"
                      disabled={revokeLink.isPending}
                      onClick={() => revokeLink.mutate(row.id)}
                    >
                      Revoke link
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mt-6 border-t border-border pt-6">
          <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Invite</h3>
          <p className="mt-1 text-sm text-text-muted">
            Search by name or email (at least two characters). Search runs after you pause typing.
            Pick someone, choose Viewer or Editor, then add them.
          </p>
          {!directorySearchAvailable ? (
            <p className="mt-3 rounded-sharp border border-accent-warning/40 bg-accent-warning/10 px-3 py-2 text-sm text-accent-warning">
              Directory search needs a Microsoft Entra sign-in (local accounts cannot call the
              tenant directory). Sign in with Entra to search, or ask someone with access to add
              members.
            </p>
          ) : null}

          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-end">
            <label className="flex flex-col gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Search
              <input
                className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Name or email"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={!directorySearchAvailable}
                autoFocus
              />
            </label>
            <label className="flex flex-col gap-1 font-mono text-xs uppercase tracking-wide text-text-muted">
              Access
              <select
                className="min-w-[9rem] rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                value={role}
                onChange={(e) => setRole(e.target.value as "editor" | "user")}
                title="Viewer: open and comment. Editor: upload versions and manage sharing."
              >
                {MEMBER_ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-40"
              disabled={!selected || create.isPending}
              onClick={() => create.mutate()}
            >
              Add member
            </button>
          </div>

          {create.error ? (
            <p className="mt-2 text-sm text-accent-warning" role="alert">
              {(create.error as Error).message}
            </p>
          ) : null}

          <div className="mt-4 rounded-sharp border border-border bg-bg-recessed p-3">
            <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Results</p>
            {query.trim().length < 2 ? (
              <p className="mt-2 text-sm text-text-muted">Type at least 2 characters to search.</p>
            ) : !directorySearchAvailable ? (
              <p className="mt-2 text-sm text-text-muted">
                Directory search is unavailable for this account.
              </p>
            ) : query.trim() !== trimmedDebounced ? (
              <p className="mt-2 text-sm text-text-muted">
                Paused — search runs after you stop typing…
              </p>
            ) : search.isFetching ? (
              <p className="mt-2 text-sm text-text-muted">Searching…</p>
            ) : search.isError ? (
              <p className="mt-2 text-sm text-accent-warning">{(search.error as Error).message}</p>
            ) : results.length ? (
              <ul className="mt-2 space-y-2">
                {results.map((row) => {
                  const active = selected?.entra_object_id === row.entra_object_id;
                  return (
                    <li key={row.entra_object_id}>
                      <button
                        type="button"
                        className={`flex w-full items-start justify-between rounded-sharp border px-3 py-2 text-left outline-none ring-primary focus-visible:ring-1 ${
                          active
                            ? "border-primary bg-primary/10"
                            : "border-border hover:bg-bg-elevated"
                        }`}
                        onClick={() => setSelected(row)}
                      >
                        <span>
                          <span className="block text-sm text-text-main">
                            {row.display_name ?? row.email}
                          </span>
                          <span className="block font-mono text-xs text-text-muted">
                            {row.email}
                          </span>
                        </span>
                        <span className="font-mono text-xs uppercase tracking-wide text-text-muted">
                          {row.user_type ?? "member"}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-text-muted">No matching tenant users found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
