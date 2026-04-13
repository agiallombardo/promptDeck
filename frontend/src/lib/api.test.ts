import { describe, expect, it } from "vitest";
import { iframeSrcForDev } from "./api";

describe("iframeSrcForDev", () => {
  it("rewrites signed /a absolute urls to same-origin relative paths", () => {
    const src =
      "http://127.0.0.1:5174/a/3fdce11d-2420-4ca1-982c-b2bce71de1a2/index.html?exp=1776108083&sig=abc";
    expect(iframeSrcForDev(src)).toBe(
      "/a/3fdce11d-2420-4ca1-982c-b2bce71de1a2/index.html?exp=1776108083&sig=abc",
    );
  });

  it("keeps non-asset urls unchanged", () => {
    const src = "http://127.0.0.1:5174/somewhere/index.html?x=1";
    expect(iframeSrcForDev(src)).toBe(src);
  });
});
