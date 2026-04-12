import { useEffect, useState } from "react";
import type { DeckPromptJobProgressSnapshot } from "../lib/deckPromptPoll";

export function formatDurationSeconds(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m}m ${r}s` : `${m}m`;
}

/** Wall-clock seconds while `active`, from `performance.now()` at mount. */
export function useWallClockElapsed(active: boolean): number {
  const [sec, setSec] = useState(0);

  useEffect(() => {
    if (!active) {
      setSec(0);
      return;
    }
    const start = performance.now();
    setSec(0);
    const id = window.setInterval(() => {
      setSec(Math.floor((performance.now() - start) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [active]);

  return sec;
}

function parseMs(iso: string | null | undefined): number | null {
  if (iso == null || iso === "") return null;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : null;
}

/**
 * Wall time from server `created_at` to `finished_at` (if done) or to now while the job is live.
 */
export function useJobWallTimeSeconds(
  snapshot: DeckPromptJobProgressSnapshot | null,
  ticking: boolean,
): number {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!ticking || !snapshot) return;
    const id = window.setInterval(() => setTick((x) => x + 1), 1000);
    return () => window.clearInterval(id);
  }, [ticking, snapshot]);

  if (!snapshot) return 0;

  const createdMs = parseMs(snapshot.createdAt);
  if (createdMs == null) return 0;

  const endMs = parseMs(snapshot.finishedAt);
  const terminal = snapshot.status === "succeeded" || snapshot.status === "failed";
  if (terminal && endMs != null) {
    return Math.max(0, Math.floor((endMs - createdMs) / 1000));
  }

  void tick;
  return Math.max(0, Math.floor((Date.now() - createdMs) / 1000));
}
