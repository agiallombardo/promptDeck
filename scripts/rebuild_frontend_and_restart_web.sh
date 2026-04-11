#!/usr/bin/env bash
# Rebuild the Vite frontend (frontend/dist), then reload nginx and restart the API
# systemd unit. Intended for production hosts per docs/RUNBOOK.md and
# docs/UBUNTU_SERVER_SETUP.md.
#
# Usage (repo root or any cwd):
#   bash scripts/rebuild_frontend_and_restart_web.sh
#   ./scripts/rebuild_frontend_and_restart_web.sh
#
# Environment:
#   BUILD_ONLY=1       — run the frontend build only (no systemctl).
#   NGINX_UNIT=nginx   — unit name for nginx (reload by default).
#   API_UNIT=promptdeck-api — FastAPI unit (restart).
#   NGINX_ACTION=reload|restart — reload is default (picks up new static files without dropping connections).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/pnpm.sh
source "$ROOT/scripts/pnpm.sh"

cd "$ROOT/frontend"
echo "Building frontend → frontend/dist"
run_pnpm run build

if [[ "${BUILD_ONLY:-0}" == "1" ]]; then
  echo "BUILD_ONLY=1: skipping systemctl."
  exit 0
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; frontend build finished. Reload/restart nginx and the API on this host manually if needed."
  exit 0
fi

SUDO=()
if [[ "$(id -u)" -ne 0 ]]; then
  SUDO=(sudo)
fi

NGINX_UNIT="${NGINX_UNIT:-nginx}"
API_UNIT="${API_UNIT:-promptdeck-api}"
NGINX_ACTION="${NGINX_ACTION:-reload}"

case "$NGINX_ACTION" in
reload | restart) ;;
*)
  echo "NGINX_ACTION must be reload or restart, got: $NGINX_ACTION" >&2
  exit 1
  ;;
esac

echo "systemctl $NGINX_ACTION $NGINX_UNIT"
"${SUDO[@]}" systemctl "$NGINX_ACTION" "$NGINX_UNIT"

echo "systemctl restart $API_UNIT"
"${SUDO[@]}" systemctl restart "$API_UNIT"

echo "Done."
