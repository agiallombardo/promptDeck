import { Drawer } from "vaul";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { PresentationCanvas } from "../components/canvas/PresentationCanvas";
import { PresentationDeckHeader } from "../components/layout/PresentationDeckHeader";
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
  const shareToken = useShareAccessStore((s) => s.token);
  const sharePresentationId = useShareAccessStore((s) => s.presentationId);
  const shareRole = useShareAccessStore((s) => s.role);
  const token = deckAccessToken(id ?? "", accessToken, {
    token: shareToken,
    presentationId: sharePresentationId,
  })!;
  const isShareSession = Boolean(shareToken && id && sharePresentationId === id);
  const [shareOpen, setShareOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [mobileFeedbackOpen, setMobileFeedbackOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const [slideIndex, setSlideIndex] = useState(0);
  const [slideCount, setSlideCount] = useState(1);

  const canComment = isShareSession
    ? shareRole === "commenter" || shareRole === "editor"
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
    (count: number, _titles?: string[]) => {
      void _titles;
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

  const scrollThreadIntoView = useCallback((threadId: string) => {
    document.getElementById(`thread-card-${threadId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, []);

  const onThreadSelectFromCanvas = useCallback(
    (threadId: string) => {
      const narrow =
        typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
      if (narrow) {
        setMobileFeedbackOpen(true);
        requestAnimationFrame(() => scrollThreadIntoView(threadId));
      } else {
        scrollThreadIntoView(threadId);
      }
    },
    [scrollThreadIntoView],
  );

  const feedbackSidebarProps = {
    threads: threads.data?.items ?? [],
    isLoading: Boolean(pres.isLoading || !versionId || threads.isLoading),
    isRefreshing: threads.isFetching && !threads.isLoading,
    error: threadsError,
    canComment,
    currentUserId: user?.id ?? null,
    commentMode,
    onToggleCommentMode: () => {
      setCommentMode((v) => !v);
      setPendingPin(null);
    },
    pendingPin,
    draftNewThread,
    onDraftNewThread: setDraftNewThread,
    onSubmitNewThread: () => {
      if (!draftNewThread.trim() || !pendingPin || !embed.data) return;
      createThread.mutate({
        pin: pendingPin,
        versionId: embed.data.version_id,
        body: draftNewThread.trim(),
      });
    },
    onClearPending: () => {
      setPendingPin(null);
      setDraftNewThread("");
    },
    onRefresh: () => void qc.invalidateQueries({ queryKey: ["threads", id, token] }),
    replyDrafts,
    onReplyDraft: (threadId: string, value: string) =>
      setReplyDrafts((prev) => ({ ...prev, [threadId]: value })),
    onReply: handleReply,
    onResolve: (threadId: string) => resolveThread.mutate(threadId),
    onDeleteComment: (commentId: string) => deleteComment.mutate(commentId),
  };

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
        <PresentationDeckHeader
          title={pres.data?.title ?? "…"}
          isShareSession={isShareSession}
          shareRole={shareRole ?? null}
          showOwnerActions={Boolean(isOwner && pres.data?.current_version_id && accessToken)}
          onShare={() => setShareOpen(true)}
          onExport={() => setExportOpen(true)}
          slideIndex={slideIndex}
          slideCount={slideCount}
          canNavigate={Boolean(embed.data)}
          onPrev={() => go(slideIndex - 1)}
          onNext={() => go(slideIndex + 1)}
        />

        <main className="flex min-h-0 flex-1 flex-col md:flex-row">
          {!pres.data?.current_version_id ? (
            <div className="mx-auto w-full max-w-xl flex-1 px-4 py-10">
              <div className="rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated">
                <h2 className="font-heading text-lg font-semibold">Upload deck</h2>
                <p className="mt-2 text-sm text-text-muted">
                  One <span className="font-mono">.html</span> file, or a{" "}
                  <span className="font-mono">.zip</span> of a built site (e.g. Vite/npm export)
                  with <span className="font-mono">index.html</span> at the root or in a folder such
                  as <span className="font-mono">dist/</span>, plus your JS/CSS assets.
                </p>
                <label className="mt-4 flex cursor-pointer flex-col gap-2 font-mono text-xs uppercase tracking-wide text-text-muted">
                  File
                  <input
                    type="file"
                    accept=".html,.htm,.zip,text/html,application/zip"
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
                  onSelectThread={onThreadSelectFromCanvas}
                  onLongPressCommentMode={
                    canComment
                      ? () => {
                          setCommentMode(true);
                          setPendingPin(null);
                        }
                      : undefined
                  }
                />
              </div>
              <div className="hidden min-h-0 md:flex md:max-w-sm md:flex-shrink-0 md:flex-col">
                <FeedbackSidebar {...feedbackSidebarProps} />
              </div>
              <div className="md:hidden">
                <Drawer.Root open={mobileFeedbackOpen} onOpenChange={setMobileFeedbackOpen}>
                  <Drawer.Trigger asChild>
                    <button
                      type="button"
                      className="fixed bottom-5 right-5 z-30 rounded-sharp border border-border bg-bg-elevated px-4 py-2 font-mono text-xs shadow-elevated"
                    >
                      Threads
                    </button>
                  </Drawer.Trigger>
                  <Drawer.Portal>
                    <Drawer.Overlay className="fixed inset-0 z-40 bg-black/50" />
                    <Drawer.Content className="fixed inset-x-0 bottom-0 z-50 flex max-h-[90vh] flex-col rounded-t-2xl border border-border bg-bg-elevated pb-4">
                      <Drawer.Handle className="mx-auto mt-3 mb-2 h-1.5 w-10 rounded-full bg-border" />
                      <div className="min-h-0 flex-1 overflow-y-auto">
                        <FeedbackSidebar {...feedbackSidebarProps} embedded />
                      </div>
                    </Drawer.Content>
                  </Drawer.Portal>
                </Drawer.Root>
              </div>
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
