import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const useNativeWatcher = ["1", "true", "yes"].includes((process.env.VITE_DEV_NATIVE_WATCH || "").toLowerCase());

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin"
    },
    watch: {
      ignored: [
        "**/.git/**",
        "**/artifacts/**",
        "**/dist/**",
        "**/test-results/**",
        "**/public/assets/**",
        "**/public/corpus/**"
      ],
      usePolling: !useNativeWatcher
    }
  },
  worker: {
    format: "es"
  },
  optimizeDeps: {
    exclude: ["@xenova/transformers", "onnxruntime-web"]
  }
});
