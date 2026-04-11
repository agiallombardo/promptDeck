# Roadmap (deferred from v1)

| Item | Rationale |
|------|-----------|
| Real-time comments (SSE/WebSocket) | v1 uses manual refresh + focus refetch |
| AI regeneration | LLM credential/config plumbing is available; generation workflow remains post-v1 |
| Entra ID / Azure AD OIDC | Local auth first; interface-ready for OIDC later |
| Azure Blob storage | `LocalFSStorage` only in v1; stub driver for swap-in |
| Multi-tenant orgs | Single tenant for v1 |
| CORS (richer multi-origin / operator UX) | v1: set `CORS_ORIGINS` + `PUBLIC_APP_URL` manually for one LAN origin |
| Let’s Encrypt / automated TLS in deploy | v1: local/LAN HTTP only; optional HTTPS left to manual nginx + certs |
| Git sync for versions | Manual upload only in v1 |
