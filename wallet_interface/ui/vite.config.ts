import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin"
    }
  },
  worker: {
    format: "es"
  },
  optimizeDeps: {
    exclude: ["@xenova/transformers", "onnxruntime-web"]
  },
  build: {
    rollupOptions: {
      input: {
        app: fileURLToPath(new URL("./index.html", import.meta.url)),
        serviceWorker: fileURLToPath(new URL("./src/pwa/serviceWorker.ts", import.meta.url))
      },
      output: {
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: (chunkInfo) =>
          chunkInfo.name === "serviceWorker" ? "service-worker.js" : "assets/[name]-[hash].js"
      }
    }
  }
});
