# Iframe probe protocol (draft)

Parent hosts a sandboxed iframe (`allow-scripts` only). The assets origin serves deck HTML and injects `probe.js`, which:

1. Detects slides: `[data-slide]` → top-level `<section>` → single-slide fallback.
2. Posts to parent: `{ type: "manifest", count, titles }` on load.
3. Listens for `{ type: "goto" | "setCommentMode", … }` from parent.
4. In comment mode, posts `{ type: "slide-click", slide, x, y }` with normalized coordinates.

Full contract will be finalized with the assets router (M2).
