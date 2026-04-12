import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../lib/api";
import { useAuthStore } from "../stores/auth";
import LoginPage from "./LoginPage";

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, apiAuthConfig: vi.fn() };
});

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    vi.mocked(api.apiAuthConfig).mockReset();
  });

  it("shows local sign-in when auth config fails and allows retry", async () => {
    vi.mocked(api.apiAuthConfig)
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce({
        entra_enabled: false,
        entra_login_url: null,
        local_password_auth_enabled: true,
      });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/network down/i)).toBeTruthy();
    });
    expect(screen.getByRole("button", { name: /local account/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /retry loading sign-in options/i }));

    await waitFor(() => {
      expect(screen.queryByText(/network down/i)).toBeNull();
    });
  });
});
