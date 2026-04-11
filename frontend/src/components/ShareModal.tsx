import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  apiDirectoryUsers,
  apiMemberCreate,
  apiMemberDelete,
  apiMembersList,
  apiMemberUpdate,
  type DirectoryUserDto,
  type PresentationMemberDto,
} from "../lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  accessToken: string;
  presentationId: string;
};

export function ShareModal({ open, onClose, accessToken, presentationId }: Props) {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<"editor" | "user">("user");
  const [selected, setSelected] = useState<DirectoryUserDto | null>(null);

  const list = useQuery({
    queryKey: ["members", presentationId, accessToken],
    queryFn: () => apiMembersList(accessToken, presentationId),
    enabled: open,
  });

  const search = useQuery({
    queryKey: ["directory-users", accessToken, query],
    queryFn: () => apiDirectoryUsers(accessToken, query.trim()),
    enabled: open && query.trim().length >= 2,
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

  const results = useMemo(() => search.data?.items ?? [], [search.data]);

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
              Search your tenant directory and grant a deck role to a specific member.
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

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-end">
          <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Search member
            <input
              className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main"
              placeholder="Name or email"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          </label>
          <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Role
            <select
              className="rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main"
              value={role}
              onChange={(e) => setRole(e.target.value as "editor" | "user")}
            >
              <option value="user">user</option>
              <option value="editor">editor</option>
            </select>
          </label>
          <button
            type="button"
            className="rounded-sharp border border-primary bg-primary/10 px-3 py-2 font-mono text-xs text-primary hover:bg-primary/20 disabled:opacity-40"
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
          <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Results</p>
          {query.trim().length < 2 ? (
            <p className="mt-2 text-sm text-text-muted">Type at least 2 characters to search.</p>
          ) : search.isLoading ? (
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
                      className={`flex w-full items-start justify-between rounded-sharp border px-3 py-2 text-left ${
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
                        <span className="block font-mono text-xs text-text-muted">{row.email}</span>
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
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

        <h3 className="mt-6 font-mono text-[10px] uppercase tracking-wide text-text-muted">
          Current members
        </h3>
        {list.isLoading ? (
          <p className="mt-2 font-mono text-sm text-text-muted">Loading…</p>
        ) : list.isError ? (
          <p className="mt-2 text-sm text-accent-warning">{(list.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {(list.data?.items ?? []).map((row: PresentationMemberDto) => (
              <li
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-sharp border border-border px-3 py-2"
              >
                <div>
                  <p className="text-sm text-text-main">
                    {row.principal_display_name ?? row.principal_email}
                  </p>
                  <p className="font-mono text-xs text-text-muted">{row.principal_email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    className="rounded-sharp border border-border bg-bg-recessed px-2 py-1 font-mono text-xs text-text-main"
                    value={row.role}
                    onChange={(e) =>
                      update.mutate({
                        memberId: row.id,
                        nextRole: e.target.value as "editor" | "user",
                      })
                    }
                    disabled={update.isPending}
                  >
                    <option value="user">user</option>
                    <option value="editor">editor</option>
                  </select>
                  <button
                    type="button"
                    className="rounded-sharp border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-wide hover:bg-bg-recessed disabled:opacity-40"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(row.id)}
                  >
                    Revoke
                  </button>
                </div>
              </li>
            ))}
            {(list.data?.items ?? []).length === 0 ? (
              <li className="font-mono text-sm text-text-muted">No shared members yet.</li>
            ) : null}
          </ul>
        )}
      </div>
    </div>
  );
}
