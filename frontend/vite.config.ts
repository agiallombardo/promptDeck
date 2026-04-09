import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiTarget = env["VITE_PROXY_TARGET"] ?? "http://127.0.0.1:8005";
  const devPort = Number(env["VITE_DEV_PORT"]) || 5174;

  return {
    plugins: [react(), tailwindcss()],
    build: {
      // Align with tsconfig `target` (Vite 6 default browserslist is older; esbuild cannot downlevel
      // modern dependency syntax like object destructuring to ES2020).
      target: "es2022",
    },
    server: {
      port: devPort,
      host: "127.0.0.1",
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/a": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      include: ["src/**/*.{test,spec}.{ts,tsx}"],
    },
  };
});
