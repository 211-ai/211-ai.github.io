export interface LiquidAudioRuntimePatchUrls {
  audioProcessorUrl: string;
  ortWrapperUrl: string;
  transformersWebModuleUrl: string;
}

export type LiquidAudioProgressPhase =
  | "queued"
  | "loading-runtime"
  | "downloading-model"
  | "warming-up"
  | "ready"
  | "generating"
  | "decoding";

export interface LiquidAudioWorkerProgress {
  phase: LiquidAudioProgressPhase;
  progress: number;
  status: string;
  file?: string;
  modelName?: string;
}

export interface LiquidAudioRunnerPatchDiagnostic {
  key: string;
  label: string;
  present: boolean;
}

const RUNNER_PATCH_PATTERNS = [
  {
    key: "onnxruntimeImport",
    label: "ONNX Runtime import",
    pattern: /import\s+\*\s+as\s+ort\s+from\s+['"]onnxruntime-web['"];?/,
    replacement: (urls: LiquidAudioRuntimePatchUrls) => `import * as ort from ${JSON.stringify(urls.ortWrapperUrl)};`,
  },
  {
    key: "transformersImport",
    label: "Transformers.js import",
    pattern: /import\s+\{\s*AutoTokenizer,\s*env\s*\}\s+from\s+['"]@huggingface\/transformers['"];?/,
    replacement: (urls: LiquidAudioRuntimePatchUrls) =>
      `import { AutoTokenizer, env } from ${JSON.stringify(urls.transformersWebModuleUrl)};`,
  },
  {
    key: "audioProcessorImport",
    label: "audio processor import",
    pattern:
      /import\s+\{\s*loadMelConfig,\s*computeMelSpectrogram,\s*loadAudioFile\s*\}\s+from\s+['"]\.\/audio-processor\.js['"];?/,
    replacement: (urls: LiquidAudioRuntimePatchUrls) =>
      `import { loadMelConfig, computeMelSpectrogram, loadAudioFile } from ${JSON.stringify(urls.audioProcessorUrl)};`,
  },
  {
    key: "loadOptions",
    label: "AudioModel.load options destructuring",
    pattern:
      /const\s+\{\s*progressCallback,\s*device\s*=\s*['"]webgpu['"],\s*quantization\s*=\s*null\s*\}\s*=\s*options;?/,
    replacement: () =>
      "const { progressCallback, device = 'webgpu', quantization = null, loadAudioEncoder = true } = options;",
  },
  {
    key: "audioEncoderLoad",
    label: "audio encoder session load",
    pattern:
      /this\.audioEncoderSession\s*=\s*await\s+loadOnnxWithExternalData\(['"]audio_encoder['"],\s*50,\s*quantConfig\.audioEncoder\);?/,
    replacement: () =>
      "if (loadAudioEncoder) { this.audioEncoderSession = await loadOnnxWithExternalData('audio_encoder', 50, quantConfig.audioEncoder); }",
  },
] as const;

export function getLiquidAudioRunnerPatchDiagnostics(source: string): LiquidAudioRunnerPatchDiagnostic[] {
  return RUNNER_PATCH_PATTERNS.map((rule) => ({
    key: rule.key,
    label: rule.label,
    present: rule.pattern.test(source),
  }));
}

export function assertLiquidAudioRunnerPatchable(source: string): void {
  const missing = getLiquidAudioRunnerPatchDiagnostics(source).filter((diagnostic) => !diagnostic.present);
  if (!missing.length) return;
  throw new Error(
    `LiquidAI audio runner patch failed; missing ${missing.map((diagnostic) => diagnostic.label).join(", ")}. ` +
      "The upstream LiquidAI demo runner may have changed.",
  );
}

export function patchAudioModelSource(source: string, urls: LiquidAudioRuntimePatchUrls): string {
  assertLiquidAudioRunnerPatchable(source);
  const patched = RUNNER_PATCH_PATTERNS.reduce(
    (current, rule) => current.replace(rule.pattern, rule.replacement(urls)),
    source,
  );

  return `// Runtime-patched from LiquidAI/LFM2.5-Audio-1.5B-transformers-js.
${patched}`;
}

export function formatLiquidAudioLoadProgress(
  progress: { status: string; progress: number; file?: string },
  modelName: string,
): LiquidAudioWorkerProgress {
  const rawProgress = Number.isFinite(progress.progress) ? progress.progress : 0;
  const normalizedProgress = rawProgress <= 1 ? rawProgress * 100 : rawProgress;
  const scaledProgress = 15 + normalizedProgress * 0.7;
  const fileDetail = progress.file ? ` ${progress.file}` : "";
  return {
    phase: "downloading-model",
    progress: clampAudioProgress(scaledProgress),
    status: `Downloading audio model${fileDetail}.`,
    file: progress.file,
    modelName,
  };
}

export function clampAudioProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}
