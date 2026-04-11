import { Drawer } from "vaul";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { PresentationCanvas } from "../components/canvas/PresentationCanvas";
import { ExportModal } from "../components/ExportModal";
import { FeedbackSidebar } from "../components/feedback/FeedbackSidebar";
import { RequireDeckAccess } from "../components/RequireDeckAccess";
import { PresentationDeckHeader } from "../components/layout/PresentationDeckHeader";
import { ShareModal } from "../components/ShareModal";
import { useComments } from "../hooks/useComments";
import { usePresentation } from "../hooks/usePresentation";
import { ApiError } from "../lib/api";
import { postSetCommentMode, postSlideGoto } from "../lib/slidePostMessage";
import { useAuthStore } from "../stores/auth";

export default function PresentationPage() {
  const { id } = useParams<{ id: string }>();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const [shareOpen, setShareOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [mobileFeedbackOpen, setMobileFeedbackOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const [slideIndex, setSlideIndex] = useState(0);
  const [slideCount, setSlideCount] = useState(1);

  const { pres, embed, upload, uploadError, iframeSrc } = usePresentation(id, accessToken);
  const versionId = pres.data?.current_version_id;
  const accessRole = pres.data?.current_user_role ?? null;
  const canComment = accessRole === "owner" || accessRole === "editor" || accessRole === "admin";
  const canManage = canComment;

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
  } = useComments(id ?? "", accessToken ?? "", versionId);

  const onManifest = useCallback(
    (count: number, _titles: string[]) => {
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
    onRefresh: () => {
      void threads.refetch();
    },
    replyDrafts,
    onReplyDraft: (threadId: string, body: string) =>
      setReplyDrafts((prev) => ({ ...prev, [threadId]: body })),
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
      <div className="min-h-dvh bg-bg-void text-text-main">
        <PresentationDeckHeader
          title={pres.data?.title ?? "Presentation"}
          accessRole={accessRole}
          showShareAction={Boolean(canManage && accessToken)}
          showExportAction={Boolean(canManage && accessToken && pres.data?.current_version_id)}
          onShare={() => setShareOpen(true)}
          onExport={() => setExportOpen(true)}
          slideIndex={slideIndex}
          slideCount={slideCount}
          canNavigate={Boolean(embed.data?.slide_count)}
          onPrev={() => go(slideIndex - 1)}
          onNext={() => go(slideIndex + 1)}
        />

        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-4 md:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-4">
            <PresentationCanvas
              iframeRef={iframeRef}
              iframeSrc={iframeSrc}
              slideIndex={slideIndex}
              commentMode={commentMode}
              canComment={canComment}
              threads={threads.data?.items ?? []}
              onManifest={onManifest}
              onSelectThread={onThreadSelectFromCanvas}
              onSlideClick={onSlideClick}
              onLongPressCommentMode={() => setCommentMode(true)}
            />
            {uploadError ? (
              <p className="text-sm text-accent-warning" role="alert">
                {uploadError}
              </p>
            ) : null}
            {canManage && accessToken ? (
              <label className="inline-flex cursor-pointer items-center gap-3 rounded-sharp border border-border px-3 py-2 font-mono text-xs text-text-muted hover:bg-bg-elevated">
                <span>Upload new version</span>
                <input
                  type="file"
                  accept=".html,.htm,.zip,text/html,application/zip"
                  className="hidden"
                  onChange={(ev) => {
                    const f = ev.target.files?.[0];
                    ev.target.value = "";
                    if (f) upload.mutate(f);
                  }}
                />
              </label>
            ) : null}
          </section>

          <div className="hidden md:block">
            <FeedbackSidebar {...feedbackSidebarProps} />
          </div>
        </div>

        <Drawer.Root open={mobileFeedbackOpen} onOpenChange={setMobileFeedbackOpen}>
          <Drawer.Portal>
            <Drawer.Overlay className="fixed inset-0 z-40 bg-black/40 md:hidden" />
            <Drawer.Content className="fixed inset-x-0 bottom-0 z-50 max-h-[88vh] rounded-t-[20px] border border-border bg-bg-elevated md:hidden">
              <div className="mx-auto mt-2 h-1.5 w-12 rounded-full bg-border" />
              <div className="max-h-[calc(88vh-24px)] overflow-y-auto p-4">
                <FeedbackSidebar {...feedbackSidebarProps} embedded />
              </div>
            </Drawer.Content>
          </Drawer.Portal>
        </Drawer.Root>

        {canManage && accessToken ? (
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
      </div>
    </RequireDeckAccess>
  );
}
