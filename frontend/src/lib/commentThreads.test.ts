import { describe, expect, it } from "vitest";
import type { ThreadDto } from "./api";
import { shouldShowFeedbackUi, visibleCommentThreads } from "./commentThreads";

function mkThread(id: string, commentsCount: number): ThreadDto {
  return {
    id,
    presentation_id: "550e8400-e29b-41d4-a716-446655440001",
    version_id: "550e8400-e29b-41d4-a716-446655440002",
    target_kind: "slide",
    target_id: null,
    slide_index: 0,
    anchor_x: 0.5,
    anchor_y: 0.5,
    status: "open",
    created_by: null,
    created_at: "2026-01-01T00:00:00Z",
    resolved_at: null,
    comments: Array.from({ length: commentsCount }).map((_, idx) => ({
      id: `550e8400-e29b-41d4-a716-4466554401${idx.toString().padStart(2, "0")}`,
      author_id: "550e8400-e29b-41d4-a716-446655440004",
      author_display_name: "Someone",
      body: `Comment ${idx + 1}`,
      body_format: "markdown",
      created_at: "2026-01-01T00:00:00Z",
      edited_at: null,
    })),
  };
}

describe("comment thread visibility", () => {
  it("filters out threads with zero comments", () => {
    const out = visibleCommentThreads([mkThread("t-1", 1), mkThread("t-2", 0), mkThread("t-3", 2)]);
    expect(out.map((t) => t.id)).toEqual(["t-1", "t-3"]);
  });

  it("hides feedback when no comments and no compose state", () => {
    expect(
      shouldShowFeedbackUi({
        commentsHidden: false,
        hasVisibleComments: false,
        commentMode: false,
        hasPendingPin: false,
        draftNewThread: "   ",
      }),
    ).toBe(false);
  });

  it("shows feedback during compose state even with zero comments", () => {
    expect(
      shouldShowFeedbackUi({
        commentsHidden: false,
        hasVisibleComments: false,
        commentMode: true,
        hasPendingPin: false,
        draftNewThread: "",
      }),
    ).toBe(true);
  });

  it("respects manual comments-hidden state", () => {
    expect(
      shouldShowFeedbackUi({
        commentsHidden: true,
        hasVisibleComments: true,
        commentMode: true,
        hasPendingPin: true,
        draftNewThread: "x",
      }),
    ).toBe(false);
  });
});
