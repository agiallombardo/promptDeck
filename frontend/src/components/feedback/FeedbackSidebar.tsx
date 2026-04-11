import type { CommentDto, ThreadDto } from "../../lib/api";

export type PendingPin = { slide: number; x: number; y: number };

type FeedbackSidebarProps = {
  threads: ThreadDto[];
  isLoading: boolean;
  isRefreshing?: boolean;
  error: string | null;
  canComment: boolean;
  currentUserId: string | null;
  commentMode: boolean;
  onToggleCommentMode: () => void;
  pendingPin: PendingPin | null;
  draftNewThread: string;
  onDraftNewThread: (value: string) => void;
  onSubmitNewThread: () => void;
  onClearPending: () => void;
  onRefresh: () => void;
  replyDrafts: Record<string, string>;
  onReplyDraft: (threadId: string, value: string) => void;
  onReply: (threadId: string) => void;
  onResolve: (threadId: string) => void;
  onDeleteComment: (commentId: string) => void;
  /** When true, drop desktop-only left border (e.g. mobile drawer). */
  embedded?: boolean;
  /** Collapse thread list (presenter mode). Requires `onShowCommentsUi`. */
  commentsUiHidden?: boolean;
  onShowCommentsUi?: () => void;
};

export function FeedbackSidebar({
  threads,
  isLoading,
  isRefreshing = false,
  error,
  canComment,
  currentUserId,
  commentMode,
  onToggleCommentMode,
  pendingPin,
  draftNewThread,
  onDraftNewThread,
  onSubmitNewThread,
  onClearPending,
  onRefresh,
  replyDrafts,
  onReplyDraft,
  onReply,
  onResolve,
  onDeleteComment,
  embedded = false,
  commentsUiHidden = false,
  onShowCommentsUi,
}: FeedbackSidebarProps) {
  if (commentsUiHidden && onShowCommentsUi) {
    return (
      <aside
        className={`flex w-full flex-col bg-bg-elevated md:max-w-sm ${
          embedded ? "border-0" : "border-border md:border-l"
        }`}
      >
        <div className="border-b border-border px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-wide text-primary">Feedback</p>
          <button
            type="button"
            className="mt-2 w-full rounded-sharp border border-border px-2 py-2 font-mono text-xs hover:bg-bg-recessed"
            onClick={onShowCommentsUi}
          >
            Show comments
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className={`flex w-full flex-col bg-bg-elevated md:max-w-sm ${
        embedded ? "border-0" : "border-border md:border-l"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wide text-primary">Feedback</p>
          <h2 className="font-heading text-sm font-semibold">Threads</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-recessed disabled:opacity-40"
            disabled={isRefreshing}
            onClick={onRefresh}
          >
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
          <button
            type="button"
            disabled={!canComment}
            className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-recessed disabled:opacity-40"
            onClick={onToggleCommentMode}
          >
            {commentMode ? "Exit pin mode" : "Pin comment"}
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {!canComment ? (
          <p className="text-sm text-text-muted">Viewers can read threads but cannot comment.</p>
        ) : null}

        {pendingPin ? (
          <div className="rounded-sharp border border-primary/40 bg-bg-recessed p-3">
            <p className="font-mono text-xs text-primary">
              New pin · slide {pendingPin.slide + 1} · ({pendingPin.x.toFixed(2)},{" "}
              {pendingPin.y.toFixed(2)})
            </p>
            <textarea
              className="mt-2 w-full rounded-sharp border border-border bg-bg-void px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
              rows={3}
              placeholder="First message…"
              value={draftNewThread}
              onChange={(ev) => onDraftNewThread(ev.target.value)}
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-sharp bg-primary/15 px-3 py-1 font-mono text-xs text-primary ring-1 ring-primary/40"
                onClick={onSubmitNewThread}
              >
                Post thread
              </button>
              <button
                type="button"
                className="rounded-sharp border border-border px-3 py-1 font-mono text-xs"
                onClick={onClearPending}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}

        {isLoading ? <p className="font-mono text-sm text-text-muted">Loading threads…</p> : null}
        {error ? (
          <p className="text-sm text-accent-warning" role="alert">
            {error}
          </p>
        ) : null}

        {!isLoading && !threads.length && !pendingPin ? (
          <p className="text-sm text-text-muted">
            No threads yet. Toggle pin mode and click the slide.
          </p>
        ) : null}

        {threads.map((t) => (
          <ThreadCard
            key={t.id}
            domId={`thread-card-${t.id}`}
            thread={t}
            currentUserId={currentUserId}
            replyDraft={replyDrafts[t.id] ?? ""}
            onReplyDraft={(v) => onReplyDraft(t.id, v)}
            onReply={() => onReply(t.id)}
            onResolve={() => onResolve(t.id)}
            onDeleteComment={onDeleteComment}
          />
        ))}
      </div>
    </aside>
  );
}

function ThreadCard({
  domId,
  thread,
  currentUserId,
  replyDraft,
  onReplyDraft,
  onReply,
  onResolve,
  onDeleteComment,
}: {
  domId: string;
  thread: ThreadDto;
  currentUserId: string | null;
  replyDraft: string;
  onReplyDraft: (v: string) => void;
  onReply: () => void;
  onResolve: () => void;
  onDeleteComment: (id: string) => void;
}) {
  return (
    <article id={domId} className="rounded-sharp border border-border bg-bg-recessed p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-mono text-xs text-text-muted">
            Slide {thread.slide_index + 1} · {thread.status}
          </p>
          <p className="font-mono text-[10px] text-text-muted">
            ({thread.anchor_x.toFixed(2)}, {thread.anchor_y.toFixed(2)})
          </p>
        </div>
        {thread.status === "open" ? (
          <button
            type="button"
            className="rounded-sharp border border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-text-muted hover:text-primary"
            onClick={onResolve}
          >
            Resolve
          </button>
        ) : null}
      </div>
      <ul className="mt-3 space-y-2">
        {thread.comments.map((c) => (
          <CommentLine
            key={c.id}
            comment={c}
            currentUserId={currentUserId}
            onDelete={() => onDeleteComment(c.id)}
          />
        ))}
      </ul>
      <div className="mt-3 space-y-2">
        <textarea
          className="w-full rounded-sharp border border-border bg-bg-void px-2 py-2 font-body text-sm text-text-main outline-none ring-primary focus:ring-1"
          rows={2}
          placeholder="Reply…"
          value={replyDraft}
          onChange={(ev) => onReplyDraft(ev.target.value)}
        />
        <button
          type="button"
          className="rounded-sharp bg-primary/10 px-3 py-1 font-mono text-xs text-primary ring-1 ring-primary/30"
          onClick={onReply}
        >
          Send reply
        </button>
      </div>
    </article>
  );
}

function CommentLine({
  comment,
  currentUserId,
  onDelete,
}: {
  comment: CommentDto;
  currentUserId: string | null;
  onDelete: () => void;
}) {
  const mine = Boolean(
    currentUserId && comment.author_id != null && comment.author_id === currentUserId,
  );
  const label =
    comment.author_display_name ??
    (comment.author_id ? comment.author_id.slice(0, 8) : "Unknown user");
  return (
    <li className="rounded-sharp border border-border/60 bg-bg-void/40 px-2 py-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-mono text-[10px] text-text-muted">{label}</p>
        {mine ? (
          <button
            type="button"
            className="font-mono text-[10px] text-accent-warning hover:underline"
            onClick={onDelete}
          >
            Delete
          </button>
        ) : null}
      </div>
      <p className="mt-1 whitespace-pre-wrap font-body text-sm text-text-main">{comment.body}</p>
    </li>
  );
}
