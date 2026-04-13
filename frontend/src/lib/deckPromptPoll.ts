import type { DeckPromptJobDto } from "./api";
import { apiDeckPromptJobGet } from "./api";

export type DeckPromptJobProgressSnapshot = {
  status: string;
  progress: number;
  statusMessage: string;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  llmModel: string | null;
  promptTokens: number | null;
  completionTokens: number | null;
  totalTokens: number | null;
  /** Successful status polls since this wait began (each reflects a server read). */
  pollSequence: number;
};

export function deckPromptJobSnapshotFromApi(
  job: DeckPromptJobDto,
  pollSequence: number,
): DeckPromptJobProgressSnapshot {
  const status = job.status;
  const msg = (job.status_message ?? status).trim() || status;
  return {
    status,
    progress: job.progress ?? 0,
    statusMessage: msg,
    createdAt: job.created_at,
    startedAt: job.started_at ?? null,
    finishedAt: job.finished_at ?? null,
    llmModel: job.llm_model ?? null,
    promptTokens: job.prompt_tokens ?? null,
    completionTokens: job.completion_tokens ?? null,
    totalTokens: job.total_tokens ?? null,
    pollSequence,
  };
}

const POLL_MS = 500;
const MAX_POLLS = 900;

export type PollDeckPromptJobOptions = {
  onProgress?: (p: DeckPromptJobProgressSnapshot) => void;
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
  let pollSequence = 0;

  for (let i = 0; i < MAX_POLLS; i++) {
    if (!(options?.firstPollImmediate && i === 0)) {
      await new Promise((r) => setTimeout(r, POLL_MS));
    }
    const j = await apiDeckPromptJobGet(accessToken, jobId);
    status = j.status;
    err = j.error ?? null;
    pollSequence += 1;
    options?.onProgress?.(deckPromptJobSnapshotFromApi(j, pollSequence));
    if (status === "succeeded" || status === "failed") {
      break;
    }
  }

  return { status, error: err };
}
