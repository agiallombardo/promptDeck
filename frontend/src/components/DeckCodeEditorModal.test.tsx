import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DeckCodeEditorModal, type DeckCodeBuffers } from "./DeckCodeEditorModal";

vi.mock("@monaco-editor/react", () => ({
  default: (props: { value?: string; onChange?: (value: string) => void }) => (
    <textarea
      aria-label="code-editor"
      value={props.value ?? ""}
      onChange={(ev) => props.onChange?.(ev.currentTarget.value)}
    />
  ),
}));

function StatefulModal(props: {
  initial: DeckCodeBuffers;
  onSave?: () => void;
  dirty?: boolean;
  onRequestClose?: () => void;
  conflictError?: string | null;
}) {
  const [buffers, setBuffers] = useState(props.initial);
  return (
    <DeckCodeEditorModal
      open
      loading={false}
      saving={false}
      loadError={null}
      conflictError={props.conflictError ?? null}
      dirty={props.dirty ?? false}
      buffers={buffers}
      onBuffersChange={setBuffers}
      onSave={props.onSave ?? (() => undefined)}
      onReload={() => undefined}
      onRequestClose={props.onRequestClose ?? (() => undefined)}
    />
  );
}

describe("DeckCodeEditorModal", () => {
  afterEach(() => {
    cleanup();
  });

  it("edits each tab buffer independently", () => {
    render(
      <StatefulModal
        initial={{
          html: "<html><body><section>One</section></body></html>",
          css: ".a { color: red; }",
          js: "window.a = 1;",
        }}
      />,
    );

    const editor = screen.getByLabelText("code-editor") as HTMLTextAreaElement;
    expect(editor.value).toContain("<section>One</section>");

    fireEvent.click(screen.getByRole("button", { name: "styles.css" }));
    fireEvent.change(screen.getByLabelText("code-editor"), {
      target: { value: ".a { color: green; }" },
    });

    fireEvent.click(screen.getByRole("button", { name: "scripts.js" }));
    fireEvent.change(screen.getByLabelText("code-editor"), {
      target: { value: "window.a = 2;" },
    });

    fireEvent.click(screen.getByRole("button", { name: "index.html" }));
    const htmlEditor = screen.getByLabelText("code-editor") as HTMLTextAreaElement;
    expect(htmlEditor.value).toContain("<section>One</section>");

    fireEvent.click(screen.getByRole("button", { name: "styles.css" }));
    const cssEditor = screen.getByLabelText("code-editor") as HTMLTextAreaElement;
    expect(cssEditor.value).toBe(".a { color: green; }");
  });

  it("runs save on Cmd/Ctrl+S", () => {
    const onSave = vi.fn();
    render(<StatefulModal initial={{ html: "<html></html>", css: "", js: "" }} onSave={onSave} />);
    fireEvent.keyDown(window, { key: "s", ctrlKey: true });
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("shows conflict error and blocks close when discard is canceled", () => {
    const onClose = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(
      <StatefulModal
        initial={{ html: "<html></html>", css: "", js: "" }}
        dirty
        onRequestClose={onClose}
        conflictError="Deck changed since editor opened. Reload code and try saving again."
      />,
    );
    expect(
      screen.getByText("Deck changed since editor opened. Reload code and try saving again."),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
