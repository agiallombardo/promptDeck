# promptDeck API (generated)

Regenerate with `just api-contract` after changing `backend/openapi.json`.

| Method | Path | Summary |
|--------|------|---------|
| GET | `/a/{version_id}/{file_path}` | Serve Asset |
| GET | `/api/v1/admin/audit` | List Audit |
| GET | `/api/v1/admin/deck-prompt-jobs` | List Deck Prompt Jobs Admin |
| GET | `/api/v1/admin/jobs` | List Export Jobs Admin |
| GET | `/api/v1/admin/logs` | List Logs |
| GET | `/api/v1/admin/presentations` | List Presentations Admin |
| GET | `/api/v1/admin/settings/entra` | Admin Entra Settings Get |
| PATCH | `/api/v1/admin/settings/entra` | Admin Entra Settings Patch |
| GET | `/api/v1/admin/settings/llm` | Admin Llm Settings Get |
| PATCH | `/api/v1/admin/settings/llm` | Admin Llm Settings Patch |
| GET | `/api/v1/admin/settings/smtp` | Admin Smtp Settings Get |
| PATCH | `/api/v1/admin/settings/smtp` | Admin Smtp Settings Patch |
| POST | `/api/v1/admin/settings/smtp/test` | Admin Smtp Test |
| GET | `/api/v1/admin/setup` | Admin Setup |
| GET | `/api/v1/admin/stats` | Admin Stats |
| GET | `/api/v1/admin/users` | List Users |
| GET | `/api/v1/auth/config` | Auth Config |
| GET | `/api/v1/auth/entra/callback` | Entra Callback |
| GET | `/api/v1/auth/entra/login` | Entra Login |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| GET | `/api/v1/auth/me` | Me |
| GET | `/api/v1/auth/me/settings` | Me Settings |
| PATCH | `/api/v1/auth/me/settings` | Me Settings Patch |
| POST | `/api/v1/auth/refresh` | Refresh |
| DELETE | `/api/v1/comments/{comment_id}` | Delete Comment |
| GET | `/api/v1/deck-prompt-jobs/{job_id}` | Get Deck Prompt Job |
| GET | `/api/v1/directory/users` | Directory Users |
| GET | `/api/v1/exports/{job_id}` | Get Export Job |
| GET | `/api/v1/exports/{job_id}/file` | Download Export File |
| GET | `/api/v1/presentations` | List Presentations |
| POST | `/api/v1/presentations` | Create Presentation |
| DELETE | `/api/v1/presentations/{presentation_id}` | Delete Presentation |
| GET | `/api/v1/presentations/{presentation_id}` | Get Presentation Detail |
| PATCH | `/api/v1/presentations/{presentation_id}` | Update Presentation |
| POST | `/api/v1/presentations/{presentation_id}/deck-prompt-jobs` | Create Deck Prompt Job |
| GET | `/api/v1/presentations/{presentation_id}/embed` | Embed Iframe |
| POST | `/api/v1/presentations/{presentation_id}/exports` | Create Export Job |
| GET | `/api/v1/presentations/{presentation_id}/members` | List Presentation Members |
| POST | `/api/v1/presentations/{presentation_id}/members` | Create Presentation Member |
| DELETE | `/api/v1/presentations/{presentation_id}/members/{member_id}` | Delete Presentation Member |
| PATCH | `/api/v1/presentations/{presentation_id}/members/{member_id}` | Update Presentation Member |
| GET | `/api/v1/presentations/{presentation_id}/share-links` | List Share Links |
| POST | `/api/v1/presentations/{presentation_id}/share-links` | Create Share Link |
| DELETE | `/api/v1/presentations/{presentation_id}/share-links/{share_link_id}` | Revoke Share Link |
| GET | `/api/v1/presentations/{presentation_id}/threads` | List Threads |
| POST | `/api/v1/presentations/{presentation_id}/threads` | Create Thread |
| GET | `/api/v1/presentations/{presentation_id}/versions` | List Versions |
| POST | `/api/v1/presentations/{presentation_id}/versions` | Upload Html Version |
| POST | `/api/v1/presentations/{presentation_id}/versions/{version_id}/activate` | Activate Version |
| POST | `/api/v1/share-links/exchange` | Exchange Share Link |
| PATCH | `/api/v1/threads/{thread_id}` | Patch Thread |
| POST | `/api/v1/threads/{thread_id}/comments` | Add Comment |
| GET | `/health` | Health |
