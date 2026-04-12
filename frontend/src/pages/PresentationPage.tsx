import { Drawer } from "vaul";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { DeckPromptJobActivity } from "../components/DeckPromptJobActivity";
import { DeckPromptTemplateChips } from "../components/DeckPromptTemplateChips";
import {
  PresentationCanvas,
  type PresentationCanvasPlaceholder,
} from "../components/canvas/PresentationCanvas";
import { FeedbackSidebar } from "../components/feedback/FeedbackSidebar";
import { RequireDeckAccess } from "../components/RequireDeckAccess";
import { PresentationDeckHeader } from "../components/layout/PresentationDeckHeader";
import { ShareModal } from "../components/ShareModal";
import { useComments } from "../hooks/useComments";
import { usePresentation } from "../hooks/usePresentation";
import {
  ApiError,
  apiDeckPromptJobCreate,
  apiExportCreate,
  apiExportDownloadFile,
  apiExportGet,
  apiShareExchange,
} from "../lib/api";
import {
  deckPromptJobSnapshotFromApi,
  pollDeckPromptJobUntilTerminal,
  type DeckPromptJobProgressSnapshot,
} from "../lib/deckPromptPoll";
import { recordRecentDeck } from "../lib/recentDecks";
import { shouldIgnoreDeckHotkeys } from "../lib/hotkeys";
import { postSetCommentMode, postSlideGoto } from "../lib/slidePostMessage";
import { useAuthStore } from "../stores/auth";
import { useToastStore } from "../stores/toasts";

export default function PresentationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const accessToken = useAuthStore((s) => s.accessToken);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const user = useAuthStore((s) => s.user);
  const shareToken = searchParams.get("share");
  const [shareExchangePending, setShareExchangePending] = useState(false);
  const [shareExchangeError, setShareExchangeError] = useState<string | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [exportBusy, setExportBusy] = useState<"pdf" | "single_html" | null>(null);
  const [deckPromptOpen, setDeckPromptOpen] = useState(false);
  const [deckPromptText, setDeckPromptText] = useState("");
  const [deckPromptBusy, setDeckPromptBusy] = useState(false);
  const [deckPromptSnapshot, setDeckPromptSnapshot] =
    useState<DeckPromptJobProgressSnapshot | null>(null);
  const [deckJobFollowSnapshot, setDeckJobFollowSnapshot] =
    useState<DeckPromptJobProgressSnapshot | null>(null);
  const [mobileFeedbackOpen, setMobileFeedbackOpen] = useState(false);
  const [commentsHidden, setCommentsHidden] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const presentRootRef = useRef<HTMLDivElement | null>(null);
  const [canvasFullscreen, setCanvasFullscreen] = useState(false);

  const [slideIndex, setSlideIndex] = useState(0);
  const [slideCount, setSlideCount] = useState(1);

  const { pres, embed, upload, uploadError, iframeSrc, qc } = usePresentation(id, accessToken);
  const versionId = pres.data?.current_version_id;

  useEffect(() => {
    if (!id || !accessToken || !pres.isSuccess || !pres.data?.title) return;
    recordRecentDeck(id, pres.data.title);
  }, [id, accessToken, pres.isSuccess, pres.data?.title]);

  const noIframePlaceholder = useMemo((): PresentationCanvasPlaceholder => {
    if (iframeSrc) {
      return "loading-embed";
    }
    if (pres.isPending || pres.isLoading) {
      return "loading-presentation";
    }
    if (!pres.data?.current_version_id) {
      return "awaiting-upload";
    }
    if (embed.isError) {
      const err = embed.error;
      const message =
        err instanceof Error ? err.message : err != null ? String(err) : "Could not load preview";
      return { type: "embed-error", message };
    }
    if (embed.isPending || embed.isLoading || embed.isFetching) {
      return "loading-embed";
    }
    if (embed.data) {
      return {
        type: "embed-error",
        message: "Preview URL missing. Try refreshing the page.",
      };
    }
    return "loading-embed";
  }, [
    iframeSrc,
    pres.isPending,
    pres.isLoading,
    pres.data?.current_version_id,
    embed.isError,
    embed.error,
    embed.isPending,
    embed.isLoading,
    embed.isFetching,
    embed.data,
  ]);
  const accessRole = pres.data?.current_user_role ?? null;
  const canComment =
    accessRole === "owner" ||
    accessRole === "editor" ||
    accessRole === "commenter" ||
    accessRole === "admin";
  const canManage = canComment;
  const canPromptEdit = accessRole === "owner" || accessRole === "editor" || accessRole === "admin";

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
      queueMicrotask(() =>
        postSetCommentMode(iframeRef.current, commentsHidden ? false : commentMode),
      );
    },
    [commentMode, commentsHidden],
  );

  const onSlideClick = useCallback(
    (payload: { slide: number; x: number; y: number }) => {
      if (!commentMode || !canComment) return;
      setPendingPin({ slide: payload.slide, x: payload.x, y: payload.y });
    },
    [canComment, commentMode, setPendingPin],
  );

  useEffect(() => {
    postSetCommentMode(iframeRef.current, commentsHidden ? false : commentMode);
  }, [commentMode, iframeSrc, commentsHidden]);

  useEffect(() => {
    function onFullscreenChange() {
      setCanvasFullscreen(document.fullscreenElement === presentRootRef.current);
    }
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  const togglePresentFullscreen = useCallback(() => {
    const el = presentRootRef.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen();
    } else {
      void el.requestFullscreen().catch(() => undefined);
    }
  }, []);

  const runExport = useCallback(
    async (format: "pdf" | "single_html") => {
      if (!id || !accessToken || !pres.data?.current_version_id) return;
      setExportBusy(format);
      const label = format === "pdf" ? "PDF" : "HTML";
      useToastStore.getState().pushToast({
        level: "info",
        message: `Preparing ${label} export…`,
      });
      try {
        const job = await apiExportCreate(accessToken, id, {
          format,
          version_id: pres.data.current_version_id,
        });
        let status = job.status;
        let err: string | null = job.error ?? null;
        for (let i = 0; i < 300 && status !== "succeeded" && status !== "failed"; i++) {
          await new Promise((r) => setTimeout(r, 400));
          const j = await apiExportGet(accessToken, job.id);
          status = j.status;
          err = j.error ?? null;
        }
        if (status !== "succeeded") {
          useToastStore.getState().pushToast({
            level: "error",
            message: err?.trim() ? err : `${label} export failed`,
          });
          return;
        }
        const blob = await apiExportDownloadFile(accessToken, job.id);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const base =
          (pres.data.title || "presentation").replace(/[^\w\-. ]+/g, "").slice(0, 80) ||
          "presentation";
        const ext = format === "pdf" ? "pdf" : "html";
        a.download = `${base}.${ext}`;
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        useToastStore.getState().pushToast({
          level: "info",
          message: `${label} downloaded`,
        });
      } catch (e) {
        const msg =
          e instanceof ApiError
            ? `${e.message}${e.requestId ? ` · Request ID: ${e.requestId}` : ""}`
            : e instanceof Error
              ? e.message
              : "Export failed";
        useToastStore.getState().pushToast({ level: "error", message: msg });
      } finally {
        setExportBusy(null);
      }
    },
    [accessToken, id, pres.data?.current_version_id, pres.data?.title],
  );

  const runDeckPrompt = useCallback(async () => {
    if (!id || !accessToken || !pres.data?.current_version_id) return;
    const prompt = deckPromptText.trim();
    if (!prompt) {
      useToastStore.getState().pushToast({ level: "error", message: "Enter a prompt" });
      return;
    }
    setDeckPromptBusy(true);
    setDeckPromptSnapshot(null);
    useToastStore.getState().pushToast({
      level: "info",
      message: "AI edit started — this can take a minute…",
    });
    try {
      const job = await apiDeckPromptJobCreate(accessToken, id, { prompt });
      setDeckPromptSnapshot(deckPromptJobSnapshotFromApi(job, 0));
      const { status, error: err } = await pollDeckPromptJobUntilTerminal(accessToken, job.id, {
        onProgress: setDeckPromptSnapshot,
      });
      if (status !== "succeeded") {
        const stillRunning = status === "running" || status === "queued";
        useToastStore.getState().pushToast({
          level: stillRunning ? "info" : "error",
          message: stillRunning
            ? "AI edit is still running — refresh this page in a bit to see the new version."
            : err?.trim()
              ? err
              : "AI edit failed",
        });
        return;
      }
      await qc.invalidateQueries({ queryKey: ["presentation", id, accessToken] });
      await qc.invalidateQueries({ queryKey: ["presentation-embed", id, accessToken] });
      useToastStore.getState().pushToast({
        level: "info",
        message: "Deck updated — preview refreshed",
      });
      setDeckPromptOpen(false);
      setDeckPromptText("");
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.message}${e.requestId ? ` · Request ID: ${e.requestId}` : ""}`
          : e instanceof Error
            ? e.message
            : "AI edit failed";
      useToastStore.getState().pushToast({ level: "error", message: msg });
    } finally {
      setDeckPromptBusy(false);
      setDeckPromptSnapshot(null);
    }
  }, [accessToken, deckPromptText, id, pres.data?.current_version_id, qc]);

  const deckJobFromUrl = searchParams.get("deckJob");

  useEffect(() => {
    if (!deckJobFromUrl || !accessToken || !id || !canPromptEdit) {
      return undefined;
    }

    let cancelled = false;

    void (async () => {
      useToastStore.getState().pushToast({
        level: "info",
        message: "Finishing AI deck generation…",
      });
      setDeckJobFollowSnapshot(null);
      try {
        const { status, error: err } = await pollDeckPromptJobUntilTerminal(
          accessToken,
          deckJobFromUrl,
          {
            firstPollImmediate: true,
            onProgress: (p) => {
              if (!cancelled) setDeckJobFollowSnapshot(p);
            },
          },
        );
        if (cancelled) return;

        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            next.delete("deckJob");
            return next;
          },
          { replace: true },
        );
        setDeckJobFollowSnapshot(null);

        if (status === "succeeded") {
          await qc.invalidateQueries({ queryKey: ["presentation", id, accessToken] });
          await qc.invalidateQueries({ queryKey: ["presentation-embed", id, accessToken] });
          useToastStore.getState().pushToast({
            level: "info",
            message: "Deck updated — preview refreshed",
          });
        } else {
          const stillRunning = status === "running" || status === "queued";
          useToastStore.getState().pushToast({
            level: stillRunning ? "info" : "error",
            message: stillRunning
              ? "AI generation is still running — refresh this page in a bit to see the new version."
              : err?.trim()
                ? err
                : "AI generation failed",
          });
        }
      } catch (e) {
        if (cancelled) return;
        setDeckJobFollowSnapshot(null);
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            next.delete("deckJob");
            return next;
          },
          { replace: true },
        );
        const msg =
          e instanceof ApiError
            ? `${e.message}${e.requestId ? ` · Request ID: ${e.requestId}` : ""}`
            : e instanceof Error
              ? e.message
              : "AI generation failed";
        useToastStore.getState().pushToast({ level: "error", message: msg });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [accessToken, canPromptEdit, deckJobFromUrl, id, qc, setSearchParams]);

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (shouldIgnoreDeckHotkeys(ev.target)) {
        return;
      }
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
      if (commentsHidden) return;
      const narrow =
        typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
      if (narrow) {
        setMobileFeedbackOpen(true);
        requestAnimationFrame(() => scrollThreadIntoView(threadId));
      } else {
        scrollThreadIntoView(threadId);
      }
    },
    [commentsHidden, scrollThreadIntoView],
  );

  const handleToggleCommentsHidden = useCallback(() => {
    setCommentsHidden((prev) => {
      const next = !prev;
      if (!prev && next) {
        setMobileFeedbackOpen(false);
        queueMicrotask(() => {
          setCommentMode(false);
          setPendingPin(null);
          setDraftNewThread("");
        });
      }
      return next;
    });
  }, [setCommentMode, setDraftNewThread, setPendingPin]);

  const feedbackSidebarProps = {
    threads: threads.data?.items ?? [],
    // Avoid treating "no version yet" as thread loading — query is disabled; show empty state.
    isLoading: Boolean(versionId ? threads.isLoading : pres.isPending || pres.isLoading),
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

  useEffect(() => {
    if (!id || accessToken || !shareToken) return;
    let cancelled = false;
    setShareExchangePending(true);
    setShareExchangeError(null);
    void apiShareExchange(shareToken)
      .then((resp) => {
        if (cancelled) return;
        setAccessToken(resp.access_token);
        navigate(`/p/${resp.presentation_id}`, { replace: true });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Share link is invalid or expired";
        setShareExchangeError(message);
      })
      .finally(() => {
        if (!cancelled) setShareExchangePending(false);
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, id, navigate, setAccessToken, shareToken]);

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
        {!accessToken && shareToken ? (
          <div className="mx-auto max-w-[min(100%,88rem)] px-4 py-3">
            {shareExchangePending ? (
              <p className="font-mono text-xs text-text-muted">Authorizing share link…</p>
            ) : null}
            {shareExchangeError ? (
              <p className="font-mono text-xs text-accent-warning" role="alert">
                {shareExchangeError}
              </p>
            ) : null}
          </div>
        ) : null}
        <PresentationDeckHeader
          title={pres.data?.title ?? "Presentation"}
          accessRole={accessRole}
          showShareAction={Boolean(canManage && accessToken)}
          showExportAction={Boolean(canManage && accessToken && pres.data?.current_version_id)}
          onShare={() => setShareOpen(true)}
          onExportPdf={() => void runExport("pdf")}
          onExportHtml={() => void runExport("single_html")}
          exportBusy={exportBusy}
          showUploadAction={Boolean(canManage && accessToken)}
          onUploadFile={(f) => upload.mutate(f)}
          showPromptEditAction={Boolean(canPromptEdit && versionId)}
          promptEditBusy={deckPromptBusy}
          onPromptEdit={() => setDeckPromptOpen(true)}
          showPresentAction={Boolean(iframeSrc && embed.data?.slide_count)}
          onPresent={togglePresentFullscreen}
          isFullscreen={canvasFullscreen}
          slideIndex={slideIndex}
          slideCount={slideCount}
          canNavigate={Boolean(embed.data?.slide_count)}
          onPrev={() => go(slideIndex - 1)}
          onNext={() => go(slideIndex + 1)}
          showCommentsVisibilityToggle={Boolean(versionId)}
          commentsHidden={commentsHidden}
          onToggleCommentsHidden={handleToggleCommentsHidden}
        />

        {deckJobFollowSnapshot || (deckJobFromUrl && canPromptEdit) ? (
          <div className="mx-auto max-w-[min(100%,88rem)] px-4 pt-2">
            <div className="rounded-sharp border border-border bg-bg-elevated px-3 py-2 shadow-elevated">
              <DeckPromptJobActivity
                title="AI is generating your deck"
                snapshot={deckJobFollowSnapshot}
                waitingSubmit={false}
                jobActive={Boolean(deckJobFromUrl && !deckJobFollowSnapshot)}
              />
            </div>
          </div>
        ) : null}

        {(() => {
          const hasThreads = (threads.data?.items ?? []).length > 0;
          const showFeedback = !commentsHidden && (hasThreads || commentMode || pendingPin != null);
          return (
            <>
              <div
                className={`mx-auto grid w-full max-w-[min(100%,96rem)] gap-4 px-3 py-3 sm:gap-6 sm:px-4 sm:py-4 ${showFeedback ? "md:grid-cols-[minmax(0,1fr)_min(300px,32vw)]" : ""}`}
              >
                <section className="space-y-4">
                  <PresentationCanvas
                    ref={presentRootRef}
                    iframeRef={iframeRef}
                    iframeSrc={iframeSrc}
                    iframeRemountKey={versionId ?? undefined}
                    noIframePlaceholder={noIframePlaceholder}
                    slideIndex={slideIndex}
                    commentMode={commentsHidden ? false : commentMode}
                    canComment={canComment}
                    threads={threads.data?.items ?? []}
                    onManifest={onManifest}
                    onSelectThread={onThreadSelectFromCanvas}
                    onSlideClick={commentsHidden ? undefined : onSlideClick}
                    onLongPressCommentMode={commentsHidden ? undefined : () => setCommentMode(true)}
                    showFullscreenExit={canvasFullscreen}
                    onExitFullscreen={() => {
                      void document.exitFullscreen();
                    }}
                    hideCommentMarkers={commentsHidden}
                    commentsHidden={commentsHidden}
                    onToggleCommentsHidden={handleToggleCommentsHidden}
                  />
                  {uploadError ? (
                    <p className="text-sm text-accent-warning" role="alert">
                      {uploadError}
                    </p>
                  ) : null}
                </section>

                {showFeedback ? (
                  <div className="hidden md:block">
                    <FeedbackSidebar {...feedbackSidebarProps} />
                  </div>
                ) : null}
              </div>

              {showFeedback ? (
                <Drawer.Root open={mobileFeedbackOpen} onOpenChange={setMobileFeedbackOpen}>
                  <Drawer.Portal>
                    <Drawer.Overlay className="fixed inset-0 z-40 bg-scrim md:hidden" />
                    <Drawer.Content className="fixed inset-x-0 bottom-0 z-50 max-h-[88vh] rounded-t-[20px] border border-border bg-bg-elevated md:hidden">
                      <div className="mx-auto mt-2 h-1.5 w-12 rounded-full bg-border" />
                      <div className="max-h-[calc(88vh-24px)] overflow-y-auto p-4">
                        <FeedbackSidebar {...feedbackSidebarProps} embedded />
                      </div>
                    </Drawer.Content>
                  </Drawer.Portal>
                </Drawer.Root>
              ) : null}
            </>
          );
        })()}

        {canManage && accessToken ? (
          <>
            <ShareModal
              open={shareOpen}
              onClose={() => setShareOpen(false)}
              accessToken={accessToken}
              presentationId={id}
            />
          </>
        ) : null}

        {deckPromptOpen ? (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-scrim p-4"
            role="presentation"
            onMouseDown={(ev) => {
              if (ev.target === ev.currentTarget && !deckPromptBusy) setDeckPromptOpen(false);
            }}
          >
            <div
              className="w-full max-w-lg rounded-sharp border border-border bg-bg-elevated p-4 shadow-elevated"
              role="dialog"
              aria-labelledby="deck-prompt-title"
              onMouseDown={(ev) => ev.stopPropagation()}
            >
              <h2 id="deck-prompt-title" className="font-heading text-base font-semibold">
                Edit deck with AI
              </h2>
              <div className="mt-1 flex items-center gap-2 font-mono text-[11px] text-text-muted">
                <p>
                  Describe the change you want. A new version is created when the model finishes.
                </p>
                <details className="group relative inline-block shrink-0">
                  <summary className="cursor-pointer select-none list-none text-text-muted/60 hover:text-primary">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className="inline-block h-3.5 w-3.5"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </summary>
                  <div className="absolute right-0 top-full z-30 mt-1 w-72 rounded-sharp border border-border bg-bg-elevated p-3 text-[11px] leading-relaxed text-text-muted shadow-elevated">
                    <p className="font-semibold text-text-main">How AI editing works</p>
                    <ul className="mt-1.5 list-disc space-y-1 pl-3.5">
                      <li>
                        Slides are designed for a <strong>16 : 9</strong> viewport.
                      </li>
                      <li>
                        External resources (Google Fonts, CDN images) are blocked — the AI uses
                        system fonts and inline CSS only.
                      </li>
                      <li>Visuals come from CSS gradients, inline SVG, and unicode/emoji.</li>
                      <li>Text is kept large so slides stay readable even in small previews.</li>
                    </ul>
                  </div>
                </details>
              </div>
              <p className="mt-2 font-mono text-[11px] text-text-muted">Quick-start templates</p>
              <DeckPromptTemplateChips
                variant="edit_deck"
                className="mt-1 flex flex-wrap gap-2"
                disabled={deckPromptBusy}
                onPick={(body) => setDeckPromptText(body)}
              />
              <textarea
                className="mt-3 h-32 w-full resize-y rounded-sharp border border-border bg-bg-recessed px-3 py-2 font-mono text-sm text-text-main"
                placeholder="e.g. Change the title slide to say Q2 Review"
                value={deckPromptText}
                disabled={deckPromptBusy}
                onChange={(ev) => setDeckPromptText(ev.target.value)}
              />
              {deckPromptBusy ? (
                <DeckPromptJobActivity
                  title="AI edit in progress"
                  snapshot={deckPromptSnapshot}
                  waitingSubmit={!deckPromptSnapshot}
                  jobActive={deckPromptBusy}
                  className="mt-2"
                />
              ) : null}
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-sharp border border-border px-3 py-1.5 font-mono text-xs hover:bg-bg-recessed disabled:opacity-50"
                  disabled={deckPromptBusy}
                  onClick={() => setDeckPromptOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="rounded-sharp border border-primary bg-primary/15 px-3 py-1.5 font-mono text-xs text-primary hover:bg-primary/25 disabled:opacity-50"
                  disabled={deckPromptBusy}
                  onClick={() => void runDeckPrompt()}
                >
                  {deckPromptBusy ? "Working…" : "Run"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </RequireDeckAccess>
  );
}
