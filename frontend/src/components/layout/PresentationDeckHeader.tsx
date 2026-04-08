import { Link } from "react-router-dom";

type Props = {
  title: string;
  isShareSession: boolean;
  shareRole: string | null;
  showOwnerActions: boolean;
  onShare: () => void;
  onExport: () => void;
  slideIndex: number;
  slideCount: number;
  canNavigate: boolean;
  onPrev: () => void;
  onNext: () => void;
};

export function PresentationDeckHeader({
  title,
  isShareSession,
  shareRole,
  showOwnerActions,
  onShare,
  onExport,
  slideIndex,
  slideCount,
  canNavigate,
  onPrev,
  onNext,
}: Props) {
  return (
    <header className="border-b border-border bg-bg-recessed px-4 py-3">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <Link className="font-mono text-sm text-text-muted hover:text-primary" to="/files">
            ← Files
          </Link>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wide text-primary">Deck</p>
            <h1 className="font-heading text-lg font-semibold leading-tight">{title}</h1>
            {isShareSession ? (
              <p className="mt-0.5 font-mono text-[10px] text-text-muted">
                Shared access{shareRole ? ` · ${shareRole}` : ""}
              </p>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {showOwnerActions ? (
            <>
              <button
                type="button"
                className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
                onClick={onShare}
              >
                Share
              </button>
              <button
                type="button"
                className="hidden rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated md:inline-flex"
                onClick={onExport}
              >
                Export
              </button>
            </>
          ) : null}
          <span className="font-mono text-xs text-text-muted">
            Slide {slideCount ? slideIndex + 1 : 0} / {slideCount || "—"}
          </span>
          <div className="flex gap-1">
            <button
              type="button"
              className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-40"
              disabled={!canNavigate || slideIndex <= 0}
              onClick={onPrev}
            >
              Prev
            </button>
            <button
              type="button"
              className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-40"
              disabled={!canNavigate || slideIndex >= slideCount - 1}
              onClick={onNext}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
