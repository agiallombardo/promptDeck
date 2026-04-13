import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { PromptDeckHomeLink } from "./PromptDeckHomeLink";

function wrap(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("PromptDeckHomeLink", () => {
  it("links to file manager with accessible home label", () => {
    wrap(<PromptDeckHomeLink />);
    const link = screen.getByRole("link", { name: /Home — file manager/i });
    expect(link.getAttribute("href")).toBe("/files");
  });

  it("optionally shows wordmark", () => {
    wrap(<PromptDeckHomeLink showWordmark />);
    expect(screen.getByText("promptDeck")).toBeDefined();
  });
});
