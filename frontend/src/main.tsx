import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { BootstrapAuth } from "./components/BootstrapAuth.tsx";
import { ToastViewport } from "./components/ToastViewport.tsx";
import { queryClient } from "./lib/queryClient.ts";
import { AppRouter } from "./router.tsx";
import "./styles/tailwind.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <BootstrapAuth>
          <AppRouter />
          <ToastViewport />
        </BootstrapAuth>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
