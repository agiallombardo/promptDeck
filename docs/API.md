# promptDeck API (generated)

Regenerate with `just api-contract` after changing `backend/openapi.json`.

| Method | Path | Summary |
|--------|------|---------|
| GET | `/a/{version_id}/{file_path}` | Serve Asset |
| GET | `/api/v1/admin/logs` | List Logs |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| GET | `/api/v1/auth/me` | Me |
| POST | `/api/v1/auth/refresh` | Refresh |
| DELETE | `/api/v1/comments/{comment_id}` | Delete Comment |
| GET | `/api/v1/exports/{job_id}` | Get Export Job |
| GET | `/api/v1/presentations` | List Presentations |
| POST | `/api/v1/presentations` | Create Presentation |
| DELETE | `/api/v1/presentations/{presentation_id}` | Delete Presentation |
| GET | `/api/v1/presentations/{presentation_id}` | Get Presentation Detail |
| PATCH | `/api/v1/presentations/{presentation_id}` | Update Presentation |
| GET | `/api/v1/presentations/{presentation_id}/embed` | Embed Iframe |
| POST | `/api/v1/presentations/{presentation_id}/exports` | Create Export Job |
| GET | `/api/v1/presentations/{presentation_id}/shares` | List Share Links |
| POST | `/api/v1/presentations/{presentation_id}/shares` | Create Share Link |
| DELETE | `/api/v1/presentations/{presentation_id}/shares/{share_id}` | Revoke Share Link |
| GET | `/api/v1/presentations/{presentation_id}/threads` | List Threads |
| POST | `/api/v1/presentations/{presentation_id}/threads` | Create Thread |
| GET | `/api/v1/presentations/{presentation_id}/versions` | List Versions |
| POST | `/api/v1/presentations/{presentation_id}/versions` | Upload Html Version |
| POST | `/api/v1/presentations/{presentation_id}/versions/{version_id}/activate` | Activate Version |
| POST | `/api/v1/shares/exchange` | Exchange Share Token |
| PATCH | `/api/v1/threads/{thread_id}` | Patch Thread |
| POST | `/api/v1/threads/{thread_id}/comments` | Add Comment |
| GET | `/health` | Health |
