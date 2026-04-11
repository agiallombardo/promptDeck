import { forwardRef, useRef, type Ref, type RefObject } from "react";
import type { ThreadDto } from "../../lib/api";
import { CommentMarker } from "./CommentMarker";
import { SlideFrame } from "./SlideFrame";

export type PresentationCanvasPlaceholder =
  | "loading-presentation"
  | "awaiting-upload"
  | "loading-embed"
  | { type: "embed-error"; message: string };

type Props = {
  iframeSrc: string;
  iframeRef: RefObject<HTMLIFrameElement | null>;
  /** When `iframeSrc` is empty, controls copy instead of a generic loading message. */
  noIframePlaceholder: PresentationCanvasPlaceholder;
  onManifest: (count: number, titles: string[]) => void;
  onSlideClick?: (payload: { slide: number; x: number; y: number }) => void;
  commentMode: boolean;
  canComment: boolean;
  threads: ThreadDto[];
  slideIndex: number;
  onSelectThread: (threadId: string) => void;
  onLongPressCommentMode?: () => void;
  /** Shown on top of the deck while the canvas is in browser fullscreen (header is off-screen). */
  showFullscreenExit?: boolean;
  onExitFullscreen?: () => void;
  hideCommentMarkers?: boolean;
  /** Fullscreen overlay: toggle comment UI when header is hidden. */
  onToggleCommentsHidden?: () => void;
  commentsHidden?: boolean;
};

function placeholderCopy(p: PresentationCanvasPlaceholder): { title: string; body?: string } {
  if (p === "loading-presentation") {
    return { title: "Loading deck…" };
  }
  if (p === "awaiting-upload") {
    return {
      title: "No deck content yet",
      body: "Upload a single .html file or a .zip bundle that includes index.html. The preview appears here after the first upload.",
    };
  }
  if (p === "loading-embed") {
    return { title: "Loading preview…" };
  }
  return { title: "Could not load preview", body: p.message };
}

export const PresentationCanvas = forwardRef<HTMLDivElement, Props>(function PresentationCanvas(
  {
    iframeSrc,
    iframeRef,
    noIframePlaceholder,
    onManifest,
    onSlideClick,
    commentMode,
    canComment,
    threads,
    slideIndex,
    onSelectThread,
    onLongPressCommentMode,
    showFullscreenExit = false,
    onExitFullscreen,
    hideCommentMarkers = false,
    onToggleCommentsHidden,
    commentsHidden = false,
  },
  ref,
) {
  const longPressTimer = useRef<number | null>(null);
  const clearLongPress = () => {
    if (longPressTimer.current != null) {
      window.clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  };
  const cursorClass =
    commentMode && canComment ? "cursor-crosshair ring-2 ring-primary/35" : "ring-1 ring-border";

  return (
    <div
      ref={ref}
      className={`relative mx-auto w-full max-w-[min(100%,88rem)] flex-1 touch-manipulation overflow-hidden rounded-sharp shadow-elevated ${cursorClass}`}
      style={{ aspectRatio: "16 / 9" }}
      onTouchStart={() => {
        if (!canComment || !onLongPressCommentMode) return;
        clearLongPress();
        longPressTimer.current = window.setTimeout(() => {
          longPressTimer.current = null;
          onLongPressCommentMode();
        }, 550);
      }}
      onTouchEnd={clearLongPress}
      onTouchCancel={clearLongPress}
    >
      {iframeSrc ? (
        <>
          <SlideFrame
            ref={iframeRef as Ref<HTMLIFrameElement>}
            src={iframeSrc}
            onManifest={onManifest}
            onSlideClick={onSlideClick}
          />
          {!hideCommentMarkers ? (
            <CommentMarker
              threads={threads}
              slideIndex={slideIndex}
              onSelectThread={onSelectThread}
            />
          ) : null}
          {showFullscreenExit && onExitFullscreen ? (
            <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex flex-wrap items-end justify-end gap-2 p-3">
              {onToggleCommentsHidden ? (
                <button
                  type="button"
                  className="pointer-events-auto rounded-sharp border border-border bg-bg-elevated/95 px-3 py-1.5 font-mono text-xs text-text-main shadow-elevated hover:bg-bg-recessed"
                  onClick={onToggleCommentsHidden}
                >
                  {commentsHidden ? "Show comments" : "Hide comments"}
                </button>
              ) : null}
              <button
                type="button"
                className="pointer-events-auto rounded-sharp border border-border bg-bg-elevated/95 px-3 py-1.5 font-mono text-xs text-text-main shadow-elevated hover:bg-bg-recessed"
                onClick={onExitFullscreen}
              >
                Exit full screen
              </button>
              <span className="pointer-events-none absolute bottom-12 right-3 font-mono text-[10px] text-text-muted">
                Esc also exits
              </span>
            </div>
          ) : null}
        </>
      ) : (
        (() => {
          const { title, body } = placeholderCopy(noIframePlaceholder);
          const isErr = typeof noIframePlaceholder === "object";
          return (
            <div className="flex h-full flex-col items-center justify-center gap-2 bg-bg-recessed px-6 text-center">
              <p
                className={`font-heading text-sm font-medium ${isErr ? "text-accent-warning" : "text-text-main"}`}
              >
                {title}
              </p>
              {body ? (
                <p
                  className={`max-w-md font-mono text-xs leading-relaxed ${isErr ? "text-accent-warning/90" : "text-text-muted"}`}
                >
                  {body}
                </p>
              ) : null}
            </div>
          );
        })()
      )}
    </div>
  );
});
