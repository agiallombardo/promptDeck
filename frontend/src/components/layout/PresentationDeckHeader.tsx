import { useEffect, useRef, useState, type ReactNode } from "react";
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

function IconShare() {
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
      <path d="M8 10V2m0 0L5 5m3-3 3 3" />
      <path d="M3 9v4a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" />
    </svg>
  );
}

function IconDownload() {
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
      <path d="M8 2v8m0 0 3-3M8 10 5 7" />
      <path d="M3 11v2a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-2" />
    </svg>
  );
}

function IconUpload() {
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
      <path d="M3 11.5a2 2 0 0 1 0-4 3.2 3.2 0 0 1 6-1.2A2.5 2.5 0 1 1 13 11.5H9" />
      <path d="M8 13.5V7.8m0 0-2 2m2-2 2 2" />
    </svg>
  );
}

function IconComment() {
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
      <path d="M3 3.5h10v7H8l-3.5 2v-2H3z" />
      <path d="M8 5.5v3M6.5 7h3" />
    </svg>
  );
}

function IconEye() {
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
      <path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8s-2.5 4.5-6.5 4.5S1.5 8 1.5 8Z" />
      <circle cx="8" cy="8" r="2" />
    </svg>
  );
}

function IconEyeOff() {
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
      <path d="M6.59 6.59a2 2 0 0 0 2.82 2.82" />
      <path d="M10.73 10.73A6.2 6.2 0 0 1 8 12.5C4 12.5 1.5 8 1.5 8a11.2 11.2 0 0 1 3.77-3.73m2.3-.93A5.4 5.4 0 0 1 8 3.5c4 0 6.5 4.5 6.5 4.5a11.3 11.3 0 0 1-1.77 2.23" />
      <path d="m2 2 12 12" />
    </svg>
  );
}

function IconUploadVersion() {
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
      <path d="M3 11.5a2 2 0 0 1 0-4 3.2 3.2 0 0 1 6-1.2A2.5 2.5 0 1 1 13 11.5H9" />
      <path d="M8 13.5V7.8m0 0-2 2m2-2 2 2" />
    </svg>
  );
}

function IconSourceFile() {
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
      <path d="M4 2.5h5l3 3V13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" />
      <path d="M9 2.5V6h3" />
      <path d="M5.5 10h5M5.5 12h5" />
    </svg>
  );
}

function IconCode() {
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
      <path d="m6 4-3 4 3 4M10 4l3 4-3 4M9 3 7 13" />
    </svg>
  );
}

function IconMagic() {
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
      <path d="m3 13 6.8-6.8a1.2 1.2 0 0 1 1.7 0l.3.3a1.2 1.2 0 0 1 0 1.7L5 15" />
      <path d="M9.5 2.5v2M8.5 3.5h2M13 5v2M12 6h2" />
    </svg>
  );
}

function IconDiagramImport() {
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
      <circle cx="3" cy="8" r="1.5" />
      <circle cx="8" cy="3" r="1.5" />
      <circle cx="13" cy="8" r="1.5" />
      <path d="M4.5 7 6.5 4.7M9.5 4.7 11.5 7" />
      <path d="M8 14V9.5m0 0-2 2m2-2 2 2" />
    </svg>
  );
}

function IconSave() {
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
      <path d="M3 2.5h8l2 2V13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
      <path d="M5 2.5v4h5v-4M5.5 10.5h5" />
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

function iconForAction(id: string, label: string) {
  if (id === "share") return <IconShare />;
  if (id === "add-comment") return <IconComment />;
  if (id === "toggle-comments") return label.includes("Show") ? <IconEye /> : <IconEyeOff />;
  if (id === "upload-version") return <IconUploadVersion />;
  if (id === "upload-source") return <IconSourceFile />;
  if (id === "edit-code") return <IconCode />;
  if (id === "edit-with-prompt") return <IconMagic />;
  if (id === "import-diagram-source") return <IconDiagramImport />;
  if (id === "save-diagram") return <IconSave />;
  return <IconSourceFile />;
}

/* ── Shared button classes ─────────────────────────────────────────── */

const actionBtn =
  "inline-flex items-center gap-1.5 rounded-sharp border border-border bg-bg-elevated/60 px-2.5 py-1.5 font-mono text-xs text-text-main transition-colors duration-150 hover:bg-bg-elevated disabled:pointer-events-none disabled:opacity-40";

const exportTriggerBtn =
  "inline-flex items-center gap-1.5 rounded-sharp border border-border bg-bg-elevated/70 px-2.5 py-1.5 font-mono text-xs text-text-main transition-colors duration-150 hover:bg-bg-elevated disabled:pointer-events-none disabled:opacity-40";

const primaryBtn =
  "inline-flex items-center gap-1.5 rounded-sharp bg-primary/10 px-2.5 py-1.5 font-mono text-xs text-primary ring-1 ring-primary/30 transition-colors duration-150 hover:bg-primary/20 active:scale-[0.97] active:transition-transform active:duration-75";

function ZoneDivider() {
  return <div className="mx-1 hidden h-5 border-l border-border sm:block" aria-hidden />;
}

function ActionButton({ item }: { item: PresentationHeaderActionItem }) {
  return (
    <button type="button" className={actionBtn} disabled={item.disabled} onClick={item.onSelect}>
      <span className="inline-flex h-4 w-4 items-center justify-center text-primary">
        {iconForAction(item.id, item.label)}
      </span>
      <span>{item.label}</span>
    </button>
  );
}

function GroupedDropdown({
  triggerLabel,
  triggerIcon,
  items,
}: {
  triggerLabel: string;
  triggerIcon: ReactNode;
  items: PresentationHeaderActionItem[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const disabled = items.every((item) => item.disabled);

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
        className={exportTriggerBtn}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="inline-flex h-4 w-4 items-center justify-center text-primary">
          {triggerIcon}
        </span>
        <span>{triggerLabel}</span>
        <IconChevronDown />
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1.5 min-w-[12.5rem] rounded-sharp border border-border bg-bg-elevated p-1 shadow-elevated"
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
              <span className="inline-flex h-4 w-4 items-center justify-center text-primary">
                {iconForAction(item.id, item.label)}
              </span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

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
  const exportItems = visibleActionItems.filter(
    (item) => item.id === "export-pdf" || item.id === "export-html",
  );
  const uploadItems = visibleActionItems.filter(
    (item) =>
      item.id === "upload-version" ||
      item.id === "upload-source" ||
      item.id === "import-diagram-source",
  );
  const editItems = visibleActionItems.filter(
    (item) => item.id === "edit-code" || item.id === "edit-with-prompt",
  );

  let exportRendered = false;
  let uploadRendered = false;
  let editRendered = false;

  return (
    <header className="border-b border-border bg-bg-recessed px-3 py-2.5 sm:px-4 sm:py-3">
      <div className="mx-auto flex w-full max-w-[min(88rem,100%)] flex-wrap items-center justify-between gap-2 sm:gap-3">
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

        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {visibleActionItems.map((item) => {
            if ((item.id === "export-pdf" || item.id === "export-html") && exportItems.length > 1) {
              if (exportRendered) return null;
              exportRendered = true;
              return (
                <GroupedDropdown
                  key="export-group"
                  triggerLabel="Export"
                  triggerIcon={<IconDownload />}
                  items={exportItems}
                />
              );
            }
            if (
              (item.id === "upload-version" ||
                item.id === "upload-source" ||
                item.id === "import-diagram-source") &&
              uploadItems.length > 1
            ) {
              if (uploadRendered) return null;
              uploadRendered = true;
              return (
                <GroupedDropdown
                  key="upload-group"
                  triggerLabel="Upload"
                  triggerIcon={<IconUpload />}
                  items={uploadItems}
                />
              );
            }
            if (
              (item.id === "edit-code" || item.id === "edit-with-prompt") &&
              editItems.length > 1
            ) {
              if (editRendered) return null;
              editRendered = true;
              return (
                <GroupedDropdown
                  key="edit-group"
                  triggerLabel="Edit"
                  triggerIcon={<IconCode />}
                  items={editItems}
                />
              );
            }
            return <ActionButton key={item.id} item={item} />;
          })}

          {visibleActionItems.length ? <ZoneDivider /> : null}

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
