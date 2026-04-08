import type { RefObject } from "react";
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
}: Props) {
  const cursorClass =
    commentMode && canComment ? "cursor-crosshair ring-2 ring-primary/35" : "ring-1 ring-border";

  return (
    <div
      className={`relative mx-auto w-full max-w-6xl flex-1 overflow-hidden rounded-sharp shadow-elevated ${cursorClass}`}
      style={{ aspectRatio: "16 / 9" }}
    >
      {iframeSrc ? (
        <>
          <SlideFrame
            ref={iframeRef}
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
