# ADR 0002: No real-time updates in v1

## Status

Accepted

## Decision

Comments and presence are **not** real-time in v1. Clients refetch on navigation, window focus, and explicit Refresh.

## Consequences

Simpler ops and fewer moving parts; acceptable for internal manual review workflows. SSE/WebSocket may follow in a later release.
