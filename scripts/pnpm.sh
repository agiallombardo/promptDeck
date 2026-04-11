#!/usr/bin/env bash
# Sourced by repo scripts — use system pnpm when present, else npx (match frontend/package.json packageManager).
run_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$@"
  else
    local cache_root
    cache_root="${TMPDIR:-/tmp}/promptdeck-npm-cache-${UID:-0}"
    mkdir -p "$cache_root"
    npm_config_cache="$cache_root" npx --yes pnpm@10.33.0 "$@"
  fi
}
