import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { PresentationDeckHeader } from "./PresentationDeckHeader";

function wrap(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

const baseProps = {
  title: "T",
  accessRole: "owner" as const,
  showShareAction: true,
  showExportAction: true,
  onShare: vi.fn(),
  onExportPdf: vi.fn(),
  onExportHtml: vi.fn(),
  showPresentAction: false,
  onPresent: vi.fn(),
  isFullscreen: false,
  slideIndex: 0,
  slideCount: 1,
  canNavigate: true,
  onPrev: vi.fn(),
  onNext: vi.fn(),
};

describe("PresentationDeckHeader", () => {
  it("renders Export dropdown that reveals PDF and HTML options", () => {
    wrap(<PresentationDeckHeader {...baseProps} />);

    const exportBtn = screen.getByRole("button", { name: /Export/i });
    expect(exportBtn).toBeDefined();
    expect(exportBtn.getAttribute("aria-haspopup")).toBe("menu");

    expect(screen.queryByRole("menu")).toBeNull();

    fireEvent.click(exportBtn);

    const menu = screen.getByRole("menu");
    expect(menu).toBeDefined();
    expect(screen.getByRole("menuitem", { name: /PDF/i })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: /HTML/i })).toBeDefined();
  });

  it("Export label text is hidden on small screens via responsive class", () => {
    wrap(<PresentationDeckHeader {...baseProps} />);

    const exportBtns = screen.getAllByRole("button", { name: /Export/i });
    const exportBtn = exportBtns[exportBtns.length - 1];
    const labelSpan = exportBtn.querySelector("span");
    expect(labelSpan?.className).toMatch(/hidden/);
    expect(labelSpan?.className).toMatch(/md:/);
  });
});
