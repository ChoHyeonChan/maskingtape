/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { scanProxyPlugin } from "./dev-server/scanProxyPlugin";

export default defineConfig({
  plugins: [react(), scanProxyPlugin()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
  },
});
