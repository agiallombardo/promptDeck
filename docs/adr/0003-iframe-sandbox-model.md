# ADR 0003: Iframe sandbox model

## Status

Accepted

## Decision

Deck content runs in an iframe with `sandbox="allow-scripts"` only. Slide detection and comment coordinates use an injected `probe.js` and `postMessage` (see `docs/PROBE_PROTOCOL.md`).

## Consequences

Strong isolation from the host app; CSP and asset signing are required on the asset origin. Parent UI must not rely on DOM access inside the iframe.
