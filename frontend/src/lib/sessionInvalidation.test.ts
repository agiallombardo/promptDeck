import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "./queryClient";
import { handleApiUnauthorized } from "./sessionInvalidation";
import { useAuthStore } from "../stores/auth";

describe("handleApiUnauthorized", () => {
  beforeEach(() => {
    useAuthStore.getState().setSession("test-token", {
      id: "u1",
      email: "a@b.c",
      display_name: null,
      role: "user",
      auth_provider: "local",
    });
    vi.spyOn(queryClient, "clear").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("clears auth and query cache for API paths", () => {
    handleApiUnauthorized("/api/v1/presentations");
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(queryClient.clear).toHaveBeenCalled();
  });

  it("does not clear session for login attempts", () => {
    handleApiUnauthorized("/api/v1/auth/login");
    expect(useAuthStore.getState().accessToken).toBe("test-token");
    expect(queryClient.clear).not.toHaveBeenCalled();
  });

  it("does not clear session for auth config", () => {
    handleApiUnauthorized("/api/v1/auth/config");
    expect(useAuthStore.getState().accessToken).toBe("test-token");
    expect(queryClient.clear).not.toHaveBeenCalled();
  });

  it("does not clear session for share link exchange", () => {
    handleApiUnauthorized("/api/v1/share-links/exchange");
    expect(useAuthStore.getState().accessToken).toBe("test-token");
    expect(queryClient.clear).not.toHaveBeenCalled();
  });
});
