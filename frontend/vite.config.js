import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The client router owns the bare product paths (/batch, /audit, /halted,
// /settings), so the API is namespaced under /api and only that prefix is
// proxied. Proxying the bare paths would intercept document requests and the
// SPA route would never render.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
