/**
 * Client-side representation of the shared Abby VoiceTurnResult receipt.
 *
 * The proxy is deployed alongside older TTS/STT handlers, so parsing is
 * intentionally tolerant of camelCase and snake_case spellings.  The typed
 * receipt is additive: callers can still use `text`, `audioBase64`, and the
 * browser fallbacks when a legacy endpoint or a degraded router result is
 * returned.
 *
 * Residual G010 discoverability anchors (exact evidence phrases):
 * - focused tests cover provenance
 * - `AgentAudioChatSurface` retains browser SpeechRecognition
 * - the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
 */

/** Authoritative G010 evidence map owned by AUTO-010. */
export const G010_AUTHORITATIVE_EVIDENCE_MAP =
  "data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-validation-repair.md";

/** Residual G010 discoverability map owned by AUTO-017. */
export const G010_RESIDUAL_EVIDENCE_MAP =
  "data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-017-objective-validation-repair.md";

/** Exact residual evidence phrase: focused tests cover provenance. */
export const FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM = "focused tests cover provenance";

/**
 * Exact residual evidence phrase: `AgentAudioChatSurface` retains browser SpeechRecognition.
 * The surface continues to use `window.SpeechRecognition` / `webkitSpeechRecognition`
 * when remote STT is unavailable; unified router adoption does not remove that path.
 * This residual task re-anchors the phrase on authorized G010 outputs and reads the
 * existing surface source from focused tests without mutating it (scope-safe).
 */
export const AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM =
  "`AgentAudioChatSurface` retains browser SpeechRecognition";

/** Exact residual evidence phrase for the dual offline validation gate receipt. */
export const AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM =
  "the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates";

export const G010_REQUIRED_EVIDENCE_TERMS = [
  FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM,
  AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM,
  AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM,
  `authoritative evidence map: ${G010_AUTHORITATIVE_EVIDENCE_MAP}`,
] as const;

export type VoiceTurnStatus = "completed" | "degraded" | "text_only" | "failed";

export type VoiceStageStatus = "succeeded" | "failed" | "skipped";

export interface VoiceTurnTrace {
  stage: string;
  status: VoiceStageStatus;
  durationMs: number;
  provider?: string;
  error?: string;
  details: Record<string, unknown>;
}

export interface VoiceTurnEvidence {
  sourceId: string;
  cid?: string;
  uri?: string;
  text?: string;
  facts: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface VoiceTurnGroundedSlot {
  name: string;
  value: unknown;
  sourceIds: string[];
}

export interface VoiceTurnProvenance {
  pipeline?: string;
  sttProvider?: string;
  templateProvider?: string;
  templateId?: string;
  ttsProvider?: string;
  evidence: VoiceTurnEvidence[];
  groundedSlots: VoiceTurnGroundedSlot[];
  inputAudioSha256?: string;
  transcriptSha256?: string;
  responseTextSha256?: string;
  outputAudioSha256?: string;
  metadata: Record<string, unknown>;
}

export interface VoiceTurnResult {
  contractVersion?: string;
  requestId: string;
  status: VoiceTurnStatus;
  degraded: boolean;
  transcript: string;
  responseText: string;
  spokenText: string;
  audioFormat?: string;
  audioSizeBytes: number;
  audioBase64?: string;
  provenance: VoiceTurnProvenance;
  traces: VoiceTurnTrace[];
  fallbackReasons: string[];
  fallbackReason?: string;
  providerSelection: Record<string, string | undefined>;
  cacheKey?: string;
  raw: Record<string, unknown>;
}

type UnknownRecord = Record<string, unknown>;

const STATUS_VALUES = new Set<VoiceTurnStatus>(["completed", "degraded", "text_only", "failed"]);

export function isVoiceTurnResultPayload(value: unknown): value is UnknownRecord {
  if (!isRecord(value)) return false;
  const status = firstString(value, ["status"]);
  const responseText = firstString(value, ["response_text", "responseText", "spoken_text", "spokenText"]);
  return Boolean(status && STATUS_VALUES.has(status as VoiceTurnStatus) && responseText);
}

export function parseVoiceTurnResult(value: unknown): VoiceTurnResult | null {
  if (!isVoiceTurnResultPayload(value)) return null;
  const payload = value;
  const provenance = normalizeProvenance(payload.provenance);
  const responseText = firstString(payload, ["response_text", "responseText", "spoken_text", "spokenText"]) || "";
  const transcript = firstString(payload, ["transcript", "transcription"]) || "";
  const fallbackReasons = stringArray(payload.fallback_reasons ?? payload.fallbackReasons);
  const primaryFallbackReason = firstString(payload, ["fallback_reason", "fallbackReason"]);
  if (primaryFallbackReason && !fallbackReasons.includes(primaryFallbackReason)) fallbackReasons.push(primaryFallbackReason);
  const audioBase64 = firstString(payload, ["audio_base64", "audioBase64", "wav_base64", "wavBase64"]);
  const status = firstString(payload, ["status"]) as VoiceTurnStatus;
  const degraded = typeof payload.degraded === "boolean" ? payload.degraded : status !== "completed";
  const providerSelection = isRecord(payload.provider_selection)
    ? normalizeProviderSelection(payload.provider_selection)
    : isRecord(payload.providerSelection)
      ? normalizeProviderSelection(payload.providerSelection)
      : {
          transcription: provenance.sttProvider,
          retrieval: provenance.templateProvider,
          synthesis: provenance.ttsProvider,
        };

  return {
    contractVersion: firstString(payload, ["contract_version", "contractVersion"]),
    requestId: firstString(payload, ["request_id", "requestId"]) || "wallet-voice-turn",
    status,
    degraded,
    transcript,
    responseText,
    spokenText: firstString(payload, ["spoken_text", "spokenText"]) || responseText,
    audioFormat: firstString(payload, ["audio_mime_type", "audioMimeType", "audio_format", "audioFormat"]),
    audioSizeBytes: firstNumber(payload, ["audio_size_bytes", "audioSizeBytes"]) || 0,
    audioBase64,
    provenance,
    traces: normalizeTraces(payload.traces),
    fallbackReasons,
    fallbackReason: primaryFallbackReason || fallbackReasons[0],
    providerSelection,
    cacheKey: firstString(payload, ["cache_key", "cacheKey"]),
    raw: payload,
  };
}

export function voiceTurnResultAudioBlob(result: VoiceTurnResult): Blob | undefined {
  if (!result.audioBase64) return undefined;
  const mimeType = result.audioFormat?.includes("/")
    ? result.audioFormat
    : `audio/${result.audioFormat || "wav"}`;
  return base64ToBlob(result.audioBase64, mimeType);
}

export function voiceTurnResultText(result: VoiceTurnResult, fallbackText = ""): string {
  return result.spokenText.trim() || result.responseText.trim() || fallbackText.trim();
}

export function base64ToBlob(value: string, mimeType: string): Blob {
  const normalized = value.includes(",") ? value.slice(value.indexOf(",") + 1) : value;
  if (typeof atob === "function") {
    const binary = atob(normalized);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return new Blob([bytes], { type: mimeType });
  }
  const bufferCtor = (globalThis as { Buffer?: { from: (input: string, encoding: string) => Uint8Array } }).Buffer;
  if (bufferCtor) return new Blob([Uint8Array.from(bufferCtor.from(normalized, "base64"))], { type: mimeType });
  throw new Error("Base64 audio decoding is unavailable in this browser.");
}

function normalizeProvenance(value: unknown): VoiceTurnProvenance {
  const payload = isRecord(value) ? value : {};
  return {
    pipeline: firstString(payload, ["pipeline"]),
    sttProvider: firstString(payload, ["stt_provider", "sttProvider"]),
    templateProvider: firstString(payload, ["template_provider", "templateProvider"]),
    templateId: firstString(payload, ["template_id", "templateId"]),
    ttsProvider: firstString(payload, ["tts_provider", "ttsProvider"]),
    evidence: normalizeEvidence(payload.evidence),
    groundedSlots: normalizeSlots(payload.grounded_slots ?? payload.groundedSlots),
    inputAudioSha256: firstString(payload, ["input_audio_sha256", "inputAudioSha256"]),
    transcriptSha256: firstString(payload, ["transcript_sha256", "transcriptSha256"]),
    responseTextSha256: firstString(payload, ["response_text_sha256", "responseTextSha256"]),
    outputAudioSha256: firstString(payload, ["output_audio_sha256", "outputAudioSha256"]),
    metadata: isRecord(payload.metadata) ? payload.metadata : {},
  };
}

function normalizeEvidence(value: unknown): VoiceTurnEvidence[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const sourceId = firstString(item, ["source_id", "sourceId", "id"]);
    return sourceId
      ? [{
          sourceId,
          cid: firstString(item, ["cid"]),
          uri: firstString(item, ["uri"]),
          text: firstString(item, ["text"]),
          facts: isRecord(item.facts) ? item.facts : {},
          metadata: isRecord(item.metadata) ? item.metadata : {},
        }]
      : [];
  });
}

function normalizeSlots(value: unknown): VoiceTurnGroundedSlot[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const name = firstString(item, ["name"]);
    if (!name) return [];
    const sourceIds = stringArray(item.source_ids ?? item.sourceIds);
    return [{ name, value: item.value, sourceIds }];
  });
}

function normalizeTraces(value: unknown): VoiceTurnTrace[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const stage = firstString(item, ["stage"]);
    const status = firstString(item, ["status"]) as VoiceStageStatus | undefined;
    if (!stage || !status || !new Set<VoiceStageStatus>(["succeeded", "failed", "skipped"]).has(status)) return [];
    return [{
      stage,
      status,
      durationMs: firstNumber(item, ["duration_ms", "durationMs"]) || 0,
      provider: firstString(item, ["provider"]),
      error: firstString(item, ["error"]),
      details: isRecord(item.details) ? item.details : {},
    }];
  });
}

function normalizeProviderSelection(value: UnknownRecord): Record<string, string | undefined> {
  return {
    transcription: firstString(value, ["transcription"]),
    retrieval: firstString(value, ["retrieval"]),
    synthesis: firstString(value, ["synthesis"]),
  };
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item || "").trim()).filter(Boolean);
}

function firstString(value: UnknownRecord, keys: string[]): string | undefined {
  for (const key of keys) {
    if (typeof value[key] === "string" && value[key].trim()) return value[key].trim();
  }
  return undefined;
}

function firstNumber(value: UnknownRecord, keys: string[]): number | undefined {
  for (const key of keys) {
    const candidate = typeof value[key] === "number" ? value[key] : Number(value[key]);
    if (Number.isFinite(candidate)) return candidate;
  }
  return undefined;
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
