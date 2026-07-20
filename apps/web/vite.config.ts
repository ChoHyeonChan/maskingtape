/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { scanProxyPlugin } from "./dev-server/scanProxyPlugin";

export default defineConfig({
  plugins: [react(), scanProxyPlugin()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
  },
});
