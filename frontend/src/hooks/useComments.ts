import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { PendingPin } from "../components/feedback/FeedbackSidebar";
import {
  apiCommentCreate,
  apiCommentDelete,
  apiThreadCreate,
  apiThreadPatch,
  apiThreadsList,
} from "../lib/api";

export function useComments(
  presentationId: string,
  token: string | null,
  versionId: string | null | undefined,
) {
  const qc = useQueryClient();
  const [commentMode, setCommentMode] = useState(false);
  const [pendingPin, setPendingPin] = useState<PendingPin | null>(null);
  const [draftNewThread, setDraftNewThread] = useState("");
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});

  const threads = useQuery({
    queryKey: ["threads", presentationId, token, versionId],
    queryFn: () => apiThreadsList(token!, presentationId, versionId ?? null),
    enabled: Boolean(token) && Boolean(versionId),
  });

  const createThread = useMutation({
    mutationFn: (args: { pin: PendingPin; versionId: string; body: string }) =>
      apiThreadCreate(token!, presentationId, {
        version_id: args.versionId,
        slide_index: args.pin.slide,
        anchor_x: args.pin.x,
        anchor_y: args.pin.y,
        first_comment: args.body,
      }),
    onSuccess: async () => {
      setPendingPin(null);
      setDraftNewThread("");
      await qc.invalidateQueries({ queryKey: ["threads", presentationId, token] });
    },
    onError: () => undefined,
  });

  const addReply = useMutation({
    mutationFn: ({ threadId, body }: { threadId: string; body: string }) =>
      apiCommentCreate(token!, threadId, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", presentationId, token] });
    },
    onError: () => undefined,
  });

  const resolveThread = useMutation({
    mutationFn: (threadId: string) => apiThreadPatch(token!, threadId, "resolved"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", presentationId, token] });
    },
  });

  const deleteComment = useMutation({
    mutationFn: (commentId: string) => apiCommentDelete(token!, commentId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["threads", presentationId, token] });
    },
  });

  return {
    threads,
    commentMode,
    setCommentMode,
    pendingPin,
    setPendingPin,
    draftNewThread,
    setDraftNewThread,
    replyDrafts,
    setReplyDrafts,
    createThread,
    addReply,
    resolveThread,
    deleteComment,
    qc,
  };
}
