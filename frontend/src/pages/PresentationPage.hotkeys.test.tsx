import { describe, expect, it } from "vitest";
import { shouldIgnoreDeckHotkeys } from "../lib/hotkeys";

describe("shouldIgnoreDeckHotkeys", () => {
  it("returns true for editable form controls", () => {
    const input = document.createElement("input");
    const textarea = document.createElement("textarea");
    const select = document.createElement("select");
    const editable = document.createElement("div");
    editable.contentEditable = "true";

    expect(shouldIgnoreDeckHotkeys(input)).toBe(true);
    expect(shouldIgnoreDeckHotkeys(textarea)).toBe(true);
    expect(shouldIgnoreDeckHotkeys(select)).toBe(true);
    expect(shouldIgnoreDeckHotkeys(editable)).toBe(true);
  });

  it("returns false for non-editable elements", () => {
    const div = document.createElement("div");
    expect(shouldIgnoreDeckHotkeys(div)).toBe(false);
    expect(shouldIgnoreDeckHotkeys(null)).toBe(false);
  });
});
