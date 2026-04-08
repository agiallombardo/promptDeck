# Security notes (v1 direction)

- Sandboxed iframe, strict CSP on asset routes, signed asset URLs (HMAC) — implemented in M2+.
- Passwords: argon2id; JWT access + HttpOnly refresh — M1.
- Zip uploads: zip-slip guards and size caps — M4.
- Share tokens: random bytes, store hash — M4.
- Rate limits on auth and sensitive endpoints — M7.

This document will gain operational checklists as features land.
