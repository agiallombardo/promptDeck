import { useMemo } from "react";
import type { ThreadDto } from "../../lib/api";

type Props = {
  threads: ThreadDto[];
  slideIndex: number;
  onSelectThread: (threadId: string) => void;
};

const ANCHOR_GRID = 100;

function anchorKey(x: number, y: number): string {
  const rx = Math.round(x * ANCHOR_GRID) / ANCHOR_GRID;
  const ry = Math.round(y * ANCHOR_GRID) / ANCHOR_GRID;
  return `${rx},${ry}`;
}

function clusterLayout(threads: ThreadDto[]): Map<string, { index: number; total: number }> {
  const byKey = new Map<string, ThreadDto[]>();
  for (const t of threads) {
    const k = anchorKey(t.anchor_x, t.anchor_y);
    const list = byKey.get(k);
    if (list) list.push(t);
    else byKey.set(k, [t]);
  }
  const layout = new Map<string, { index: number; total: number }>();
  for (const [, group] of byKey) {
    const total = group.length;
    group.forEach((t, index) => {
      layout.set(t.id, { index, total });
    });
  }
  return layout;
}

function pinOffset(index: number, total: number): { dx: number; dy: number } {
  if (total <= 1) return { dx: 0, dy: 0 };
  const angle = (2 * Math.PI * index) / total;
  const r = 0.022;
  return { dx: r * Math.cos(angle), dy: r * Math.sin(angle) };
}

export function CommentMarker({ threads, slideIndex, onSelectThread }: Props) {
  const onSlide = useMemo(() => {
    const open = threads.filter((t) => t.slide_index === slideIndex && t.status === "open");
    return [...open].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [threads, slideIndex]);

  const layout = useMemo(() => clusterLayout(onSlide), [onSlide]);

  return (
    <>
      {onSlide.map((t) => {
        const { index, total } = layout.get(t.id) ?? { index: 0, total: 1 };
        const { dx, dy } = pinOffset(index, total);
        const left = (t.anchor_x + dx) * 100;
        const top = (t.anchor_y + dy) * 100;
        return (
          <button
            key={t.id}
            type="button"
            className="absolute z-10 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-primary/90 shadow-md ring-2 ring-bg-void hover:scale-110 md:h-3 md:w-3"
            style={{
              left: `${left}%`,
              top: `${top}%`,
            }}
            title="Jump to thread"
            aria-label={`Comment thread on slide ${slideIndex + 1}`}
            onClick={() => onSelectThread(t.id)}
          />
        );
      })}
    </>
  );
}
