import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import HomeRedirect from "./App";
import { useAuthStore } from "./stores/auth";

describe("HomeRedirect", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });

  it("redirects unauthenticated visitors to login", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="/files" element={<div>Files page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText("Login page")).toBeTruthy());
  });

  it("redirects authenticated users to files", async () => {
    useAuthStore.getState().setSession("tok", {
      id: "00000000-0000-0000-0000-000000000001",
      email: "e@example.com",
      display_name: null,
      role: "user",
      auth_provider: "local",
    });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="/files" element={<div>Files page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText("Files page")).toBeTruthy());
  });
});
