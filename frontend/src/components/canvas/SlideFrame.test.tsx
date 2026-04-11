import { render } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { SlideFrame } from "./SlideFrame";

describe("SlideFrame", () => {
  it("accepts sandboxed null-origin messages from the iframe window", () => {
    const onManifest = vi.fn();
    const ref = createRef<HTMLIFrameElement>();
    render(<SlideFrame ref={ref} src="http://127.0.0.1:5174/a/deck" onManifest={onManifest} />);
    const frameWindow = ref.current?.contentWindow;
    expect(frameWindow).toBeTruthy();

    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "null",
        source: frameWindow as MessageEventSource,
        data: { type: "manifest", count: 2, titles: ["A", "B"] },
      }),
    );

    expect(onManifest).toHaveBeenCalledWith(2, ["A", "B"]);
  });

  it("ignores messages from other windows", () => {
    const onManifest = vi.fn();
    const ref = createRef<HTMLIFrameElement>();
    render(<SlideFrame ref={ref} src="http://127.0.0.1:5174/a/deck" onManifest={onManifest} />);

    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "http://127.0.0.1:5174",
        data: { type: "manifest", count: 3, titles: ["X", "Y", "Z"] },
      }),
    );

    expect(onManifest).not.toHaveBeenCalled();
  });
});
