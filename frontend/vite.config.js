import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/register": "http://127.0.0.1:8000",
      "/login": "http://127.0.0.1:8000",
      "/transaction": "http://127.0.0.1:8000",
      "/dashboard": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/account": "http://127.0.0.1:8000",
    },
  },
});
