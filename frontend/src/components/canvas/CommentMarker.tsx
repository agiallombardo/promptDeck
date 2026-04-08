import type { ThreadDto } from "../../lib/api";

type Props = {
  threads: ThreadDto[];
  slideIndex: number;
  onSelectThread: (threadId: string) => void;
};

export function CommentMarker({ threads, slideIndex, onSelectThread }: Props) {
  const onSlide = threads.filter((t) => t.slide_index === slideIndex && t.status === "open");
  return (
    <>
      {onSlide.map((t) => (
        <button
          key={t.id}
          type="button"
          className="absolute z-10 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-primary/90 shadow-md ring-2 ring-bg-void hover:scale-110"
          style={{
            left: `${t.anchor_x * 100}%`,
            top: `${t.anchor_y * 100}%`,
          }}
          title="Jump to thread"
          aria-label={`Comment thread on slide ${slideIndex + 1}`}
          onClick={() => onSelectThread(t.id)}
        />
      ))}
    </>
  );
}
