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
        accessRole={"owner"}
        showShareAction
        showExportAction
        onShare={() => {}}
        onExportPdf={() => {}}
        onExportHtml={() => {}}
        showPresentAction={false}
        onPresent={() => {}}
        isFullscreen={false}
        slideIndex={0}
        slideCount={1}
        canNavigate
        onPrev={() => {}}
        onNext={() => {}}
      />,
    );
    const exportPdfBtn = screen.getByRole("button", { name: "Export PDF" });
    expect(exportPdfBtn.className).toMatch(/hidden/);
    expect(exportPdfBtn.className).toMatch(/md:/);
  });
});
