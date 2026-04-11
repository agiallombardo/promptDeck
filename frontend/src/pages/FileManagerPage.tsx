import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiPresentationCreate, apiPresentationsList } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function FileManagerPage() {
  const token = useAuthStore((s) => s.accessToken)!;
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["presentations", token],
    queryFn: () => apiPresentationsList(token),
  });

  const create = useMutation({
    mutationFn: async () => {
      setError(null);
      const t = title.trim() || "Untitled deck";
      return apiPresentationCreate(token, t);
    },
    onSuccess: async () => {
      setTitle("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="font-heading text-xl font-semibold">Files</h1>

      <div className="mt-8 rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated">
        <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">
          New presentation
        </h2>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 font-mono text-xs text-text-muted">
            Title
            <input
              className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
              value={title}
              onChange={(ev) => setTitle(ev.target.value)}
              placeholder="Q4 narrative"
            />
          </label>
          <button
            type="button"
            disabled={create.isPending}
            onClick={() => create.mutate()}
            className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
          >
            {create.isPending ? "Creating…" : "Create"}
          </button>
        </div>
        {error ? (
          <p className="mt-3 text-sm text-accent-warning" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="mt-10">
        <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">Your decks</h2>
        {q.isLoading ? (
          <p className="mt-4 font-mono text-sm text-text-muted">Loading…</p>
        ) : q.isError ? (
          <p className="mt-4 text-sm text-accent-warning">{(q.error as Error).message}</p>
        ) : (
          <ul className="mt-4 divide-y divide-border rounded-sharp border border-border bg-bg-elevated">
            {q.data?.items.length ? (
              q.data.items.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div>
                    <p className="font-heading text-base font-medium">{p.title}</p>
                    <p className="font-mono text-xs text-text-muted">
                      {p.current_version_id ? "Has version" : "No upload yet"}
                    </p>
                  </div>
                  <Link
                    className="rounded-sharp border border-border px-3 py-1.5 font-mono text-sm text-primary hover:bg-primary/10"
                    to={`/p/${p.id}`}
                  >
                    Open
                  </Link>
                </li>
              ))
            ) : (
              <li className="px-4 py-6 text-sm text-text-muted">No presentations yet.</li>
            )}
          </ul>
        )}
      </div>
    </main>
  );
}
