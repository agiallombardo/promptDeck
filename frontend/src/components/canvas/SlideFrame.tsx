import { forwardRef, useEffect } from "react";

export type SlideFrameProps = {
  src: string;
  onManifest?: (count: number, titles: string[]) => void;
  onSlideClick?: (payload: { slide: number; x: number; y: number }) => void;
};

export const SlideFrame = forwardRef<HTMLIFrameElement, SlideFrameProps>(function SlideFrame(
  { src, onManifest, onSlideClick },
  ref,
) {
  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      const d = ev.data;
      if (!d || typeof d !== "object") return;
      if (d.type === "manifest" && typeof d.count === "number") {
        const titles = Array.isArray(d.titles) ? (d.titles as string[]) : [];
        onManifest?.(d.count, titles);
      }
      if (
        d.type === "slide-click" &&
        typeof d.slide === "number" &&
        typeof d.x === "number" &&
        typeof d.y === "number"
      ) {
        onSlideClick?.({ slide: d.slide, x: d.x, y: d.y });
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onManifest, onSlideClick]);

  return (
    <iframe
      ref={ref}
      title="Presentation"
      className="h-full w-full rounded-sharp border border-border bg-bg-recessed"
      sandbox="allow-scripts"
      src={src}
    />
  );
});
