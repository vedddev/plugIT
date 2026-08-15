import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI server mounts the contents of `frontend/` at `/dashboard/`, so
// the build output must use relative asset paths. Vite's default `base: '/'`
// would emit `/assets/...` URLs that resolve to the API origin instead.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: ".",
    emptyOutDir: false,
    rollupOptions: {
      input: {
        index: "index.html",
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/dashboard": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
