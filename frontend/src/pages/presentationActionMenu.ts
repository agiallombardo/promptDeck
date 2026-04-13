export type PresentationActionMenuId =
  | "share"
  | "export-pdf"
  | "export-html"
  | "add-comment"
  | "toggle-comments"
  | "upload-version"
  | "upload-source"
  | "edit-code"
  | "edit-with-prompt"
  | "import-diagram-source"
  | "save-diagram";

export type PresentationActionMenuEntry = {
  id: PresentationActionMenuId;
  label: string;
  disabled?: boolean;
};

export type PresentationActionMenuInput = {
  canManage: boolean;
  hasAccessToken: boolean;
  hasCurrentVersion: boolean;
  isDiagram: boolean;
  canPromptEdit: boolean;
  showCommentAction: boolean;
  showCommentsVisibilityToggle: boolean;
  commentsHidden: boolean;
  exportBusy: "pdf" | "single_html" | null;
  codeLoadBusy: boolean;
  codeSaveBusy: boolean;
  deckPromptBusy: boolean;
  diagramDirty: boolean;
  saveDiagramPending: boolean;
};

export function buildPresentationActionMenuEntries(
  input: PresentationActionMenuInput,
): PresentationActionMenuEntry[] {
  const entries: PresentationActionMenuEntry[] = [];

  if (input.canManage && input.hasAccessToken) {
    entries.push({ id: "share", label: "Share" });
  }
  if (input.canManage && input.hasAccessToken && input.hasCurrentVersion) {
    entries.push({
      id: "export-pdf",
      label: input.exportBusy === "pdf" ? "Exporting PDF…" : "Export PDF",
      disabled: input.exportBusy != null,
    });
    entries.push({
      id: "export-html",
      label: input.exportBusy === "single_html" ? "Exporting HTML…" : "Export Single-file HTML",
      disabled: input.exportBusy != null,
    });
  }
  if (input.showCommentAction) {
    entries.push({ id: "add-comment", label: "Add comment" });
  }
  if (input.showCommentsVisibilityToggle) {
    entries.push({
      id: "toggle-comments",
      label: input.commentsHidden ? "Show comments" : "Hide comments",
    });
  }
  if (input.canManage && input.hasAccessToken && !input.isDiagram) {
    entries.push({
      id: "upload-version",
      label: input.hasCurrentVersion ? "Upload new version" : "Upload HTML or zip",
    });
  }
  if (input.canManage && input.hasAccessToken && !input.isDiagram && input.hasCurrentVersion) {
    entries.push({ id: "upload-source", label: "Upload source" });
  }
  if (input.canPromptEdit && input.hasCurrentVersion) {
    entries.push({
      id: "edit-code",
      label: "Edit code",
      disabled: input.codeLoadBusy || input.codeSaveBusy,
    });
    entries.push({
      id: "edit-with-prompt",
      label: "Edit with prompt",
      disabled: input.deckPromptBusy,
    });
  }
  if (input.canManage && input.hasAccessToken && input.isDiagram) {
    entries.push({ id: "import-diagram-source", label: "Import diagram source" });
    entries.push({
      id: "save-diagram",
      label: input.saveDiagramPending ? "Saving…" : input.diagramDirty ? "Save diagram" : "Saved",
      disabled: !input.diagramDirty || input.saveDiagramPending,
    });
  }

  return entries;
}
