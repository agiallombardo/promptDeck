import { Link } from "react-router-dom";

type Props = {
  title: string;
  accessRole: string | null;
  showShareAction: boolean;
  showExportAction: boolean;
  onShare: () => void;
  onExportPdf: () => void;
  onExportHtml: () => void;
  /** Which export is running, if any (disables both buttons). */
  exportBusy?: "pdf" | "single_html" | null;
  showPresentAction: boolean;
  onPresent: () => void;
  isFullscreen: boolean;
  slideIndex: number;
  slideCount: number;
  canNavigate: boolean;
  onPrev: () => void;
  onNext: () => void;
  /** Presenter-friendly: hide markers and sidebar threads. */
  showCommentsVisibilityToggle?: boolean;
  commentsHidden?: boolean;
  onToggleCommentsHidden?: () => void;
};

export function PresentationDeckHeader({
  title,
  accessRole,
  showShareAction,
  showExportAction,
  onShare,
  onExportPdf,
  onExportHtml,
  exportBusy = null,
  showPresentAction,
  onPresent,
  isFullscreen,
  slideIndex,
  slideCount,
  canNavigate,
  onPrev,
  onNext,
  showCommentsVisibilityToggle = false,
  commentsHidden = false,
  onToggleCommentsHidden,
}: Props) {
  return (
    <header className="border-b border-border bg-bg-recessed px-3 py-2.5 sm:px-4 sm:py-3">
      <div className="mx-auto flex w-full max-w-[min(88rem,100%)] flex-wrap items-center justify-between gap-2 sm:gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            to="/files"
            className="shrink-0 rounded-sharp outline-none ring-primary focus-visible:ring-2"
            title="Home"
            aria-label="Home — file manager"
          >
            <img
              src="/favicon.svg"
              alt=""
              width={28}
              height={28}
              className="h-7 w-7 opacity-90 hover:opacity-100"
            />
          </Link>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wide text-primary">Deck</p>
            <h1 className="max-w-[min(100%,42rem)] font-heading text-[clamp(1rem,0.92rem+0.35vw,1.125rem)] font-semibold leading-tight">
              {title}
            </h1>
            {accessRole ? (
              <p className="mt-0.5 font-mono text-[10px] text-text-muted">Access · {accessRole}</p>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {showShareAction ? (
            <button
              type="button"
              className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
              onClick={onShare}
            >
              Share
            </button>
          ) : null}
          {showExportAction ? (
            <>
              <button
                type="button"
                className="hidden rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-50 md:inline-flex"
                disabled={exportBusy != null}
                onClick={onExportPdf}
              >
                {exportBusy === "pdf" ? "PDF…" : "Export PDF"}
              </button>
              <button
                type="button"
                className="hidden rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated disabled:opacity-50 md:inline-flex"
                disabled={exportBusy != null}
                onClick={onExportHtml}
              >
                {exportBusy === "single_html" ? "HTML…" : "Export HTML"}
              </button>
            </>
          ) : null}
          {showPresentAction ? (
            <button
              type="button"
              className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
              onClick={onPresent}
            >
              {isFullscreen ? "Exit full screen" : "Present"}
            </button>
          ) : null}
          {showCommentsVisibilityToggle && onToggleCommentsHidden ? (
            <button
              type="button"
              className="rounded-sharp border border-border px-2 py-1 font-mono text-xs hover:bg-bg-elevated"
              onClick={onToggleCommentsHidden}
            >
              {commentsHidden ? "Show comments" : "Hide comments"}
            </button>
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
