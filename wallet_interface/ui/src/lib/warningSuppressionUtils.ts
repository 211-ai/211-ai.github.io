export interface WarningSuppressionOptions {
  patterns?: readonly RegExp[];
  consoleObject?: Pick<Console, "warn">;
}

export interface WarningSuppressionHandle {
  restore: () => void;
}

const DEFAULT_SUPPRESSED_WARNING_PATTERNS: readonly RegExp[] = [
  /env\.wasm\.numThreads is set to \d+.*crossOriginIsolated mode/i,
  /WebAssembly multi-threading is not supported.*falling back to single-threading/i,
  /removing requested execution provider "webgpu" from session options because it is not available/i,
  /WebGPU not available on this browser/i,
  /Failed to get GPU adapter.*enable-unsafe-webgpu/i,
  /Property "env\.wasm\.simd" is set to unknown value/i,
];

const suppressionStateKey = Symbol.for("abby.warningSuppression.consoleWarn");

interface WarningSuppressionState {
  originalWarn: Console["warn"];
  patterns: RegExp[];
  refCount: number;
}

type ConsoleWithSuppressionState = Pick<Console, "warn"> & {
  [suppressionStateKey]?: WarningSuppressionState;
};

export function installWarningSuppression(options: WarningSuppressionOptions = {}): WarningSuppressionHandle {
  const consoleObject = (options.consoleObject || console) as ConsoleWithSuppressionState;
  const patterns = [...DEFAULT_SUPPRESSED_WARNING_PATTERNS, ...(options.patterns || [])];
  const existingState = consoleObject[suppressionStateKey];

  if (existingState) {
    existingState.patterns.push(...patterns);
    existingState.refCount += 1;
    return {
      restore: () => restoreWarningSuppression(consoleObject),
    };
  }

  const originalWarn = consoleObject.warn.bind(consoleObject);
  consoleObject[suppressionStateKey] = {
    originalWarn,
    patterns,
    refCount: 1,
  };

  consoleObject.warn = (...args: unknown[]) => {
    const state = consoleObject[suppressionStateKey];
    if (state && shouldSuppressWarning(args, state.patterns)) {
      return;
    }
    originalWarn(...args);
  };

  return {
    restore: () => restoreWarningSuppression(consoleObject),
  };
}

export function shouldSuppressWarning(args: readonly unknown[], patterns = DEFAULT_SUPPRESSED_WARNING_PATTERNS): boolean {
  const message = warningArgsToString(args);
  return patterns.some((pattern) => pattern.test(message));
}

export function getSafeOnnxWasmThreadCount(maxThreads = 8): number {
  if (!supportsSharedWasmThreads()) {
    return 1;
  }
  const hardwareConcurrency = typeof navigator !== "undefined" ? navigator.hardwareConcurrency || 1 : 1;
  return Math.max(1, Math.min(hardwareConcurrency, maxThreads));
}

function restoreWarningSuppression(consoleObject: ConsoleWithSuppressionState): void {
  const state = consoleObject[suppressionStateKey];
  if (!state) {
    return;
  }

  state.refCount -= 1;
  if (state.refCount > 0) {
    return;
  }

  consoleObject.warn = state.originalWarn;
  delete consoleObject[suppressionStateKey];
}

function warningArgsToString(args: readonly unknown[]): string {
  return args.map(warningArgToString).join(" ");
}

function warningArgToString(arg: unknown): string {
  if (typeof arg === "string") {
    return arg;
  }
  if (arg instanceof Error) {
    return `${arg.name}: ${arg.message}`;
  }
  try {
    return JSON.stringify(arg);
  } catch {
    return String(arg);
  }
}

function supportsSharedWasmThreads(): boolean {
  return (
    typeof SharedArrayBuffer !== "undefined" &&
    Boolean((globalThis as { crossOriginIsolated?: boolean }).crossOriginIsolated)
  );
}
