import { apiDeckPromptJobGet } from "./api";

export type DeckPromptProgress = { pct: number; msg: string };

const POLL_MS = 500;
const MAX_POLLS = 900;

export type PollDeckPromptJobOptions = {
  onProgress?: (p: DeckPromptProgress) => void;
  /** When true, the first status fetch runs immediately (e.g. following a job from URL). */
  firstPollImmediate?: boolean;
};

/**
 * Poll until the job reaches succeeded, failed, or max polls (still queued/running).
 */
export async function pollDeckPromptJobUntilTerminal(
  accessToken: string,
  jobId: string,
  options?: PollDeckPromptJobOptions,
): Promise<{ status: string; error: string | null }> {
  let status = "queued";
  let err: string | null = null;

  for (let i = 0; i < MAX_POLLS && status !== "succeeded" && status !== "failed"; i++) {
    if (!(options?.firstPollImmediate && i === 0)) {
      await new Promise((r) => setTimeout(r, POLL_MS));
    }
    const j = await apiDeckPromptJobGet(accessToken, jobId);
    status = j.status;
    err = j.error ?? null;
    options?.onProgress?.({
      pct: j.progress ?? 0,
      msg: (j.status_message ?? status).trim() || status,
    });
  }

  return { status, error: err };
}
