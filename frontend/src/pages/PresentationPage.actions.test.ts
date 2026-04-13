import { describe, expect, it } from "vitest";
import { buildPresentationActionMenuEntries } from "./presentationActionMenu";

const baseInput = {
  canManage: true,
  hasAccessToken: true,
  hasCurrentVersion: true,
  isDiagram: false,
  canPromptEdit: true,
  showCommentAction: true,
  showCommentsVisibilityToggle: true,
  commentsHidden: false,
  exportBusy: null as "pdf" | "single_html" | null,
  codeLoadBusy: false,
  codeSaveBusy: false,
  deckPromptBusy: false,
  diagramDirty: false,
  saveDiagramPending: false,
};

describe("buildPresentationActionMenuEntries", () => {
  it("includes shared and deck-specific actions for deck mode", () => {
    const entries = buildPresentationActionMenuEntries({ ...baseInput, isDiagram: false });
    const ids = entries.map((entry) => entry.id);

    expect(ids).toContain("share");
    expect(ids).toContain("export-pdf");
    expect(ids).toContain("export-html");
    expect(ids).toContain("add-comment");
    expect(ids).toContain("toggle-comments");
    expect(ids).toContain("upload-version");
    expect(ids).toContain("upload-source");
    expect(ids).toContain("edit-code");
    expect(ids).toContain("edit-with-prompt");

    expect(ids).not.toContain("import-diagram-source");
    expect(ids).not.toContain("save-diagram");
  });

  it("includes shared and diagram-specific actions for diagram mode", () => {
    const entries = buildPresentationActionMenuEntries({
      ...baseInput,
      isDiagram: true,
      canPromptEdit: false,
      showCommentAction: false,
      showCommentsVisibilityToggle: false,
    });
    const ids = entries.map((entry) => entry.id);

    expect(ids).toContain("share");
    expect(ids).toContain("export-pdf");
    expect(ids).toContain("export-html");
    expect(ids).toContain("import-diagram-source");
    expect(ids).toContain("save-diagram");

    expect(ids).not.toContain("upload-version");
    expect(ids).not.toContain("upload-source");
    expect(ids).not.toContain("edit-code");
    expect(ids).not.toContain("edit-with-prompt");
  });

  it("marks busy and unavailable actions as disabled", () => {
    const entries = buildPresentationActionMenuEntries({
      ...baseInput,
      isDiagram: true,
      exportBusy: "pdf",
      diagramDirty: false,
      saveDiagramPending: true,
      canPromptEdit: false,
      showCommentAction: false,
      showCommentsVisibilityToggle: false,
    });

    expect(entries.find((entry) => entry.id === "export-pdf")?.disabled).toBe(true);
    expect(entries.find((entry) => entry.id === "export-html")?.disabled).toBe(true);
    expect(entries.find((entry) => entry.id === "save-diagram")?.disabled).toBe(true);
    expect(entries.find((entry) => entry.id === "save-diagram")?.label).toBe("Saving…");
  });

  it("respects hidden-by-state conditions", () => {
    const entries = buildPresentationActionMenuEntries({
      ...baseInput,
      hasCurrentVersion: false,
      canPromptEdit: false,
      showCommentAction: false,
      showCommentsVisibilityToggle: false,
      isDiagram: false,
    });
    const ids = entries.map((entry) => entry.id);

    expect(ids).toContain("share");
    expect(ids).toContain("upload-version");

    expect(ids).not.toContain("export-pdf");
    expect(ids).not.toContain("export-html");
    expect(ids).not.toContain("upload-source");
    expect(ids).not.toContain("edit-code");
    expect(ids).not.toContain("edit-with-prompt");
  });
});
