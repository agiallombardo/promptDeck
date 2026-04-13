import {
  formatDurationSeconds,
  useJobWallTimeSeconds,
  useWallClockElapsed,
} from "../hooks/useDeckPromptJobTimers";
import type { DeckPromptJobProgressSnapshot } from "../lib/deckPromptPoll";

type Step = { label: string; done: boolean; active: boolean };

export type DeckPromptStepVariant = "deck" | "diagram";

function stepsForSnapshot(
  s: DeckPromptJobProgressSnapshot,
  variant: DeckPromptStepVariant,
): Step[] {
  const { status, progress } = s;
  const failed = status === "failed";
  const succeeded = status === "succeeded";
  const queuedDone = status !== "queued" || progress > 0;
  const readDone = progress >= 15 || succeeded || (failed && progress >= 15);
  const llmDone = progress >= 80 || succeeded || (failed && progress >= 80);
  const saveDone = succeeded || (failed && progress >= 80);

  const readLabel = variant === "diagram" ? "Reading diagram" : "Reading deck";

  const steps: Step[] = [
    { label: "Queued", done: queuedDone, active: false },
    { label: readLabel, done: readDone, active: false },
    { label: "Calling model", done: llmDone, active: false },
    { label: "Saving new version", done: saveDone, active: false },
  ];

  const activeIdx = steps.findIndex((x) => !x.done);
  if (activeIdx >= 0) steps[activeIdx].active = true;
  return steps;
}

const LLM_PHASE = (s: DeckPromptJobProgressSnapshot) =>
  s.status === "running" && s.progress >= 15 && s.progress < 80;

type Props = {
  title: string;
  snapshot: DeckPromptJobProgressSnapshot | null;
  /** Labels for the "reading source" step (deck vs diagram jobs). */
  stepVariant?: DeckPromptStepVariant;
  /** True while waiting on the network before the first job payload is available. */
  waitingSubmit?: boolean;
  /** True once we have a snapshot or are polling; `waitingSubmit` takes precedence for copy. */
  jobActive?: boolean;
  className?: string;
};

export function DeckPromptJobActivity({
  title,
  snapshot,
  stepVariant = "deck",
  waitingSubmit = false,
  jobActive = false,
  className = "",
}: Props) {
  const submitElapsed = useWallClockElapsed(waitingSubmit);
  const connectElapsed = useWallClockElapsed(Boolean(jobActive && !waitingSubmit && !snapshot));
  const jobWallSeconds = useJobWallTimeSeconds(
    snapshot,
    Boolean(snapshot && snapshot.status !== "succeeded" && snapshot.status !== "failed"),
  );

  const steps = snapshot ? stepsForSnapshot(snapshot, stepVariant) : null;
  const inLlmHold = snapshot ? LLM_PHASE(snapshot) : false;
  const pct = snapshot ? Math.min(100, Math.max(0, snapshot.progress)) : 0;

  return (
    <div className={className}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-xs text-text-muted">{title}</p>
        {waitingSubmit ? (
          <p className="font-mono text-[11px] text-primary tabular-nums">
            {formatDurationSeconds(submitElapsed)} creating job…
          </p>
        ) : snapshot ? (
          <p className="font-mono text-[11px] text-primary tabular-nums">
            {formatDurationSeconds(jobWallSeconds)} job time
          </p>
        ) : jobActive ? (
          <p className="font-mono text-[11px] text-text-muted tabular-nums">
            Connecting… {formatDurationSeconds(connectElapsed)}
          </p>
        ) : null}
      </div>

      <div className="relative mt-2 h-2 w-full overflow-hidden rounded-full bg-bg-recessed">
        {inLlmHold ? (
          <div className="pointer-events-none absolute inset-0 animate-pulse bg-primary/20" />
        ) : null}
        <div
          className={`relative h-full bg-primary transition-[width] duration-300 ${
            inLlmHold ? "opacity-90" : ""
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {snapshot ? (
        <>
          <p className="mt-1 font-mono text-[11px] text-text-main">{snapshot.statusMessage}</p>
          {steps ? (
            <ol className="mt-2 flex flex-wrap items-center gap-x-1 gap-y-1 font-mono text-[10px]">
              {steps.map((st, idx) => (
                <li
                  key={st.label}
                  className={`flex min-w-0 items-center gap-1 ${
                    st.active ? "text-primary" : st.done ? "text-text-muted" : "text-text-muted/70"
                  }`}
                >
                  <span className="w-3.5 shrink-0 text-center">
                    {st.done ? "✓" : st.active ? "›" : "○"}
                  </span>
                  <span className="max-w-[9rem] truncate sm:max-w-none">{st.label}</span>
                  {idx < steps.length - 1 ? (
                    <span className="mx-0.5 shrink-0 text-text-muted/50" aria-hidden>
                      ·
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
