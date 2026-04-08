import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PresentationCanvas } from "../components/canvas/PresentationCanvas";
import { ExportModal } from "../components/ExportModal";
import { FeedbackSidebar } from "../components/feedback/FeedbackSidebar";
import { RequireDeckAccess } from "../components/RequireDeckAccess";
import { ShareModal } from "../components/ShareModal";
import { useComments } from "../hooks/useComments";
import { usePresentation } from "../hooks/usePresentation";
import { ApiError } from "../lib/api";
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
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const [slideIndex, setSlideIndex] = useState(0);
  const [slideCount, setSlideCount] = useState(1);

  const canComment = isShareSession
    ? shareSlice.role === "commenter" || shareSlice.role === "editor"
    : Boolean(user && user.role !== "viewer");

  const { pres, embed, upload, uploadError, iframeSrc, qc } = usePresentation(id, token);
  const versionId = pres.data?.current_version_id;

  const {
    threads,
    commentMode,
    setCommentMode,
    pendingPin,
    setPendingPin,
    draftNewThread,
    setDraftNewThread,
    replyDrafts,
    setReplyDrafts,
    createThread,
    addReply,
    resolveThread,
    deleteComment,
  } = useComments(id ?? "", token, versionId);

  const onManifest = useCallback(
    (count: number) => {
      setSlideCount(Math.max(1, count));
      setSlideIndex(0);
      queueMicrotask(() => postSetCommentMode(iframeRef.current, commentMode));
    },
    [commentMode],
  );

  const onSlideClick = useCallback(
    (payload: { slide: number; x: number; y: number }) => {
      if (!commentMode || !canComment) return;
      setPendingPin({ slide: payload.slide, x: payload.x, y: payload.y });
    },
    [canComment, commentMode, setPendingPin],
  );

  useEffect(() => {
    postSetCommentMode(iframeRef.current, commentMode);
  }, [commentMode, iframeSrc]);

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
    threads.error instanceof ApiError
      ? threads.error.message +
        (threads.error.requestId ? ` · Request ID: ${threads.error.requestId}` : "")
      : threads.error instanceof Error
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

  function scrollThreadIntoView(threadId: string) {
    document.getElementById(`thread-card-${threadId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
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
              {pres.error instanceof Error ? pres.error.message : String(pres.error)}
            </p>
          ) : embed.isError ? (
            <p className="flex-1 p-6 text-center text-sm text-accent-warning">
              {embed.error instanceof Error ? embed.error.message : String(embed.error)}
            </p>
          ) : (
            <>
              <div className="flex min-h-0 flex-1 flex-col px-4 py-6">
                <PresentationCanvas
                  iframeSrc={iframeSrc}
                  iframeRef={iframeRef}
                  onManifest={onManifest}
                  onSlideClick={onSlideClick}
                  commentMode={commentMode}
                  canComment={canComment}
                  threads={threads.data?.items ?? []}
                  slideIndex={slideIndex}
                  onSelectThread={scrollThreadIntoView}
                />
              </div>
              <FeedbackSidebar
                threads={threads.data?.items ?? []}
                isLoading={threads.isLoading}
                isRefreshing={threads.isFetching && !threads.isLoading}
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
                  if (!draftNewThread.trim() || !pendingPin || !embed.data) return;
                  createThread.mutate({
                    pin: pendingPin,
                    versionId: embed.data.version_id,
                    body: draftNewThread.trim(),
                  });
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
