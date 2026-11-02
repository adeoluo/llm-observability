import { defineConfig } from "vitest/config";

// The Python service serves the built dashboard under /ui and the JSON API under /api.
// In development, Vite serves the UI and proxies /api to the service.
const apiTarget = process.env.LLM_OBS_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  base: "/ui/",
  oxc: {
    jsx: { runtime: "automatic", importSource: "preact" },
  },
  server: {
    proxy: { "/api": apiTarget },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/main.tsx", "src/components/**"],
    },
  },
});
