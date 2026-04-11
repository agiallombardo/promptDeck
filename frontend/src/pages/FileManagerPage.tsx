import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiPresentationCreate, apiPresentationsList, apiVersionUpload } from "../lib/api";
import { useAuthStore } from "../stores/auth";

const DEFAULT_TITLE = "Untitled deck";
const MAX_TITLE_LEN = 500;

function deckTitleForCreate(raw: string): string {
  const t = raw.trim();
  if (!t) return DEFAULT_TITLE;
  return t.length > MAX_TITLE_LEN ? t.slice(0, MAX_TITLE_LEN) : t;
}

function deckTitleFromUpload(rawField: string, file: File): string {
  const typed = rawField.trim();
  if (typed) {
    return typed.length > MAX_TITLE_LEN ? typed.slice(0, MAX_TITLE_LEN) : typed;
  }
  const base = file.name.replace(/\.(html?|zip)$/i, "").trim();
  if (!base) return DEFAULT_TITLE;
  return base.length > MAX_TITLE_LEN ? base.slice(0, MAX_TITLE_LEN) : base;
}

export default function FileManagerPage() {
  const token = useAuthStore((s) => s.accessToken)!;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const uploadInputId = useId();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["presentations", token],
    queryFn: () => apiPresentationsList(token),
  });

  const create = useMutation({
    mutationFn: async () => {
      setError(null);
      return apiPresentationCreate(token, deckTitleForCreate(title));
    },
    onSuccess: async () => {
      setTitle("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const createAndUpload = useMutation({
    mutationFn: async (file: File) => {
      setError(null);
      const deckTitle = deckTitleFromUpload(title, file);
      const pres = await apiPresentationCreate(token, deckTitle);
      await apiVersionUpload(token, pres.id, file);
      return pres.id;
    },
    onSuccess: async (presentationId) => {
      setTitle("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
      navigate(`/p/${presentationId}`);
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
        <p className="mt-2 text-sm text-text-muted">
          A name is optional. Leave the title blank to use{" "}
          <span className="font-mono">{DEFAULT_TITLE}</span>, or upload a single{" "}
          <span className="font-mono">.html</span> or a <span className="font-mono">.zip</span> site
          bundle (needs <span className="font-mono">index.html</span> plus assets). Creates the deck
          and first version in one step; the file name is the deck title when the title field is
          empty.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 font-mono text-xs text-text-muted">
            Title{" "}
            <span className="font-body font-normal normal-case text-text-muted">(optional)</span>
            <input
              className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
              value={title}
              onChange={(ev) => setTitle(ev.target.value)}
              placeholder="Q4 narrative"
              maxLength={MAX_TITLE_LEN}
            />
          </label>
          <button
            type="button"
            disabled={create.isPending || createAndUpload.isPending}
            onClick={() => create.mutate()}
            className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
          >
            {create.isPending ? "Creating…" : "Create empty deck"}
          </button>
        </div>
        <div className="mt-4 border-t border-border pt-4">
          <label
            htmlFor={uploadInputId}
            className="font-mono text-xs uppercase tracking-wide text-text-muted"
          >
            Upload HTML or zip bundle
          </label>
          <input
            id={uploadInputId}
            type="file"
            accept=".html,.htm,.zip,text/html,application/zip"
            disabled={createAndUpload.isPending || create.isPending}
            className="mt-2 block w-full max-w-md font-body text-sm text-text-main file:mr-3 file:rounded-sharp file:border file:border-border file:bg-bg-recessed file:px-3 file:py-2"
            onChange={(ev) => {
              const f = ev.target.files?.[0];
              ev.target.value = "";
              if (f) createAndUpload.mutate(f);
            }}
          />
          {createAndUpload.isPending ? (
            <p className="mt-2 font-mono text-sm text-text-muted">Creating deck and uploading…</p>
          ) : null}
        </div>
        {error ? (
          <p className="mt-3 text-sm text-accent-warning" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="mt-10">
        <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">
          Your decks and shares
        </h2>
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
                      Role: {p.current_user_role ?? "user"} ·{" "}
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
