import { useEffect, useRef, useState } from "react";
import { PromptDeckHomeLink } from "./PromptDeckHomeLink";

export type PresentationHeaderActionItem = {
  id: string;
  label: string;
  onSelect: () => void;
  disabled?: boolean;
  hidden?: boolean;
};

type Props = {
  title: string;
  /** Shown as the small uppercase label above the title (deck vs diagram). */
  titleKind?: "deck" | "diagram";
  accessRole: string | null;
  actionMenuItems?: PresentationHeaderActionItem[];
  showPresentAction: boolean;
  onPresent: () => void;
  isFullscreen: boolean;
  slideIndex: number;
  slideCount: number;
  canNavigate: boolean;
  onPrev: () => void;
  onNext: () => void;
};

/* ── Inline SVG icons (16×16, stroke-based, currentColor) ──────────── */

function IconActions() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="3" cy="8" r="1" />
      <circle cx="8" cy="8" r="1" />
      <circle cx="13" cy="8" r="1" />
    </svg>
  );
}

function IconChevronDown() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m3 4.5 3 3 3-3" />
    </svg>
  );
}

function IconPlay() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" stroke="none">
      <path d="M5.5 3.5a.75.75 0 0 1 1.15-.633l6 3.75a.75.75 0 0 1 0 1.266l-6 3.75A.75.75 0 0 1 5.5 11V3.5Z" />
    </svg>
  );
}

function IconMinimize() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 2v4H2M10 14v-4h4M2 6l4-4M14 10l-4 4" />
    </svg>
  );
}

function IconChevronLeft() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m8.5 3.5-3.5 3.5 3.5 3.5" />
    </svg>
  );
}

function IconChevronRight() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m5.5 3.5 3.5 3.5-3.5 3.5" />
    </svg>
  );
}

/* ── Shared button classes ─────────────────────────────────────────── */

const ghostBtn =
  "inline-flex items-center gap-1.5 rounded-sharp border border-border px-2.5 py-1.5 font-mono text-xs text-text-main transition-colors duration-150 hover:bg-bg-elevated active:scale-[0.97] active:transition-transform active:duration-75 disabled:pointer-events-none disabled:opacity-40";

const primaryBtn =
  "inline-flex items-center gap-1.5 rounded-sharp bg-primary/10 px-2.5 py-1.5 font-mono text-xs text-primary ring-1 ring-primary/30 transition-colors duration-150 hover:bg-primary/20 active:scale-[0.97] active:transition-transform active:duration-75";

/* ── Divider ───────────────────────────────────────────────────────── */

function ZoneDivider() {
  return <div className="mx-1 hidden h-5 border-l border-border sm:block" aria-hidden />;
}

/* ── Unified actions dropdown ──────────────────────────────────────── */

function ActionsDropdown({ items }: { items: PresentationHeaderActionItem[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className={ghostBtn}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <IconActions />
        <span>Actions</span>
        <IconChevronDown />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1.5 min-w-[12rem] rounded-sharp border border-border bg-bg-elevated p-1 shadow-elevated"
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-left font-mono text-xs text-text-main transition-colors duration-150 hover:bg-bg-recessed disabled:opacity-40"
              disabled={item.disabled}
              onClick={() => {
                if (item.disabled) return;
                item.onSelect();
                setOpen(false);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/* ── Main component ────────────────────────────────────────────────── */

export function PresentationDeckHeader({
  title,
  titleKind = "deck",
  accessRole,
  actionMenuItems = [],
  showPresentAction,
  onPresent,
  isFullscreen,
  slideIndex,
  slideCount,
  canNavigate,
  onPrev,
  onNext,
}: Props) {
  const prevDisabled = !canNavigate || slideIndex <= 0;
  const nextDisabled = !canNavigate || slideIndex >= slideCount - 1;
  const visibleActionItems = actionMenuItems.filter((item) => !item.hidden);
  const hasActionMenu = visibleActionItems.length > 0;

  return (
    <header className="border-b border-border bg-bg-recessed px-3 py-2.5 sm:px-4 sm:py-3">
      <div className="mx-auto flex w-full max-w-[min(88rem,100%)] flex-wrap items-center justify-between gap-2 sm:gap-3">
        {/* ── Left: branding + title ─────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-3">
          <PromptDeckHomeLink />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wide text-primary">
              {titleKind === "diagram" ? "Diagram" : "Deck"}
            </p>
            <h1 className="max-w-[min(100%,42rem)] font-heading text-[clamp(1rem,0.92rem+0.35vw,1.125rem)] font-semibold leading-tight">
              {title}
            </h1>
            {accessRole ? (
              <p className="mt-0.5 font-mono text-[10px] text-text-muted">Access · {accessRole}</p>
            ) : null}
          </div>
        </div>

        {/* ── Right: actions + presentation mode + slide nav ────── */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {hasActionMenu ? <ActionsDropdown items={visibleActionItems} /> : null}
          {hasActionMenu ? <ZoneDivider /> : null}

          {showPresentAction ? (
            <button type="button" className={primaryBtn} onClick={onPresent}>
              {isFullscreen ? <IconMinimize /> : <IconPlay />}
              <span>{isFullscreen ? "Exit" : "Present"}</span>
            </button>
          ) : null}

          {showPresentAction ? <ZoneDivider /> : null}

          <div className="inline-flex items-center overflow-hidden rounded-sharp border border-border">
            <button
              type="button"
              className="flex items-center px-2 py-1.5 text-text-muted transition-colors duration-150 hover:bg-bg-elevated disabled:opacity-30 disabled:hover:bg-transparent"
              disabled={prevDisabled}
              onClick={onPrev}
              aria-label="Previous slide"
            >
              <IconChevronLeft />
            </button>
            <span className="border-x border-border px-3 py-1.5 font-mono text-xs text-text-muted">
              {slideCount ? slideIndex + 1 : 0}
              <span className="mx-0.5">/</span>
              {slideCount || "\u2014"}
            </span>
            <button
              type="button"
              className="flex items-center px-2 py-1.5 text-text-muted transition-colors duration-150 hover:bg-bg-elevated disabled:opacity-30 disabled:hover:bg-transparent"
              disabled={nextDisabled}
              onClick={onNext}
              aria-label="Next slide"
            >
              <IconChevronRight />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
