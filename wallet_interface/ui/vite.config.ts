import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
  build: {
    rollupOptions: {
      input: {
        app: fileURLToPath(new URL("./index.html", import.meta.url)),
        serviceWorker: fileURLToPath(new URL("./src/pwa/serviceWorker.ts", import.meta.url))
      },
      output: {
        entryFileNames: (chunkInfo) =>
          chunkInfo.name === "serviceWorker" ? "serviceWorker.js" : "assets/[name]-[hash].js"
      }
    }
  },
  optimizeDeps: {
    exclude: ["@huggingface/transformers", "@xenova/transformers", "onnxruntime-web"]
  }
});
