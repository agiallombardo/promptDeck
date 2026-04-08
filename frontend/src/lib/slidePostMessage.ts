/** Messages received from the sandboxed slide iframe (probe.js). */
export type SlideInboundMessage =
  | { type: "manifest"; count: number; titles: string[] }
  | { type: "slide-click"; slide: number; x: number; y: number };

export function parseSlideInboundMessage(data: unknown): SlideInboundMessage | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  if (d.type === "manifest" && typeof d.count === "number") {
    const titles = Array.isArray(d.titles) ? (d.titles as string[]) : [];
    return { type: "manifest", count: d.count, titles };
  }
  if (
    d.type === "slide-click" &&
    typeof d.slide === "number" &&
    typeof d.x === "number" &&
    typeof d.y === "number"
  ) {
    return { type: "slide-click", slide: d.slide, x: d.x, y: d.y };
  }
  return null;
}

export function postSlideGoto(
  iframe: HTMLIFrameElement | null,
  slide: number,
  targetOrigin: string = "*",
) {
  iframe?.contentWindow?.postMessage({ type: "goto", slide }, targetOrigin);
}

export function postSetCommentMode(
  iframe: HTMLIFrameElement | null,
  enabled: boolean,
  targetOrigin: string = "*",
) {
  iframe?.contentWindow?.postMessage({ type: "setCommentMode", enabled }, targetOrigin);
}
