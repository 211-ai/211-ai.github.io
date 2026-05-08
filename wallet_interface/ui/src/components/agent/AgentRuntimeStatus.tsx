import { useCallback, useEffect, useMemo, useState } from "react";
import { Cpu, Gauge, RefreshCw, Zap } from "lucide-react";

type ClientLlmDevice = "wasm" | "webgpu" | "auto";

interface ClientLlmRuntimeCapabilities {
  webGPU: boolean;
  webGPUError?: string;
  webGPUAdapter?: {
    vendor?: string;
    architecture?: string;
    device?: string;
    description?: string;
  };
  simd: boolean;
  wasmThreads: boolean;
  crossOriginIsolated: boolean;
  sharedArrayBuffer: boolean;
}

interface ClientLlmRuntimeStatus {
  hasWorker: boolean;
  isInitialized: boolean;
  isInitializing: boolean;
  currentModel: string;
  currentDevice: ClientLlmDevice;
  capabilities: ClientLlmRuntimeCapabilities;
  error?: string;
}

const unavailableCapabilities: ClientLlmRuntimeCapabilities = {
  webGPU: false,
  simd: false,
  wasmThreads: false,
  crossOriginIsolated: Boolean((globalThis as { crossOriginIsolated?: boolean }).crossOriginIsolated),
  sharedArrayBuffer: typeof SharedArrayBuffer !== "undefined",
};

const initialStatus: ClientLlmRuntimeStatus = {
  hasWorker: false,
  isInitialized: false,
  isInitializing: false,
  currentModel: "",
  currentDevice: "wasm",
  capabilities: unavailableCapabilities,
};

export function AgentRuntimeStatus({ open }: { open: boolean }) {
  const [status, setStatus] = useState<ClientLlmRuntimeStatus>(initialStatus);
  const [loading, setLoading] = useState(false);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    try {
      const { clientLLMWorkerService } = await import("../../lib/clientLLMWorkerService");
      const [workerCapabilities, serviceStatus] = await Promise.all([
        clientLLMWorkerService.getCapabilities(),
        Promise.resolve(clientLLMWorkerService.getStatus()),
      ]);
      setStatus({
        ...serviceStatus,
        currentDevice: workerCapabilities.device || serviceStatus.currentDevice,
        currentModel: workerCapabilities.modelName || serviceStatus.currentModel,
        isInitialized: Boolean(workerCapabilities.isInitialized ?? serviceStatus.isInitialized),
        capabilities: workerCapabilities.capabilities || serviceStatus.capabilities,
      });
    } catch (error) {
      setStatus({
        ...initialStatus,
        error: error instanceof Error ? error.message : "Assistant runtime unavailable",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    void refreshStatus();
  }, [open, refreshStatus]);

  const summary = useMemo(() => summarizeRuntime(status), [status]);
  const Icon = summary.backend === "webgpu" ? Zap : summary.backend === "wasm" ? Cpu : Gauge;

  return (
    <section
      aria-label="Assistant runtime status"
      className={`agent-runtime-status agent-runtime-status-${summary.tone}`}
    >
      <span aria-hidden="true" className="agent-runtime-icon">
        <Icon size={16} />
      </span>
      <div className="agent-runtime-summary">
        <small>{summary.label}</small>
        <span title={summary.detail}>{summary.detail}</span>
      </div>
      <dl className="agent-runtime-details" aria-label="Local inference details">
        <div>
          <dt>Model</dt>
          <dd title={status.currentModel}>{shortModelName(status.currentModel)}</dd>
        </div>
        <div>
          <dt>Threads</dt>
          <dd>{status.capabilities.wasmThreads ? "on" : "off"}</dd>
        </div>
        <div>
          <dt>Isolation</dt>
          <dd>{status.capabilities.crossOriginIsolated ? "on" : "off"}</dd>
        </div>
      </dl>
      <button
        aria-label="Refresh assistant runtime status"
        className="agent-runtime-refresh"
        disabled={loading}
        onClick={() => void refreshStatus()}
        type="button"
      >
        <RefreshCw aria-hidden="true" className={loading ? "loading-icon" : undefined} size={15} />
      </button>
    </section>
  );
}

function summarizeRuntime(status: ClientLlmRuntimeStatus): {
  backend: "webgpu" | "wasm" | "unknown";
  detail: string;
  label: string;
  tone: "success" | "warning" | "danger" | "neutral";
} {
  if (status.error) {
    return {
      backend: "unknown",
      detail: status.error,
      label: "Runtime unavailable",
      tone: "danger",
    };
  }
  if (status.currentDevice === "webgpu") {
    return {
      backend: "webgpu",
      detail: formatAdapter(status.capabilities.webGPUAdapter) || "WebGPU active",
      label: "WebGPU",
      tone: "success",
    };
  }
  if (status.capabilities.webGPU) {
    return {
      backend: "wasm",
      detail: status.isInitialized ? "WASM active" : "WebGPU available before model load",
      label: status.isInitialized ? "WASM" : "WebGPU ready",
      tone: status.isInitialized ? "warning" : "success",
    };
  }
  return {
    backend: "wasm",
    detail: status.capabilities.webGPUError || "WebGPU unavailable; WASM fallback",
    label: "WASM fallback",
    tone: status.capabilities.webGPUError ? "warning" : "neutral",
  };
}

function shortModelName(modelName: string): string {
  if (!modelName) {
    return "not loaded";
  }
  const parts = modelName.split("/");
  return (parts[parts.length - 1] || modelName).replace(/-Instruct$/, "");
}

function formatAdapter(adapter: ClientLlmRuntimeCapabilities["webGPUAdapter"]): string {
  if (!adapter) {
    return "";
  }
  return [adapter.vendor, adapter.device || adapter.description, adapter.architecture].filter(Boolean).join(" ");
}
