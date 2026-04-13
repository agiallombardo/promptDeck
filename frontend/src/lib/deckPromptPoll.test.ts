import { afterEach, describe, expect, it, vi } from "vitest";
import { pollDeckPromptJobUntilTerminal } from "./deckPromptPoll";
import { apiDeckPromptJobGet } from "./api";
import type { DeckPromptJobDto } from "./api";

vi.mock("./api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("./api")>();
  return {
    ...mod,
    apiDeckPromptJobGet: vi.fn(),
  };
});

const baseJob = {
  id: "00000000-0000-4000-8000-000000000001",
  presentation_id: "00000000-0000-4000-8000-000000000002",
  source_version_id: "00000000-0000-4000-8000-000000000003",
  job_type: "deck_generate" as const,
  is_generation: true,
  status_message: "Done",
  progress: 100,
  error: null,
  result_version_id: "00000000-0000-4000-8000-000000000004",
  llm_model: "test",
  prompt_tokens: 1,
  completion_tokens: 2,
  total_tokens: 3,
  created_at: "2026-01-01T00:00:00Z",
  started_at: "2026-01-01T00:00:01Z",
  finished_at: "2026-01-01T00:00:02Z",
} satisfies Omit<DeckPromptJobDto, "status">;

describe("pollDeckPromptJobUntilTerminal", () => {
  afterEach(() => {
    vi.mocked(apiDeckPromptJobGet).mockReset();
  });

  it("invokes onProgress for the first fetch when the job is already terminal", async () => {
    vi.mocked(apiDeckPromptJobGet).mockResolvedValue({
      ...baseJob,
      status: "succeeded",
    });

    const onProgress = vi.fn();

    const out = await pollDeckPromptJobUntilTerminal("token", baseJob.id, {
      firstPollImmediate: true,
      onProgress,
    });

    expect(out.status).toBe("succeeded");
    expect(onProgress).toHaveBeenCalledTimes(1);
    expect(onProgress.mock.calls[0]![0]).toMatchObject({
      status: "succeeded",
      progress: 100,
      pollSequence: 1,
    });
    expect(apiDeckPromptJobGet).toHaveBeenCalledTimes(1);
  });
});
