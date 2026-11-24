import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En développement, /api est relayé vers l'API Python (uvicorn sur le port 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
