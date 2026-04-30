import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/static/react/",
  plugins: [react()],
  build: {
    outDir: "static/react",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith(".css")) {
            return "app.css";
          }
          return "assets/[name]-[hash][extname]";
        },
      },
    },
  },
});
