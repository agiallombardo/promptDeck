import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeedbackSidebar } from "./FeedbackSidebar";

describe("FeedbackSidebar", () => {
  it("hides write actions when canComment is false", () => {
    const noop = () => {};
    const thread = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      presentation_id: "550e8400-e29b-41d4-a716-446655440001",
      version_id: "550e8400-e29b-41d4-a716-446655440002",
      target_kind: "slide",
      slide_index: 0,
      anchor_x: 0.5,
      anchor_y: 0.5,
      status: "open" as const,
      created_by: null,
      created_at: "2026-01-01T00:00:00Z",
      resolved_at: null,
      comments: [
        {
          id: "550e8400-e29b-41d4-a716-446655440003",
          author_id: "550e8400-e29b-41d4-a716-446655440004",
          author_display_name: "Someone",
          body: "Hello",
          body_format: "markdown",
          created_at: "2026-01-01T00:00:00Z",
          edited_at: null,
        },
      ],
    };

    render(
      <FeedbackSidebar
        threads={[thread]}
        isLoading={false}
        error={null}
        canComment={false}
        currentUserId="550e8400-e29b-41d4-a716-446655440004"
        commentMode={false}
        onToggleCommentMode={noop}
        pendingPin={null}
        draftNewThread=""
        onDraftNewThread={noop}
        onSubmitNewThread={noop}
        onClearPending={noop}
        onRefresh={noop}
        replyDrafts={{}}
        onReplyDraft={noop}
        onReply={noop}
        onResolve={noop}
        onDeleteComment={noop}
      />,
    );

    expect(screen.queryByRole("button", { name: "Resolve" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Send reply" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });
});
