/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173 },
  // Never inline assets as data: URIs; the page CSP allows fonts and images from 'self' only.
  build: { assetsInlineLimit: 0 },
  test: { environment: "jsdom", setupFiles: ["tests/unit/setup.ts"], include: ["tests/unit/**/*.test.tsx"] },
});
