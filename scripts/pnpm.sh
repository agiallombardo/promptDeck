#!/usr/bin/env bash
# Sourced by repo scripts — use system pnpm when present, else npx pnpm@9.15.4.
run_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$@"
  else
    npx --yes pnpm@9.15.4 "$@"
  fi
}
