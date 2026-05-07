import { readFile } from "node:fs/promises";
import { defineConfig, transformWithEsbuild, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function portalServiceWorkerPlugin(): Plugin {
  const serviceWorkerSourceUrl = new URL("./src/pwa/serviceWorker.ts", import.meta.url);

  async function buildServiceWorker(): Promise<string> {
    const source = await readFile(serviceWorkerSourceUrl, "utf8");
    const result = await transformWithEsbuild(source, serviceWorkerSourceUrl.pathname, {
      format: "esm",
      loader: "ts",
      target: "es2020"
    });
    return result.code;
  }

  return {
    name: "portal-service-worker",
    configureServer(server) {
      server.middlewares.use("/serviceWorker.js", async (request, response, next) => {
        if (request.method !== "GET" && request.method !== "HEAD") {
          next();
          return;
        }

        try {
          const code = await buildServiceWorker();
          response.statusCode = 200;
          response.setHeader("Cache-Control", "no-store");
          response.setHeader("Content-Type", "text/javascript; charset=utf-8");
          response.end(request.method === "HEAD" ? "" : code);
        } catch (error) {
          next(error);
        }
      });
    },
    async generateBundle() {
      this.emitFile({
        fileName: "serviceWorker.js",
        source: await buildServiceWorker(),
        type: "asset"
      });
    }
  };
}

export default defineConfig({
  base: "./",
  plugins: [react(), portalServiceWorkerPlugin()],
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
  }
});
