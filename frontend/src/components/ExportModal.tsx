import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiExportCreate, apiExportGet } from "../lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  accessToken: string;
  presentationId: string;
  versionId: string | null;
};

export function ExportModal({ open, onClose, accessToken, presentationId, versionId }: Props) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [poll, setPoll] = useState<{
    status: string;
    progress: number;
    output_path: string | null;
    error: string | null;
  } | null>(null);

  const start = useMutation({
    mutationFn: () =>
      apiExportCreate(accessToken, presentationId, {
        format: "pdf",
        version_id: versionId ?? undefined,
      }),
    onSuccess: (job) => {
      setJobId(job.id);
      setPoll({
        status: job.status,
        progress: job.progress,
        output_path: job.output_path,
        error: job.error,
      });
    },
  });

  useEffect(() => {
    if (!open) {
      setJobId(null);
      setPoll(null);
      return;
    }
    if (!jobId) return;

    let cancelled = false;
    const id = window.setInterval(() => {
      void (async () => {
        try {
          const j = await apiExportGet(accessToken, jobId);
          if (cancelled) return;
          setPoll({
            status: j.status,
            progress: j.progress,
            output_path: j.output_path,
            error: j.error,
          });
          if (j.status === "succeeded" || j.status === "failed") {
            window.clearInterval(id);
          }
        } catch {
          if (!cancelled) {
            setPoll((p) =>
              p
                ? { ...p, status: "failed", error: "Could not load job status" }
                : {
                    status: "failed",
                    progress: 0,
                    output_path: null,
                    error: "Could not load job status",
                  },
            );
            window.clearInterval(id);
          }
        }
      })();
    }, 400);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [open, jobId, accessToken]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="export-modal-title" className="font-heading text-lg font-semibold">
              Export PDF
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Server-side stub writes a minimal PDF to storage. Download API is not wired yet — path
              is for operators.
            </p>
          </div>
          <button
            type="button"
            className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-recessed"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <button
          type="button"
          className="mt-4 rounded-sharp border border-primary bg-primary/10 px-3 py-2 font-mono text-xs text-primary hover:bg-primary/20 disabled:opacity-40"
          disabled={!versionId || start.isPending}
          autoFocus
          onClick={() => {
            setJobId(null);
            setPoll(null);
            start.mutate();
          }}
        >
          Start export
        </button>
        {start.error ? (
          <p className="mt-2 text-sm text-accent-warning" role="alert">
            {(start.error as Error).message}
          </p>
        ) : null}

        {poll ? (
          <div className="mt-4 rounded-sharp border border-border bg-bg-recessed p-3 font-mono text-xs">
            <p className="text-text-muted">
              Status: <span className="text-text-main">{poll.status}</span> · Progress:{" "}
              {poll.progress}%
            </p>
            {poll.output_path ? (
              <p className="mt-2 break-all text-text-main">{poll.output_path}</p>
            ) : null}
            {poll.error ? <p className="mt-2 text-accent-warning">{poll.error}</p> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
