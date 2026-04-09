#!/usr/bin/env bash
# Sourced by repo scripts — use system pnpm when present, else npx (match frontend/package.json packageManager).
run_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$@"
  else
    npx --yes pnpm@10.33.0 "$@"
  fi
}
