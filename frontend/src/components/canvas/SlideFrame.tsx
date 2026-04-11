import { forwardRef, useCallback, useEffect, useMemo, useRef } from "react";
import { parseSlideInboundMessage } from "../../lib/slidePostMessage";

export type SlideFrameProps = {
  src: string;
  onManifest?: (count: number, titles: string[]) => void;
  onSlideClick?: (payload: { slide: number; x: number; y: number }) => void;
};

export const SlideFrame = forwardRef<HTMLIFrameElement, SlideFrameProps>(function SlideFrame(
  { src, onManifest, onSlideClick },
  ref,
) {
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const setFrameRef = useCallback(
    (node: HTMLIFrameElement | null) => {
      frameRef.current = node;
      if (typeof ref === "function") {
        ref(node);
      } else if (ref) {
        ref.current = node;
      }
    },
    [ref],
  );

  const expectedOrigin = useMemo(() => {
    try {
      return new URL(src, window.location.href).origin;
    } catch {
      return window.location.origin;
    }
  }, [src]);

  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      const frameWindow = frameRef.current?.contentWindow;
      if (frameWindow && ev.source !== frameWindow) return;
      if (ev.origin !== "null" && ev.origin !== expectedOrigin) return;
      const msg = parseSlideInboundMessage(ev.data);
      if (!msg) return;
      if (msg.type === "manifest") {
        onManifest?.(msg.count, msg.titles);
      } else if (msg.type === "slide-click") {
        onSlideClick?.({ slide: msg.slide, x: msg.x, y: msg.y });
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [expectedOrigin, onManifest, onSlideClick]);

  return (
    <iframe
      ref={setFrameRef}
      title="Presentation"
      className="h-full w-full rounded-sharp border border-border bg-bg-recessed"
      sandbox="allow-scripts"
      src={src}
    />
  );
});
