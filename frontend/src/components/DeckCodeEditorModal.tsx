import Editor from "@monaco-editor/react";
import { useEffect, useMemo, useState } from "react";

export type DeckCodeBuffers = {
  html: string;
  css: string;
  js: string;
};

type CodeTab = "html" | "css" | "js";

type Props = {
  open: boolean;
  loading: boolean;
  saving: boolean;
  loadError: string | null;
  conflictError: string | null;
  dirty: boolean;
  buffers: DeckCodeBuffers;
  onBuffersChange: (next: DeckCodeBuffers) => void;
  onRequestClose: () => void;
  onSave: () => void;
  onReload: () => void;
};

const tabButtonClass =
  "rounded-sharp border px-2.5 py-1 font-mono text-xs transition-colors duration-150";

export function DeckCodeEditorModal({
  open,
  loading,
  saving,
  loadError,
  conflictError,
  dirty,
  buffers,
  onBuffersChange,
  onRequestClose,
  onSave,
  onReload,
}: Props) {
  const [activeTab, setActiveTab] = useState<CodeTab>("html");

  useEffect(() => {
    if (open) setActiveTab("html");
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    function onKey(ev: KeyboardEvent) {
      const wantsSave = (ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "s";
      if (!wantsSave || loading || saving) return;
      ev.preventDefault();
      onSave();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [loading, onSave, open, saving]);

  const language = useMemo(() => {
    if (activeTab === "css") return "css";
    if (activeTab === "js") return "javascript";
    return "html";
  }, [activeTab]);

  const activeValue = useMemo(() => {
    if (activeTab === "css") return buffers.css;
    if (activeTab === "js") return buffers.js;
    return buffers.html;
  }, [activeTab, buffers.css, buffers.html, buffers.js]);

  function setActiveValue(next: string) {
    if (activeTab === "css") {
      onBuffersChange({ ...buffers, css: next });
      return;
    }
    if (activeTab === "js") {
      onBuffersChange({ ...buffers, js: next });
      return;
    }
    onBuffersChange({ ...buffers, html: next });
  }

  function handleClose() {
    if (dirty) {
      const ok = window.confirm("Discard unsaved code changes?");
      if (!ok) return;
    }
    onRequestClose();
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-scrim p-4"
      role="presentation"
      onMouseDown={(ev) => {
        if (ev.target === ev.currentTarget && !saving) handleClose();
      }}
    >
      <div
        className="flex h-[min(90vh,52rem)] w-full max-w-[min(96rem,100%)] flex-col rounded-sharp border border-border bg-bg-elevated shadow-elevated"
        role="dialog"
        aria-labelledby="deck-code-editor-title"
        onMouseDown={(ev) => ev.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 id="deck-code-editor-title" className="font-heading text-base font-semibold">
              Edit deck code
            </h2>
            <p className="font-mono text-[11px] text-text-muted">
              Use tabs for managed CSS/JS blocks. Save creates a new version.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-sharp border border-border px-3 py-1.5 font-mono text-xs text-text-muted hover:bg-bg-recessed disabled:opacity-50"
              disabled={saving}
              onClick={handleClose}
            >
              Close
            </button>
            <button
              type="button"
              className="rounded-sharp border border-primary bg-primary/15 px-3 py-1.5 font-mono text-xs text-primary hover:bg-primary/25 disabled:opacity-50"
              disabled={loading || saving || !buffers.html.trim()}
              onClick={onSave}
            >
              {saving ? "Saving…" : "Save version"}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 border-b border-border px-4 py-2">
          <button
            type="button"
            className={`${tabButtonClass} ${
              activeTab === "html"
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-text-muted hover:bg-bg-recessed"
            }`}
            onClick={() => setActiveTab("html")}
          >
            index.html
          </button>
          <button
            type="button"
            className={`${tabButtonClass} ${
              activeTab === "css"
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-text-muted hover:bg-bg-recessed"
            }`}
            onClick={() => setActiveTab("css")}
          >
            styles.css
          </button>
          <button
            type="button"
            className={`${tabButtonClass} ${
              activeTab === "js"
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-text-muted hover:bg-bg-recessed"
            }`}
            onClick={() => setActiveTab("js")}
          >
            scripts.js
          </button>
          <div className="ml-auto font-mono text-[11px] text-text-muted">
            {dirty ? "Unsaved changes" : "Saved"}
          </div>
        </div>

        {conflictError ? (
          <div className="mx-4 mt-3 rounded-sharp border border-accent-warning/40 bg-accent-warning/10 px-3 py-2 font-mono text-xs text-accent-warning">
            {conflictError}
          </div>
        ) : null}

        {loadError ? (
          <div className="mx-4 mt-3 rounded-sharp border border-accent-warning/40 bg-accent-warning/10 px-3 py-2">
            <p className="font-mono text-xs text-accent-warning">{loadError}</p>
            <div className="mt-2">
              <button
                type="button"
                className="rounded-sharp border border-border px-2.5 py-1 font-mono text-xs text-text-muted hover:bg-bg-recessed"
                onClick={onReload}
              >
                Reload
              </button>
            </div>
          </div>
        ) : null}

        <div className="min-h-0 flex-1 p-4">
          {loading ? (
            <div className="flex h-full items-center justify-center font-mono text-xs text-text-muted">
              Loading code…
            </div>
          ) : (
            <Editor
              height="100%"
              language={language}
              value={activeValue}
              onChange={(value) => setActiveValue(value ?? "")}
              options={{
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 13,
                wordWrap: "on",
                lineNumbersMinChars: 3,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
