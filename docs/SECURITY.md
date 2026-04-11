# Security notes (v1 direction)

- Sandboxed iframe, strict CSP on asset routes, signed asset URLs (HMAC) — implemented in M2+.
- Passwords: argon2id; JWT access + HttpOnly refresh — M1.
- Zip uploads: zip-slip guards and size caps — M4.
- Share links: random bytes, store hash; exchange endpoint issues short-lived signed access JWTs.
- Rate limits on auth and sensitive endpoints — M7 (slowapi: login, refresh, share exchange).

## Content-Security-Policy (deck assets)

Signed HTML decks are served from `/a/…` with a dedicated CSP string in `backend/app/routers/assets.py` (`ASSET_CSP`). It allows inline scripts and `unsafe-eval` so third-party HTML decks can run; `frame-ancestors 'self'` keeps embeds same-origin. When changing this string, re-test a representative deck (scripts, fonts, images, iframes) and record the rationale—tightening without breaking real decks is the main operational risk.

## Argon2 tuning

Password hashing uses Argon2id via `argon2-cffi`. Time cost, memory (KiB), and parallelism are configurable through settings (`ARGON2_TIME_COST`, `ARGON2_MEMORY_COST`, `ARGON2_PARALLELISM` in `app/config.py`) for production tuning against your CPU/RAM envelope.

This document will gain operational checklists as features land.
