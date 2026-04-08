import { useRef, type Ref, type RefObject } from "react";
import type { ThreadDto } from "../../lib/api";
import { CommentMarker } from "./CommentMarker";
import { SlideFrame } from "./SlideFrame";

type Props = {
  iframeSrc: string;
  iframeRef: RefObject<HTMLIFrameElement | null>;
  onManifest: (count: number, titles: string[]) => void;
  onSlideClick: (payload: { slide: number; x: number; y: number }) => void;
  commentMode: boolean;
  canComment: boolean;
  threads: ThreadDto[];
  slideIndex: number;
  onSelectThread: (threadId: string) => void;
  onLongPressCommentMode?: () => void;
};

export function PresentationCanvas({
  iframeSrc,
  iframeRef,
  onManifest,
  onSlideClick,
  commentMode,
  canComment,
  threads,
  slideIndex,
  onSelectThread,
  onLongPressCommentMode,
}: Props) {
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
      className={`relative mx-auto w-full max-w-6xl flex-1 touch-manipulation overflow-hidden rounded-sharp shadow-elevated ${cursorClass}`}
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
          <CommentMarker
            threads={threads}
            slideIndex={slideIndex}
            onSelectThread={onSelectThread}
          />
        </>
      ) : (
        <div className="flex h-full items-center justify-center bg-bg-recessed font-mono text-sm text-text-muted">
          Loading canvas…
        </div>
      )}
    </div>
  );
}
