import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { PresentationDeckHeader } from "./PresentationDeckHeader";

function wrap(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

afterEach(() => {
  cleanup();
});

const baseProps = {
  title: "T",
  accessRole: "owner" as const,
  actionMenuItems: [],
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
  it("renders standalone actions and grouped export dropdown", () => {
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "share", label: "Share", onSelect: vi.fn() },
          { id: "export-pdf", label: "Export PDF", onSelect: vi.fn() },
          { id: "export-html", label: "Export Single-file HTML", onSelect: vi.fn() },
        ]}
      />,
    );

    expect(screen.getByRole("button", { name: "Share" })).toBeDefined();
    const exportBtn = screen.getByRole("button", { name: /Export/i });
    expect(exportBtn).toBeDefined();
    expect(exportBtn.getAttribute("aria-haspopup")).toBe("menu");

    fireEvent.click(exportBtn);

    expect(screen.getByRole("menuitem", { name: "Export PDF" })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: "Export Single-file HTML" })).toBeDefined();
  });

  it("groups edit actions into one top-bar control", () => {
    const onCode = vi.fn();
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "edit-code", label: "Edit code", onSelect: onCode },
          { id: "edit-with-prompt", label: "Edit with prompt", onSelect: vi.fn() },
        ]}
      />,
    );

    const editBtn = screen.getByRole("button", { name: /Edit/i });
    fireEvent.click(editBtn);
    fireEvent.click(screen.getByRole("menuitem", { name: "Edit code" }));

    expect(onCode).toHaveBeenCalledTimes(1);
  });

  it("groups upload actions into one top-bar control", () => {
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "upload-version", label: "Upload new version", onSelect: vi.fn() },
          { id: "upload-source", label: "Upload source", onSelect: vi.fn() },
        ]}
      />,
    );

    const uploadBtn = screen.getByRole("button", { name: /Upload/i });
    fireEvent.click(uploadBtn);

    expect(screen.getByRole("menuitem", { name: "Upload new version" })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: "Upload source" })).toBeDefined();
  });

  it("keeps Present as standalone action", () => {
    const onPresent = vi.fn();
    wrap(<PresentationDeckHeader {...baseProps} showPresentAction onPresent={onPresent} />);

    const presentBtn = screen.getByRole("button", { name: /Present/i });
    fireEvent.click(presentBtn);

    expect(onPresent).toHaveBeenCalledTimes(1);
  });

  it("does not render hidden actions", () => {
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "visible", label: "Visible", onSelect: vi.fn() },
          { id: "hidden", label: "Hidden", onSelect: vi.fn(), hidden: true },
        ]}
      />,
    );

    expect(screen.getByRole("button", { name: "Visible" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Hidden" })).toBeNull();
  });

  it("does not invoke disabled actions", () => {
    const onDisabled = vi.fn();
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "disabled", label: "Disabled", onSelect: onDisabled, disabled: true },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Disabled" }));

    expect(onDisabled).not.toHaveBeenCalled();
  });

  it("shows Diagram label when titleKind is diagram", () => {
    wrap(<PresentationDeckHeader {...baseProps} titleKind="diagram" />);
    expect(screen.getByText("Diagram")).toBeDefined();
  });
});
