import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

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
  build: {
    rollupOptions: {
      input: {
        app: resolve(rootDir, "index.html"),
        serviceWorker: resolve(rootDir, "src/pwa/serviceWorker.ts")
      },
      output: {
        entryFileNames: (chunkInfo) =>
          chunkInfo.name === "serviceWorker" ? "serviceWorker.js" : "assets/[name]-[hash].js"
      }
    }
  },
  worker: {
    format: "es"
  },
  optimizeDeps: {
    exclude: ["@xenova/transformers", "onnxruntime-web"]
  }
});
