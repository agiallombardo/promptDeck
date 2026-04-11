#!/usr/bin/env bash
# Create an Azure AD (Microsoft Entra ID) app registration for promptDeck OIDC login.
# Requires: az CLI, signed-in account with permission to create applications.
#
# Usage:
#   export PROMPTDECK_PUBLIC_API_URL="https://api.example.com"   # origin of the FastAPI app
#   export AZURE_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # optional; default from az account
#   bash scripts/azure-entra-app-registration.sh
#
# After the script prints the client secret, store it via Admin → Identity / Entra or ENTRA_* env vars.
set -euo pipefail

API_BASE="${PROMPTDECK_PUBLIC_API_URL:?Set PROMPTDECK_PUBLIC_API_URL (e.g. https://api.example.com)}"
REDIRECT_URI="${API_BASE%/}/api/v1/auth/entra/callback"
DISPLAY_NAME="${ENTRA_APP_NAME:-promptDeck}"

echo "Redirect URI (add this in the portal if needed): ${REDIRECT_URI}"

APP_JSON="$(az ad app create \
  --display-name "${DISPLAY_NAME}" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "${REDIRECT_URI}" \
  --enable-id-token-issuance true \
  --query "{appId:appId}" -o json)"
CLIENT_ID="$(echo "${APP_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['appId'])")"

echo "Application (client) ID: ${CLIENT_ID}"

SECRET_JSON="$(az ad app credential reset --id "${CLIENT_ID}" --query "{password:password}" -o json)"
CLIENT_SECRET="$(echo "${SECRET_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")"

echo "Client secret (save once; rotate in portal if lost): ${CLIENT_SECRET}"

TENANT="$(az account show --query tenantId -o tsv 2>/dev/null || true)"
if [[ -n "${AZURE_TENANT_ID:-}" ]]; then
  TENANT="${AZURE_TENANT_ID}"
fi
echo "Directory (tenant) ID: ${TENANT:-unknown}"

echo ""
echo "Next: grant admin consent if required, then configure promptDeck with tenant, client ID, and secret."
