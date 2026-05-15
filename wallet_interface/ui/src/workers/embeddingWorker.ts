import { env, pipeline } from "@xenova/transformers";
// @ts-expect-error Xenova publishes this runtime export without a matching deep module declaration.
import { Tensor } from "@xenova/transformers/src/utils/tensor.js";
import ortWasmAsyncifyMjsUrl from "../../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.mjs?url";
import ortWasmAsyncifyWasmUrl from "../../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.wasm?url";
import { getSafeOnnxWasmThreadCount, installWarningSuppression } from "../lib/warningSuppressionUtils";

env.allowLocalModels = false;
env.useBrowserCache = true;
env.useWasmCache = true;
env.logLevel = "error";
installWarningSuppression();
installXenovaOnnxRuntimeCompatibilityShim();

type EmbeddingRequest =
  | {
      id: string;
      type: "embed";
      data: { text: string; modelName?: string };
    }
  | {
      id: string;
      type: "status";
      data?: Record<string, never>;
    };

interface EmbeddingResponse {
  id: string;
  success: boolean;
  data?: {
    embedding?: number[];
    modelName?: string;
    isInitialized?: boolean;
  };
  error?: string;
}

const DEFAULT_EMBEDDING_MODEL = "Xenova/bge-small-en-v1.5";

let extractor: any = null;
let currentModelName = DEFAULT_EMBEDDING_MODEL;
let initializePromise: Promise<void> | null = null;

async function initialize(modelName = DEFAULT_EMBEDDING_MODEL): Promise<void> {
  if (extractor && currentModelName === modelName) {
    return;
  }

  if (!initializePromise) {
    configureTransformersRuntime();
    initializePromise = pipeline("feature-extraction", modelName, {
      quantized: true,
    }).then((pipe: any) => {
      extractor = pipe;
      currentModelName = modelName;
    });
  }

  try {
    await initializePromise;
  } finally {
    initializePromise = null;
  }
}

async function embed(text: string, modelName?: string): Promise<number[]> {
  await initialize(modelName || DEFAULT_EMBEDDING_MODEL);
  const output = await extractor(text, { pooling: "mean", normalize: true });
  return Array.from(output.data as Float32Array | number[]).map((value) => Number(value));
}

self.onmessage = async (event: MessageEvent<EmbeddingRequest>) => {
  const { id, type, data } = event.data;

  try {
    if (type === "status") {
      postResponse({ id, success: true, data: { modelName: currentModelName, isInitialized: Boolean(extractor) } });
      return;
    }

    if (type === "embed") {
      const embedding = await embed(data.text, data.modelName);
      postResponse({ id, success: true, data: { embedding, modelName: currentModelName, isInitialized: true } });
      return;
    }

    throw new Error(`Unknown embedding worker request: ${type}`);
  } catch (error) {
    postResponse({
      id,
      success: false,
      error: error instanceof Error ? error.message : "Embedding worker failed",
    });
  }
};

function configureTransformersRuntime(): void {
  const backends = env.backends as unknown as {
    onnx?: {
      wasm?: {
        numThreads?: number;
        simd?: boolean;
        wasmPaths?: {
          mjs: string;
          wasm: string;
        };
      };
    };
  };
  if (backends.onnx?.wasm) {
    backends.onnx.wasm.numThreads = getSafeOnnxWasmThreadCount(8);
    backends.onnx.wasm.simd = true;
    backends.onnx.wasm.wasmPaths = {
      mjs: ortWasmAsyncifyMjsUrl,
      wasm: ortWasmAsyncifyWasmUrl,
    };
  }
}

function postResponse(response: EmbeddingResponse): void {
  self.postMessage(response);
}

function installXenovaOnnxRuntimeCompatibilityShim(): void {
  const tensorPrototype = Tensor.prototype as {
    cpuData?: unknown;
    data?: unknown;
    location?: string;
    dataLocation?: string;
  };
  const locationDescriptor = Object.getOwnPropertyDescriptor(tensorPrototype, "location");
  if (!locationDescriptor) {
    Object.defineProperty(tensorPrototype, "location", {
      configurable: true,
      enumerable: false,
      get() {
        return this.dataLocation || "cpu";
      },
    });
  }
  const dataDescriptor = Object.getOwnPropertyDescriptor(tensorPrototype, "data");
  if (!dataDescriptor) {
    Object.defineProperty(tensorPrototype, "data", {
      configurable: true,
      enumerable: false,
      get() {
        return this.cpuData;
      },
      set(value) {
        this.cpuData = value;
      },
    });
  }
}
