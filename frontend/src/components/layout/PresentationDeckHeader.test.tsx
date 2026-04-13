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
  it("renders Actions dropdown and reveals menu items", () => {
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "share", label: "Share", onSelect: vi.fn() },
          { id: "export-pdf", label: "Export PDF", onSelect: vi.fn() },
        ]}
      />,
    );

    const actionsBtn = screen.getByRole("button", { name: /Actions/i });
    expect(actionsBtn).toBeDefined();
    expect(actionsBtn.getAttribute("aria-haspopup")).toBe("menu");
    expect(screen.queryByRole("menu")).toBeNull();

    fireEvent.click(actionsBtn);

    expect(screen.getByRole("menu")).toBeDefined();
    expect(screen.getByRole("menuitem", { name: "Share" })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: "Export PDF" })).toBeDefined();
  });

  it("runs action handlers and closes the menu", () => {
    const onShare = vi.fn();
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[{ id: "share", label: "Share", onSelect: onShare }]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Actions/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Share" }));

    expect(onShare).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("keeps Present as standalone action", () => {
    const onPresent = vi.fn();
    wrap(<PresentationDeckHeader {...baseProps} showPresentAction onPresent={onPresent} />);

    const presentBtn = screen.getByRole("button", { name: /Present/i });
    fireEvent.click(presentBtn);

    expect(onPresent).toHaveBeenCalledTimes(1);
  });

  it("does not render hidden menu items", () => {
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "visible", label: "Visible", onSelect: vi.fn() },
          { id: "hidden", label: "Hidden", onSelect: vi.fn(), hidden: true },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Actions/i }));

    expect(screen.getByRole("menuitem", { name: "Visible" })).toBeDefined();
    expect(screen.queryByRole("menuitem", { name: "Hidden" })).toBeNull();
  });

  it("does not invoke disabled menu items", () => {
    const onDisabled = vi.fn();
    wrap(
      <PresentationDeckHeader
        {...baseProps}
        actionMenuItems={[
          { id: "disabled", label: "Disabled", onSelect: onDisabled, disabled: true },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Actions/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Disabled" }));

    expect(onDisabled).not.toHaveBeenCalled();
  });

  it("shows Diagram label when titleKind is diagram", () => {
    wrap(<PresentationDeckHeader {...baseProps} titleKind="diagram" />);
    expect(screen.getByText("Diagram")).toBeDefined();
  });
});
