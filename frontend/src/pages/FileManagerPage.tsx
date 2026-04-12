import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { DeckPromptTemplateChips } from "../components/DeckPromptTemplateChips";
import { ShareModal } from "../components/ShareModal";
import {
  apiPresentationCreate,
  apiPresentationDelete,
  apiPresentationGenerateFromPrompt,
  apiPresentationsList,
  apiVersionUpload,
} from "../lib/api";
import { useAuthStore } from "../stores/auth";

const DEFAULT_TITLE = "Untitled deck";
const MAX_TITLE_LEN = 500;

function normalizeDeckTitle(raw: string): string {
  const t = raw.trim();
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

function canManageDeck(role: string | null | undefined): boolean {
  return role === "owner" || role === "editor" || role === "admin";
}

function canDeleteDeck(role: string | null | undefined): boolean {
  return role === "owner" || role === "admin";
}

export default function FileManagerPage() {
  const token = useAuthStore((s) => s.accessToken)!;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const uploadInputId = useId();
  const [title, setTitle] = useState("");
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sharePresentationId, setSharePresentationId] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["presentations", token],
    queryFn: () => apiPresentationsList(token),
  });

  const create = useMutation({
    mutationFn: async () => {
      setError(null);
      const trimmed = title.trim();
      if (!trimmed) {
        throw new Error("Enter a title to create an empty deck.");
      }
      return apiPresentationCreate(token, normalizeDeckTitle(title));
    },
    onSuccess: async (data) => {
      setTitle("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
      navigate(`/p/${data.id}`);
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

  const generateFromPrompt = useMutation({
    mutationFn: async () => {
      setError(null);
      const trimmedTitle = title.trim();
      if (!trimmedTitle) {
        throw new Error("Enter a title for the new deck.");
      }
      const p = generatePrompt.trim();
      if (!p) {
        throw new Error("Enter a prompt describing the deck you want.");
      }
      return apiPresentationGenerateFromPrompt(token, {
        title: normalizeDeckTitle(title),
        prompt: p,
      });
    },
    onSuccess: async (data) => {
      setGeneratePrompt("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
      navigate(`/p/${data.presentation.id}?deckJob=${data.job.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const remove = useMutation({
    mutationFn: async (presentationId: string) => {
      setError(null);
      await apiPresentationDelete(token, presentationId);
    },
    onSuccess: async () => {
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
        <p className="mt-2 text-sm text-text-muted">
          Create an empty deck or upload a single <span className="font-mono">.html</span> file or a{" "}
          <span className="font-mono">.zip</span> bundle that includes{" "}
          <span className="font-mono">index.html</span>. Upload creates the deck and its first
          version in one step.
        </p>
        <ul className="mt-3 list-none space-y-2 text-sm text-text-muted">
          <li className="flex gap-3">
            <span className="w-28 shrink-0 font-mono text-xs uppercase tracking-wide text-text-main">
              Empty deck
            </span>
            <span>Enter a title first — it is required for an empty deck.</span>
          </li>
          <li className="flex gap-3">
            <span className="w-28 shrink-0 font-mono text-xs uppercase tracking-wide text-text-main">
              Upload
            </span>
            <span>
              Title is optional. If you leave it blank, the file name becomes the deck title, or{" "}
              <span className="font-mono text-text-main">{DEFAULT_TITLE}</span> when the name cannot
              be used.
            </span>
          </li>
        </ul>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 font-mono text-xs text-text-muted">
            Title
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
            disabled={create.isPending || createAndUpload.isPending || generateFromPrompt.isPending}
            onClick={() => create.mutate()}
            className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
          >
            {create.isPending ? "Creating…" : "Create empty deck"}
          </button>
        </div>
        <div className="mt-6 border-t border-border pt-6">
          <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">
            Generate new deck with AI
          </h3>
          <p className="mt-2 text-sm text-text-muted">
            Uses the same AI pipeline as{" "}
            <span className="font-mono text-text-main">Edit with prompt</span> on an open deck. You
            need a title and a brief; a starter file is created, then replaced when generation
            finishes.
          </p>
          <label className="mt-3 flex flex-col gap-1 font-mono text-xs text-text-muted">
            Prompt
            <textarea
              className="min-h-[100px] w-full resize-y rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
              value={generatePrompt}
              onChange={(ev) => setGeneratePrompt(ev.target.value)}
              placeholder="Describe the deck you want — audience, sections, tone, slide count…"
              disabled={generateFromPrompt.isPending}
              maxLength={16000}
            />
          </label>
          <p className="mt-2 font-mono text-[11px] text-text-muted">Quick-start templates</p>
          <DeckPromptTemplateChips
            className="mt-2 flex flex-wrap gap-2"
            disabled={generateFromPrompt.isPending}
            onPick={(body) => setGeneratePrompt(body)}
          />
          <button
            type="button"
            disabled={create.isPending || createAndUpload.isPending || generateFromPrompt.isPending}
            onClick={() => generateFromPrompt.mutate()}
            className="mt-4 rounded-sharp border border-primary bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
          >
            {generateFromPrompt.isPending ? "Starting generation…" : "Generate with AI"}
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
            disabled={createAndUpload.isPending || create.isPending || generateFromPrompt.isPending}
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
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      className="rounded-sharp border border-border px-3 py-1.5 font-mono text-sm text-primary hover:bg-primary/10"
                      to={`/p/${p.id}`}
                    >
                      Open
                    </Link>
                    {canManageDeck(p.current_user_role) ? (
                      <button
                        type="button"
                        className="rounded-sharp border border-border px-3 py-1.5 font-mono text-sm text-primary hover:bg-primary/10"
                        onClick={() => setSharePresentationId(p.id)}
                      >
                        Share
                      </button>
                    ) : null}
                    {canDeleteDeck(p.current_user_role) ? (
                      <button
                        type="button"
                        disabled={remove.isPending}
                        className="rounded-sharp border border-border px-3 py-1.5 font-mono text-sm text-accent-warning hover:bg-accent-warning/10 disabled:opacity-50"
                        onClick={() => {
                          if (!window.confirm(`Delete deck “${p.title}”? This cannot be undone.`)) {
                            return;
                          }
                          remove.mutate(p.id);
                        }}
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
                </li>
              ))
            ) : (
              <li className="px-4 py-6 text-sm text-text-muted">No presentations yet.</li>
            )}
          </ul>
        )}
      </div>

      {sharePresentationId ? (
        <ShareModal
          open
          onClose={() => setSharePresentationId(null)}
          accessToken={token}
          presentationId={sharePresentationId}
        />
      ) : null}
    </main>
  );
}
