import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useComments } from "./useComments";

const mocks = vi.hoisted(() => ({
  apiThreadCreate: vi.fn(),
  apiThreadsList: vi.fn().mockResolvedValue({ items: [] }),
  apiCommentCreate: vi.fn(),
  apiCommentDelete: vi.fn(),
  apiThreadPatch: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  apiThreadsList: mocks.apiThreadsList,
  apiThreadCreate: mocks.apiThreadCreate,
  apiCommentCreate: mocks.apiCommentCreate,
  apiCommentDelete: mocks.apiCommentDelete,
  apiThreadPatch: mocks.apiThreadPatch,
}));

function NewThreadHarness() {
  const h = useComments("pres-id", "tok", "ver-id");
  return (
    <div>
      <input
        data-testid="draft"
        value={h.draftNewThread}
        onChange={(e) => h.setDraftNewThread(e.target.value)}
      />
      <button
        type="button"
        onClick={() =>
          h.createThread.mutate({
            pin: { slide: 0, x: 0.5, y: 0.5 },
            versionId: "ver-id",
            body: h.draftNewThread.trim() || "fallback",
          })
        }
      >
        Post thread
      </button>
    </div>
  );
}

function ReplyHarness() {
  const h = useComments("pres-id", "tok", "ver-id");
  return (
    <div>
      <input
        data-testid="reply-draft"
        value={h.replyDrafts["thread-1"] ?? ""}
        onChange={(e) => h.setReplyDrafts((prev) => ({ ...prev, "thread-1": e.target.value }))}
      />
      <button
        type="button"
        onClick={() =>
          h.addReply.mutate({
            threadId: "thread-1",
            body: (h.replyDrafts["thread-1"] ?? "").trim() || "x",
          })
        }
      >
        Send reply
      </button>
    </div>
  );
}

describe("useComments", () => {
  it("keeps new-thread draft when createThread fails", async () => {
    mocks.apiThreadCreate.mockRejectedValueOnce(new Error("network"));

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <NewThreadHarness />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByTestId("draft"), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: /post thread/i }));

    await waitFor(() => expect(mocks.apiThreadCreate).toHaveBeenCalled());
    expect((screen.getByTestId("draft") as HTMLInputElement).value).toBe("hello");
  });

  it("keeps reply draft when addReply fails", async () => {
    mocks.apiCommentCreate.mockRejectedValueOnce(new Error("network"));

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <ReplyHarness />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByTestId("reply-draft"), { target: { value: "reply text" } });
    fireEvent.click(screen.getByRole("button", { name: /send reply/i }));

    await waitFor(() => expect(mocks.apiCommentCreate).toHaveBeenCalled());
    expect((screen.getByTestId("reply-draft") as HTMLInputElement).value).toBe("reply text");
  });
});
