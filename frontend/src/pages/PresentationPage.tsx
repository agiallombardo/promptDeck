import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { SlideFrame } from "../components/canvas/SlideFrame";
import type { PendingPin } from "../components/feedback/FeedbackSidebar";
import { ExportModal } from "../components/ExportModal";
import { FeedbackSidebar } from "../components/feedback/FeedbackSidebar";
import { RequireDeckAccess } from "../components/RequireDeckAccess";
import { ShareModal } from "../components/ShareModal";
import {
  apiCommentCreate,
  apiCommentDelete,
  apiPresentationEmbed,
  apiPresentationGet,
  apiThreadCreate,
  apiThreadPatch,
  apiThreadsList,
  apiVersionUpload,
  iframeSrcForDev,
} from "../lib/api";
import { deckAccessToken } from "../lib/deckAuth";
import { postSetCommentMode, postSlideGoto } from "../lib/slidePostMessage";
import { useAuthStore } from "../stores/auth";
import { useShareAccessStore } from "../stores/shareAccess";

export default function PresentationPage() {
  const { id } = useParams<{ id: string }>();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const shareSlice = useShareAccessStore((s) => ({
    token: s.token,
    presentationId: s.presentationId,
    role: s.role,
  }));
  const token = deckAccessToken(id ?? "", accessToken, shareSlice)!;
  const isShareSession = Boolean(shareSlice.token && id && shareSlice.presentationId === id);
  const [shareOpen, setShareOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const qc = useQueryClient();
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const [slideIndex, setSlideIndex] = useState(0);
  const [slideCount, setSlideCount] = useState(1);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [commentMode, setCommentMode] = useState(false);
  const [pendingPin, setPendingPin] = useState<PendingPin | null>(null);
  const [draftNewThread, setDraftNewThread] = useState("");
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});

  const canComment = !isShareSession && user ? user.role !== "viewer" : false;

  const pres = useQuery({
    queryKey: ["presentation", id, token],
    queryFn: () => apiPresentationGet(token, id!),
    enabled: Boolean(id) && Boolean(token),
  });

  const embed = useQuery({
    queryKey: ["presentation-embed", id, token, pres.data?.current_version_id],
    queryFn: () => apiPresentationEmbed(token, id!),
    enabled: Boolean(id) && Boolean(pres.data?.current_version_id),
  });

  const threads = useQuery({
    queryKey: ["threads", id, token, pres.data?.current_version_id],
    queryFn: () => apiThreadsList(token, id!, pres.data?.current_version_id ?? null),
    enabled: Boolean(id) && Boolean(pres.data?.current_version_id),
  });

  const upload = useMutation({
    mutationFn: (file: File) => apiVersionUpload(token, id!, file),
    onSuccess: async () => {
      setUploadError(null);
      await qc.invalidateQueries({ queryKey: ["presentation", id, token] });
      await qc.invalidateQueries({ queryKey: ["presentation-embed", id, token] });
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  const createThread = useMutation({
    mutationFn: () => {
      if (!pendingPin || !embed.data) {
        throw new Error("Missing pin or version");
      }
      return apiThreadCreate(token, id!, {
        version_id: embed.data.version_id,
        slide_index: pendingPin.slide,
        anchor_x: pendingPin.x,
        anchor_y: pendingPin.y,
        first_comment: draftNewThread.trim(),
      });
    },
    onSuccess: async () => {
      setPendingPin(null);
      setDraftNewThread("");
      setCommentMode(false);
      await qc.invalidateQueries({ queryKey: ["threads", id, token] });
    },
  });

  const addReply = useMutation({
    mutationFn: ({ threadId, body }: { threadId: string; body: string }) =>
      apiCommentCreate(token, threadId, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", id, token] });
    },
  });

  const resolveThread = useMutation({
    mutationFn: (threadId: string) => apiThreadPatch(token, threadId, "resolved"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", id, token] });
    },
  });

  const deleteComment = useMutation({
    mutationFn: (commentId: string) => apiCommentDelete(token, commentId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", id, token] });
    },
  });

  const onManifest = useCallback((count: number) => {
    setSlideCount(Math.max(1, count));
    setSlideIndex(0);
  }, []);

  const onSlideClick = useCallback(
    (payload: { slide: number; x: number; y: number }) => {
      if (!commentMode || !canComment) return;
      setPendingPin({ slide: payload.slide, x: payload.x, y: payload.y });
    },
    [canComment, commentMode],
  );

  const iframeSrc = embed.data ? iframeSrcForDev(embed.data.iframe_src) : "";

  useEffect(() => {
    postSetCommentMode(iframeRef.current, commentMode);
  }, [commentMode, iframeSrc]);

  useEffect(() => {
    function onFocus() {
      void qc.invalidateQueries({ queryKey: ["threads", id, token] });
    }
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [qc, id, token]);

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        setSlideIndex((i) => {
          const next = Math.max(0, i - 1);
          postSlideGoto(iframeRef.current, next);
          return next;
        });
      }
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        setSlideIndex((i) => {
          const next = Math.min(slideCount - 1, i + 1);
          postSlideGoto(iframeRef.current, next);
          return next;
        });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [slideCount]);

  const go = (next: number) => {
    const clamped = Math.max(0, Math.min(slideCount - 1, next));
    setSlideIndex(clamped);
    postSlideGoto(iframeRef.current, clamped);
  };

  const threadsError =
    threads.error instanceof Error
      ? threads.error.message
      : threads.error
        ? String(threads.error)
        : null;

  const isOwner = Boolean(user && pres.data && pres.data.owner_id === user.id);

  function handleReply(threadId: string) {
    const body = (replyDrafts[threadId] ?? "").trim();
    if (!body) return;
    addReply.mutate(
      { threadId, body },
      {
        onSuccess: () => {
          setReplyDrafts((prev) => ({ ...prev, [threadId]: "" }));
        },
      },
    );
  }

  if (!id) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-void font-mono text-sm text-accent-warning">
        Missing presentation id
      </div>
    );
  }

  return (
    <RequireDeckAccess presentationId={id}>
      <div className="flex min-h-dvh flex-col bg-bg-void text-text-main">
        <header className="border-b border-border bg-bg-recessed px-4 py-3">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <Link className="font-mono text-sm text-text-muted hover:text-primary" to="/files">
                ← Files
              </Link>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wide text-primary">Deck</p>
                <h1 className="font-heading text-lg font-semibold leading-tight">
                  {pres.data?.title ?? "…"}
                </h1>
                {isShareSession ? (
                  <p className="mt-0.5 font-mono text-[10px] text-text-muted">
                    Shared access{shareSlice.role ? ` · ${shareSlice.role}` : ""}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {isOwner && pres.data?.current_version_id && accessToken ? (
                <>
                  <button
                    type="button"
                    className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
                    onClick={() => setShareOpen(true)}
                  >
                    Share
                  </button>
                  <button
                    type="button"
                    className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
                    onClick={() => setExportOpen(true)}
                  >
                    Export
                  </button>
                </>
              ) : null}
              <span className="font-mono text-xs text-text-muted">
                Slide {slideCount ? slideIndex + 1 : 0} / {slideCount || "—"}
              </span>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-40"
                  disabled={!embed.data || slideIndex <= 0}
                  onClick={() => go(slideIndex - 1)}
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-40"
                  disabled={!embed.data || slideIndex >= slideCount - 1}
                  onClick={() => go(slideIndex + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col md:flex-row">
          {!pres.data?.current_version_id ? (
            <div className="mx-auto w-full max-w-xl flex-1 px-4 py-10">
              <div className="rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated">
                <h2 className="font-heading text-lg font-semibold">Upload HTML</h2>
                <p className="mt-2 text-sm text-text-muted">
                  Add a single `.html` deck to preview slides in the canvas.
                </p>
                <label className="mt-4 flex cursor-pointer flex-col gap-2 font-mono text-xs uppercase tracking-wide text-text-muted">
                  File
                  <input
                    type="file"
                    accept=".html,text/html"
                    className="font-body text-sm text-text-main file:mr-3 file:rounded-sharp file:border file:border-border file:bg-bg-recessed file:px-3 file:py-2"
                    onChange={(ev) => {
                      const f = ev.target.files?.[0];
                      if (f) upload.mutate(f);
                    }}
                  />
                </label>
                {uploadError ? (
                  <p className="mt-3 text-sm text-accent-warning" role="alert">
                    {uploadError}
                  </p>
                ) : null}
                {upload.isPending ? (
                  <p className="mt-3 font-mono text-sm text-text-muted">Uploading…</p>
                ) : null}
              </div>
            </div>
          ) : pres.isError ? (
            <p className="flex-1 p-6 text-center text-sm text-accent-warning">
              {(pres.error as Error).message}
            </p>
          ) : embed.isError ? (
            <p className="flex-1 p-6 text-center text-sm text-accent-warning">
              {(embed.error as Error).message}
            </p>
          ) : (
            <>
              <div className="flex min-h-0 flex-1 flex-col px-4 py-6">
                <div
                  className="relative mx-auto w-full max-w-6xl flex-1 overflow-hidden rounded-sharp shadow-elevated ring-1 ring-border"
                  style={{ aspectRatio: "16 / 9" }}
                >
                  {iframeSrc ? (
                    <SlideFrame
                      ref={iframeRef}
                      src={iframeSrc}
                      onManifest={onManifest}
                      onSlideClick={onSlideClick}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center bg-bg-recessed font-mono text-sm text-text-muted">
                      Loading canvas…
                    </div>
                  )}
                </div>
              </div>
              <FeedbackSidebar
                threads={threads.data?.items ?? []}
                isLoading={threads.isLoading}
                error={threadsError}
                canComment={canComment}
                currentUserId={user?.id ?? null}
                commentMode={commentMode}
                onToggleCommentMode={() => {
                  setCommentMode((v) => !v);
                  setPendingPin(null);
                }}
                pendingPin={pendingPin}
                draftNewThread={draftNewThread}
                onDraftNewThread={setDraftNewThread}
                onSubmitNewThread={() => {
                  if (!draftNewThread.trim()) return;
                  createThread.mutate();
                }}
                onClearPending={() => {
                  setPendingPin(null);
                  setDraftNewThread("");
                }}
                onRefresh={() => void qc.invalidateQueries({ queryKey: ["threads", id, token] })}
                replyDrafts={replyDrafts}
                onReplyDraft={(threadId, value) =>
                  setReplyDrafts((prev) => ({ ...prev, [threadId]: value }))
                }
                onReply={handleReply}
                onResolve={(threadId) => resolveThread.mutate(threadId)}
                onDeleteComment={(commentId) => deleteComment.mutate(commentId)}
              />
            </>
          )}
        </main>
      </div>
      {isOwner && accessToken ? (
        <>
          <ShareModal
            open={shareOpen}
            onClose={() => setShareOpen(false)}
            accessToken={accessToken}
            presentationId={id}
          />
          <ExportModal
            open={exportOpen}
            onClose={() => setExportOpen(false)}
            accessToken={accessToken}
            presentationId={id}
            versionId={pres.data?.current_version_id ?? null}
          />
        </>
      ) : null}
    </RequireDeckAccess>
  );
}
