export function postSlideGoto(iframe: HTMLIFrameElement | null, slide: number) {
  iframe?.contentWindow?.postMessage({ type: "goto", slide }, "*");
}

export function postSetCommentMode(iframe: HTMLIFrameElement | null, enabled: boolean) {
  iframe?.contentWindow?.postMessage({ type: "setCommentMode", enabled }, "*");
}
