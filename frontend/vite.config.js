import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, `npm run dev` forwards /api calls to the Django backend,
// so the browser only ever talks to one origin (no CORS setup needed).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_URL || "http://localhost:8000",
    },
  },
});
