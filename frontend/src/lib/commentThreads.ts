import type { ThreadDto } from "./api";

export function visibleCommentThreads(threads: ThreadDto[]): ThreadDto[] {
  return threads.filter((thread) => thread.comments.length > 0);
}

type FeedbackVisibilityArgs = {
  commentsHidden: boolean;
  hasVisibleComments: boolean;
  commentMode: boolean;
  hasPendingPin: boolean;
  draftNewThread: string;
};

export function shouldShowFeedbackUi(args: FeedbackVisibilityArgs): boolean {
  if (args.commentsHidden) return false;
  if (args.hasVisibleComments) return true;
  if (args.commentMode) return true;
  if (args.hasPendingPin) return true;
  return args.draftNewThread.trim().length > 0;
}
