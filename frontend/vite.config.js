import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/batch": "http://localhost:8000",
      "/reports": "http://localhost:8000",
      "/audit": "http://localhost:8000",
      "/halted": "http://localhost:8000",
      "/promises": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
