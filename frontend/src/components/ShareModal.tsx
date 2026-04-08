import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiShareCreate, apiShareRevoke, apiSharesList, type ShareLinkDto } from "../lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  accessToken: string;
  presentationId: string;
};

export function ShareModal({ open, onClose, accessToken, presentationId }: Props) {
  const qc = useQueryClient();
  const [role, setRole] = useState("viewer");
  const [lastCreatedUrl, setLastCreatedUrl] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ["shares", presentationId, accessToken],
    queryFn: () => apiSharesList(accessToken, presentationId),
    enabled: open,
  });

  const create = useMutation({
    mutationFn: () => apiShareCreate(accessToken, presentationId, { role }),
    onSuccess: (row) => {
      const path = `/share/${encodeURIComponent(row.token)}`;
      setLastCreatedUrl(`${window.location.origin}${path}`);
      void qc.invalidateQueries({ queryKey: ["shares", presentationId, accessToken] });
    },
  });

  const revoke = useMutation({
    mutationFn: (shareId: string) => apiShareRevoke(accessToken, presentationId, shareId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["shares", presentationId, accessToken] });
    },
  });

  if (!open) return null;

  function copy(text: string) {
    void navigator.clipboard.writeText(text);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-modal-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="share-modal-title" className="font-heading text-lg font-semibold">
              Share deck
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Create a link others can open without an account. Copy the URL once — it is not shown
              again in the list.
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

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Role
            <select
              className="rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-body text-sm text-text-main"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              autoFocus
            >
              <option value="viewer">viewer</option>
              <option value="commenter">commenter</option>
              <option value="editor">editor</option>
            </select>
          </label>
          <button
            type="button"
            className="rounded-sharp border border-primary bg-primary/10 px-3 py-2 font-mono text-xs text-primary hover:bg-primary/20 disabled:opacity-40"
            disabled={create.isPending}
            onClick={() => create.mutate()}
          >
            Create link
          </button>
        </div>
        {create.error ? (
          <p className="mt-2 text-sm text-accent-warning" role="alert">
            {(create.error as Error).message}
          </p>
        ) : null}
        {lastCreatedUrl ? (
          <div className="mt-4 rounded-sharp border border-border bg-bg-recessed p-3">
            <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
              New link (copy now)
            </p>
            <p className="mt-2 break-all font-mono text-xs text-text-main">{lastCreatedUrl}</p>
            <button
              type="button"
              className="mt-3 rounded-sharp border border-border px-3 py-1 font-mono text-xs hover:bg-bg-elevated"
              onClick={() => copy(lastCreatedUrl)}
            >
              Copy URL
            </button>
          </div>
        ) : null}

        <h3 className="mt-6 font-mono text-[10px] uppercase tracking-wide text-text-muted">
          Active links
        </h3>
        {list.isLoading ? (
          <p className="mt-2 font-mono text-sm text-text-muted">Loading…</p>
        ) : list.isError ? (
          <p className="mt-2 text-sm text-accent-warning">{(list.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {(list.data?.items ?? []).map((row: ShareLinkDto) => (
              <li
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-sharp border border-border px-3 py-2"
              >
                <div className="font-mono text-xs text-text-main">
                  <span className="text-text-muted">{row.role}</span>
                  {row.revoked_at ? (
                    <span className="ml-2 text-accent-warning">revoked</span>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="rounded-sharp border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-wide hover:bg-bg-recessed disabled:opacity-40"
                  disabled={Boolean(row.revoked_at) || revoke.isPending}
                  onClick={() => revoke.mutate(row.id)}
                >
                  Revoke
                </button>
              </li>
            ))}
            {(list.data?.items ?? []).length === 0 ? (
              <li className="font-mono text-sm text-text-muted">No links yet.</li>
            ) : null}
          </ul>
        )}
      </div>
    </div>
  );
}
