import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { PresentationDeckHeader } from "./PresentationDeckHeader";

function wrap(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("PresentationDeckHeader", () => {
  it("hides Export on small breakpoints via responsive classes", () => {
    wrap(
      <PresentationDeckHeader
        title="T"
        isShareSession={false}
        shareRole={null}
        showOwnerActions
        onShare={() => {}}
        onExport={() => {}}
        slideIndex={0}
        slideCount={1}
        canNavigate
        onPrev={() => {}}
        onNext={() => {}}
      />,
    );
    const exportBtn = screen.getByRole("button", { name: "Export" });
    expect(exportBtn.className).toMatch(/hidden/);
    expect(exportBtn.className).toMatch(/md:/);
  });
});
