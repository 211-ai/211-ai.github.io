export interface BackendCapabilities {
  webnn: boolean;
  webgpu: boolean;
  wasm: boolean;
  webgl: boolean;
  simd: boolean;
  threads: boolean;
}

export interface BackendDetectionResult {
  capabilities: BackendCapabilities;
  recommendedBackend: "webgpu" | "webnn" | "wasm" | "javascript";
  deviceInfo: {
    userAgent: string;
    hardwareConcurrency: number;
    deviceMemory?: number;
    crossOriginIsolated: boolean;
  };
}

let detectionPromise: Promise<BackendDetectionResult> | null = null;

export async function detectBrowserMlBackends(): Promise<BackendDetectionResult> {
  if (!detectionPromise) {
    detectionPromise = detectBackends();
  }
  return detectionPromise;
}

async function detectBackends(): Promise<BackendDetectionResult> {
  const capabilities: BackendCapabilities = {
    webnn: detectWebNN(),
    webgpu: await detectWebGPU(),
    wasm: detectWasm(),
    webgl: detectWebGL(),
    simd: detectWasmSimd(),
    threads: detectWasmThreads(),
  };

  return {
    capabilities,
    recommendedBackend: recommendBackend(capabilities),
    deviceInfo: {
      userAgent: navigator.userAgent,
      hardwareConcurrency: navigator.hardwareConcurrency || 1,
      deviceMemory: (navigator as Navigator & { deviceMemory?: number }).deviceMemory,
      crossOriginIsolated: Boolean(globalThis.crossOriginIsolated),
    },
  };
}

function detectWebNN(): boolean {
  return typeof navigator !== "undefined" && "ml" in navigator;
}

async function detectWebGPU(): Promise<boolean> {
  try {
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter: (options?: unknown) => Promise<any> } }).gpu;
    if (!gpu?.requestAdapter) {
      return false;
    }
    const adapter = await gpu.requestAdapter({ powerPreference: "high-performance" });
    if (!adapter) {
      return false;
    }
    const device = await adapter.requestDevice();
    device.destroy();
    return true;
  } catch {
    return false;
  }
}

function detectWasm(): boolean {
  return typeof WebAssembly === "object" && typeof WebAssembly.instantiate === "function";
}

function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function detectWasmSimd(): boolean {
  try {
    const simdModule = new Uint8Array([
      0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b,
    ]);
    return WebAssembly.validate(simdModule);
  } catch {
    return false;
  }
}

function detectWasmThreads(): boolean {
  try {
    return typeof SharedArrayBuffer !== "undefined" && typeof Worker !== "undefined" && globalThis.crossOriginIsolated;
  } catch {
    return false;
  }
}

function recommendBackend(capabilities: BackendCapabilities): BackendDetectionResult["recommendedBackend"] {
  if (capabilities.webgpu) {
    return "webgpu";
  }
  if (capabilities.webnn) {
    return "webnn";
  }
  if (capabilities.wasm) {
    return "wasm";
  }
  return "javascript";
}
