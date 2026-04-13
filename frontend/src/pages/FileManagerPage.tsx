import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { formatDurationSeconds, useWallClockElapsed } from "../hooks/useDeckPromptJobTimers";
import { DeckPromptTemplateChips } from "../components/DeckPromptTemplateChips";
import { RecentDeckPreviews } from "../components/RecentDeckPreviews";
import { ShareModal } from "../components/ShareModal";
import {
  apiPresentationCreate,
  apiPresentationDelete,
  apiPresentationGenerateDiagramFromPrompt,
  apiPresentationGenerateFromPrompt,
  apiPresentationsList,
  apiVersionUpload,
} from "../lib/api";
import { readRecentDecks, RECENT_DECKS_CHANGED, removeRecentDeck } from "../lib/recentDecks";
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
  const [createKind, setCreateKind] = useState<"deck" | "diagram">("deck");
  const [title, setTitle] = useState("");
  const [deckPrompt, setDeckPrompt] = useState("");
  const [diagramPrompt, setDiagramPrompt] = useState("");
  const [recentDecks, setRecentDecks] = useState(readRecentDecks);
  const [error, setError] = useState<string | null>(null);
  const [sharePresentationId, setSharePresentationId] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["presentations", token],
    queryFn: () => apiPresentationsList(token),
  });

  useEffect(() => {
    function refreshRecent() {
      setRecentDecks(readRecentDecks());
    }
    window.addEventListener(RECENT_DECKS_CHANGED, refreshRecent);
    window.addEventListener("focus", refreshRecent);
    return () => {
      window.removeEventListener(RECENT_DECKS_CHANGED, refreshRecent);
      window.removeEventListener("focus", refreshRecent);
    };
  }, []);

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

  const createAndImportDiagram = useMutation({
    mutationFn: async (file: File) => {
      setError(null);
      const docTitle = deckTitleFromUpload(title, file);
      const pres = await apiPresentationCreate(token, docTitle, "diagram");
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
      const p = deckPrompt.trim();
      if (!p) {
        throw new Error("Enter a prompt describing the deck you want.");
      }
      return apiPresentationGenerateFromPrompt(token, {
        title: normalizeDeckTitle(title),
        prompt: p,
      });
    },
    onSuccess: async (data) => {
      setDeckPrompt("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
      navigate(`/p/${data.presentation.id}?deckJob=${data.job.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const generateSubmitElapsed = useWallClockElapsed(generateFromPrompt.isPending);

  const generateDiagramFromPrompt = useMutation({
    mutationFn: async () => {
      setError(null);
      const trimmedTitle = title.trim();
      if (!trimmedTitle) {
        throw new Error("Enter a title for the new diagram.");
      }
      const p = diagramPrompt.trim();
      if (!p) {
        throw new Error("Enter a prompt describing the diagram you want.");
      }
      return apiPresentationGenerateDiagramFromPrompt(token, {
        title: normalizeDeckTitle(title),
        prompt: p,
      });
    },
    onSuccess: async (data) => {
      setDiagramPrompt("");
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
      navigate(`/p/${data.presentation.id}?deckJob=${data.job.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const generateDiagramElapsed = useWallClockElapsed(generateDiagramFromPrompt.isPending);

  const remove = useMutation({
    mutationFn: async (presentationId: string) => {
      setError(null);
      await apiPresentationDelete(token, presentationId);
    },
    onSuccess: async (_void, presentationId) => {
      removeRecentDeck(presentationId);
      await qc.invalidateQueries({ queryKey: ["presentations", token] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <main className="mx-auto w-full max-w-[min(100%,64rem)] px-4 py-8 sm:px-6 sm:py-10">
      <h1 className="font-heading text-[clamp(1.25rem,1rem+1vw,1.5rem)] font-semibold">Files</h1>

      {generateFromPrompt.isPending || generateDiagramFromPrompt.isPending ? (
        <div className="mt-4 rounded-sharp border border-border bg-bg-elevated px-3 py-2 shadow-elevated">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-mono text-xs text-text-muted">
              {generateDiagramFromPrompt.isPending
                ? "Starting AI diagram generation…"
                : "Starting AI deck generation…"}
            </p>
            <p className="font-mono text-[11px] text-primary tabular-nums">
              {formatDurationSeconds(
                generateDiagramFromPrompt.isPending
                  ? generateDiagramElapsed
                  : generateSubmitElapsed,
              )}{" "}
              on this step
            </p>
          </div>
        </div>
      ) : null}

      <div className="mt-6 rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated sm:mt-8 sm:p-6">
        <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">
          New presentation or diagram
        </h2>
        <fieldset className="mt-4">
          <legend className="sr-only">What to create</legend>
          <div className="flex flex-wrap gap-4 font-mono text-xs text-text-main">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="createKind"
                checked={createKind === "deck"}
                onChange={() => setCreateKind("deck")}
                disabled={generateFromPrompt.isPending || generateDiagramFromPrompt.isPending}
              />
              Presentation
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="createKind"
                checked={createKind === "diagram"}
                onChange={() => setCreateKind("diagram")}
                disabled={generateFromPrompt.isPending || generateDiagramFromPrompt.isPending}
              />
              Diagram
            </label>
          </div>
        </fieldset>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1 font-mono text-xs text-text-muted">
            Title
            <input
              className="rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
              value={title}
              onChange={(ev) => setTitle(ev.target.value)}
              placeholder={createKind === "deck" ? "Q4 narrative" : "Payments system architecture"}
              maxLength={MAX_TITLE_LEN}
            />
          </label>
        </div>
        {createKind === "deck" ? (
          <div className="mt-6 border-t border-border pt-6">
            <DeckPromptTemplateChips
              variant="new_deck"
              className="flex flex-wrap gap-2"
              disabled={generateFromPrompt.isPending}
              onPick={(body) => setDeckPrompt(body)}
            />
            <label className="mt-4 flex flex-col gap-1 font-mono text-xs text-text-muted">
              AI prompt
              <textarea
                className="min-h-[100px] w-full resize-y rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                value={deckPrompt}
                onChange={(ev) => setDeckPrompt(ev.target.value)}
                placeholder="Describe the deck you want — audience, sections, tone, slide count…"
                disabled={generateFromPrompt.isPending}
                maxLength={16000}
              />
            </label>
          </div>
        ) : (
          <div className="mt-6 border-t border-border pt-6">
            <DeckPromptTemplateChips
              variant="new_diagram"
              className="flex flex-wrap gap-2"
              disabled={generateDiagramFromPrompt.isPending}
              onPick={(body) => setDiagramPrompt(body)}
            />
            <label className="mt-4 flex flex-col gap-1 font-mono text-xs text-text-muted">
              Diagram prompt
              <textarea
                className="min-h-[100px] w-full resize-y rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
                value={diagramPrompt}
                onChange={(ev) => setDiagramPrompt(ev.target.value)}
                placeholder="Describe the diagram scope, entities, and flows..."
                disabled={generateDiagramFromPrompt.isPending}
                maxLength={16000}
              />
            </label>
          </div>
        )}
        <button
          type="button"
          disabled={
            createAndUpload.isPending ||
            createAndImportDiagram.isPending ||
            generateFromPrompt.isPending ||
            generateDiagramFromPrompt.isPending
          }
          onClick={() =>
            createKind === "deck" ? generateFromPrompt.mutate() : generateDiagramFromPrompt.mutate()
          }
          className="mt-4 rounded-sharp border border-primary bg-primary/15 px-4 py-2 font-mono text-sm font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/25 disabled:opacity-50"
        >
          {createKind === "deck"
            ? generateFromPrompt.isPending
              ? "Starting generation…"
              : "Generate with AI"
            : generateDiagramFromPrompt.isPending
              ? "Starting generation…"
              : "Generate diagram"}
        </button>
        <div className="mt-4 border-t border-border pt-4">
          <label
            htmlFor={uploadInputId}
            className="font-mono text-xs uppercase tracking-wide text-text-muted"
          >
            {createKind === "deck" ? "Upload HTML or zip bundle" : "Or import source file"}
          </label>
          <input
            key={createKind}
            id={uploadInputId}
            type="file"
            accept={
              createKind === "deck"
                ? ".html,.htm,.zip,text/html,application/zip"
                : ".json,.pdf,.png,.jpg,.jpeg,.webp,.gif,.bmp,.svg,.drawio,.vsdx,.vdx,.graphml,.dot,.mmd,.puml,.uml,.xml,.yaml,.yml,.csv,.txt,.md,.zip"
            }
            disabled={
              (createKind === "deck"
                ? createAndUpload.isPending
                : createAndImportDiagram.isPending) ||
              generateFromPrompt.isPending ||
              generateDiagramFromPrompt.isPending
            }
            className="mt-2 block w-full max-w-md font-body text-sm text-text-main file:mr-3 file:rounded-sharp file:border file:border-border file:bg-bg-recessed file:px-3 file:py-2"
            onChange={(ev) => {
              const f = ev.target.files?.[0];
              ev.target.value = "";
              if (!f) return;
              if (createKind === "deck") {
                createAndUpload.mutate(f);
              } else {
                createAndImportDiagram.mutate(f);
              }
            }}
          />
          {createKind === "deck" && createAndUpload.isPending ? (
            <p className="mt-2 font-mono text-sm text-text-muted">Creating deck and uploading…</p>
          ) : null}
          {createKind === "diagram" && createAndImportDiagram.isPending ? (
            <p className="mt-2 font-mono text-sm text-text-muted">
              Creating diagram and importing…
            </p>
          ) : null}
        </div>
        {error ? (
          <p className="mt-3 text-sm text-accent-warning" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <RecentDeckPreviews accessToken={token} entries={recentDecks} />

      <div className="mt-10">
        <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">
          Your presentations and shares
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
                      {(p.kind ?? "deck").toUpperCase()} · Role: {p.current_user_role ?? "user"} ·{" "}
                      {p.current_version_id ? "Has version" : "No content yet"}
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
                          if (!window.confirm(`Delete “${p.title}”? This cannot be undone.`)) {
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
