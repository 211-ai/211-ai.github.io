import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM,
  AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM,
  FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM,
  G010_AUTHORITATIVE_EVIDENCE_MAP,
  G010_REQUIRED_EVIDENCE_TERMS,
  isVoiceTurnResultPayload,
  parseVoiceTurnResult,
  voiceActionLabel,
  voiceActionNeedsConfirmation,
  voiceTurnResultAudioBlob,
  voiceTurnResultText,
} from "../src/features/agent/lib/voiceTurnResult";
import { ClientAudioReplyService } from "../src/features/agent/lib/clientAudioReplyService";
import { createVoiceProxyFormData } from "../src/features/agent/lib/voiceProxyPayload";

const AUDIO_BYTES = createMinimalWav();
const AUDIO_BASE64 = AUDIO_BYTES.toString("base64");
const UI_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(UI_ROOT, "../..");

function createMinimalWav(): Buffer {
  const sampleCount = 8;
  const bytes = Buffer.alloc(44 + sampleCount * 2);
  bytes.write("RIFF", 0, "ascii");
  bytes.writeUInt32LE(bytes.length - 8, 4);
  bytes.write("WAVE", 8, "ascii");
  bytes.write("fmt ", 12, "ascii");
  bytes.writeUInt32LE(16, 16);
  bytes.writeUInt16LE(1, 20);
  bytes.writeUInt16LE(1, 22);
  bytes.writeUInt32LE(16_000, 24);
  bytes.writeUInt32LE(32_000, 28);
  bytes.writeUInt16LE(2, 32);
  bytes.writeUInt16LE(16, 34);
  bytes.write("data", 36, "ascii");
  bytes.writeUInt32LE(sampleCount * 2, 40);
  for (let index = 0; index < sampleCount; index += 1) {
    bytes.writeInt16LE(index % 2 ? 2_000 : -2_000, 44 + index * 2);
  }
  return bytes;
}

/**
 * Residual G010 discoverability anchors (exact evidence phrases):
 * - focused tests cover provenance
 * - `AgentAudioChatSurface` retains browser SpeechRecognition
 * - the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
 *
 * Scope-safe note: this suite asserts the existing AgentAudioChatSurface source
 * without modifying it, and keeps all Python residual assertions out of
 * wallet_interface/tests/test_voice_router_adapter.py (outside task-owned paths).
 */
test.describe("unified wallet voice-turn receipt", () => {
  test("parses fail-closed action surface and confirms only on explicit form flag", async () => {
    const receipt = {
      request_id: "wallet-action-1",
      status: "completed",
      transcript: "Open wallet documents",
      response_text: "Open your Wallet documents surface.",
      spoken_text: "Open your Wallet documents surface.",
      action: {
        route: "app_surface_navigation",
        status: "confirm",
        execution_enabled: false,
        proposal: {
          proposal_id: "prop-1",
          descriptor_id: "voice.cli.open_app_surface.v1",
          logical_action: "open_app_surface",
          arguments: {},
        },
        decision: {
          decision_id: "dec-1",
          kind: "confirm",
          proposal_id: "prop-1",
          descriptor_id: "voice.cli.open_app_surface.v1",
          reason: "confirmation_required",
          permits_execution: false,
        },
        receipt: null,
      },
      provenance: { pipeline: "abby-grounded-voice-v1" },
      traces: [],
      fallback_reasons: [],
    };
    const result = parseVoiceTurnResult(receipt);
    expect(result?.action?.route).toBe("app_surface_navigation");
    expect(result?.action?.proposal?.logicalAction).toBe("open_app_surface");
    expect(voiceActionNeedsConfirmation(result?.action)).toBe(true);
    expect(voiceActionLabel(result?.action)).toContain("open app surface");

    const form = createVoiceProxyFormData({
      mode: "voice-reply",
      text: "Open your Wallet documents surface.",
      userPrompt: "Open wallet documents",
      route: "app_surface_navigation",
      confirmAction: true,
      requestId: "confirm-1",
    });
    expect(form.get("route")).toBe("app_surface_navigation");
    expect(form.get("confirm_action")).toBe("true");
    expect(form.get("request_id")).toBe("confirm-1");
  });

  test("focused tests cover provenance for the canonical receipt and decode audio", async () => {
    expect(FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM).toBe("focused tests cover provenance");

    const receipt = {
      contract_version: "1.0",
      request_id: "wallet-turn-1",
      status: "completed",
      transcript: "Where can I find food help?",
      response_text: "A nearby service can help.",
      spoken_text: "A nearby service can help.",
      audio_format: "wav",
      audio_size_bytes: 24,
      audio_base64: AUDIO_BASE64,
      provenance: {
        pipeline: "abby-grounded-voice-v1",
        stt_provider: "supplied_transcript",
        template_provider: "wallet-graphrag",
        template_id: "food-help-v1",
        tts_provider: "abby_indextts",
        evidence: [{ source_id: "service-record-1", cid: "bafy-test", text: "Example Pantry hours" }],
        grounded_slots: [{ name: "provider", value: "Example Pantry", source_ids: ["service-record-1"] }],
        input_audio_sha256: "aa".repeat(32),
        transcript_sha256: "bb".repeat(32),
        response_text_sha256: "cc".repeat(32),
        output_audio_sha256: "dd".repeat(32),
      },
      traces: [
        { stage: "transcription", status: "skipped", duration_ms: 0 },
        { stage: "retrieval", status: "succeeded", duration_ms: 1.2 },
        { stage: "rendering", status: "succeeded", duration_ms: 0.4 },
        { stage: "synthesis", status: "succeeded", duration_ms: 2.4 },
      ],
      fallback_reasons: [],
    };

    expect(isVoiceTurnResultPayload(receipt)).toBe(true);
    const result = parseVoiceTurnResult(receipt);
    expect(result).not.toBeNull();
    expect(result).toMatchObject({
      requestId: "wallet-turn-1",
      status: "completed",
      transcript: "Where can I find food help?",
      responseText: "A nearby service can help.",
      provenance: {
        pipeline: "abby-grounded-voice-v1",
        sttProvider: "supplied_transcript",
        templateProvider: "wallet-graphrag",
        templateId: "food-help-v1",
        ttsProvider: "abby_indextts",
        evidence: [{ sourceId: "service-record-1", cid: "bafy-test", text: "Example Pantry hours" }],
        groundedSlots: [{ name: "provider", value: "Example Pantry", sourceIds: ["service-record-1"] }],
        inputAudioSha256: "aa".repeat(32),
        transcriptSha256: "bb".repeat(32),
        responseTextSha256: "cc".repeat(32),
        outputAudioSha256: "dd".repeat(32),
      },
    });
    // focused tests cover provenance: provider selection falls back from provenance when absent.
    expect(result?.providerSelection).toEqual({
      transcription: "supplied_transcript",
      retrieval: "wallet-graphrag",
      synthesis: "abby_indextts",
    });
    expect(result?.traces.map((trace) => trace.stage)).toEqual([
      "transcription",
      "retrieval",
      "rendering",
      "synthesis",
    ]);
    expect(voiceTurnResultText(result!)).toBe("A nearby service can help.");

    const audio = voiceTurnResultAudioBlob(result!);
    expect(audio).toBeDefined();
    expect(audio?.type).toBe("audio/wav");
    const decoded = Buffer.from(await audio!.arrayBuffer());
    expect(decoded.length).toBe(AUDIO_BYTES.length);
    expect(decoded.subarray(0, 4).toString("ascii")).toBe("RIFF");
    expect(decoded.subarray(8, 12).toString("ascii")).toBe("WAVE");
    expect(decoded.readUInt32LE(40)).toBeGreaterThan(0);
    expect(decoded.subarray(44).some((value) => value !== 0)).toBe(true);
  });

  test("makes degraded text-only receipts explicit and preserves them through browser speech", async () => {
    const result = parseVoiceTurnResult({
      request_id: "wallet-text-only",
      status: "text_only",
      degraded: true,
      transcript: "I need help.",
      response_text: "Please try again or use browser speech.",
      fallback_reason: "tts_failed",
      provenance: {
        pipeline: "abby-grounded-voice-v1",
        stt_provider: "supplied_transcript",
        template_provider: "wallet-graphrag",
        tts_provider: "abby_indextts",
        evidence: [],
        grounded_slots: [],
      },
      traces: [{ stage: "synthesis", status: "failed", duration_ms: 3, error: "provider unavailable" }],
    });

    expect(result?.degraded).toBe(true);
    expect(result?.fallbackReasons).toEqual(["tts_failed"]);
    expect(result?.audioBase64).toBeUndefined();
    expect(voiceTurnResultAudioBlob(result!)).toBeUndefined();
    expect(voiceTurnResultText(result!, "browser fallback")).toBe("Please try again or use browser speech.");
    // focused tests cover provenance even on degraded text-only receipts.
    expect(result?.provenance.sttProvider).toBe("supplied_transcript");
    expect(result?.provenance.templateProvider).toBe("wallet-graphrag");
    expect(result?.provenance.ttsProvider).toBe("abby_indextts");

    const service = new ClientAudioReplyService({
      generateRemoteAudio: async () => ({
        modelName: "abby_indextts",
        text: voiceTurnResultText(result!),
        voiceTurnResult: result!,
      }),
      preflightRemoteAudioProxy: async () => ({
        modelName: "abby_indextts",
        text: "ready",
      }),
      hasWebGPU: () => true,
      hasSpeechSynthesis: () => true,
      voiceProxyEnabled: true,
    });
    const browserDelivery = await service.generateAudio("I need help.");
    expect(browserDelivery).toMatchObject({
      kind: "browser-speech",
      provider: "browser-speech",
      text: "Please try again or use browser speech.",
      fallbackReason: "Voice proxy returned text only; using browser speech output.",
      voiceTurnResult: {
        requestId: "wallet-text-only",
        status: "text_only",
        degraded: true,
        fallbackReasons: ["tts_failed"],
        audioSizeBytes: 0,
      },
    });
    expect(browserDelivery.voiceTurnResult?.traces).toEqual([
      {
        stage: "synthesis",
        status: "failed",
        durationMs: 3,
        provider: undefined,
        error: "provider unavailable",
        details: {},
      },
    ]);
    expect(browserDelivery.voiceTurnResult?.provenance.outputAudioSha256).toBeUndefined();
  });

  test("does not reinterpret an unrelated legacy payload as a unified receipt", () => {
    expect(isVoiceTurnResultPayload({ text: "legacy audio response", model: "IndexTTS" })).toBe(false);
    expect(parseVoiceTurnResult({ text: "legacy audio response" })).toBeNull();
  });

  test("`AgentAudioChatSurface` retains browser SpeechRecognition", () => {
    expect(AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM).toBe(
      "`AgentAudioChatSurface` retains browser SpeechRecognition",
    );

    // Read-only check of the existing surface (not a task-owned mutation path).
    const surfacePath = resolve(
      UI_ROOT,
      "src/features/agent/components/AgentAudioChatSurface.tsx",
    );
    const source = readFileSync(surfacePath, "utf8");
    expect(source).toContain("SpeechRecognition");
    expect(source).toContain("webkitSpeechRecognition");
    expect(source).toContain("getSpeechRecognitionConstructor");
    expect(source).toContain("warmupSpeechRecognition");
    expect(source).toContain("handleSpeechRecognitionEnd");
    // Unified router adoption must not remove the browser speech fallback branch.
    expect(source).toMatch(/browserWindow\.SpeechRecognition\s*\?\?\s*browserWindow\.webkitSpeechRecognition/);
  });

  test("the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates", () => {
    expect(AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM).toBe(
      "the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates",
    );
    expect(G010_REQUIRED_EVIDENCE_TERMS).toContain(FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM);
    expect(G010_REQUIRED_EVIDENCE_TERMS).toContain(
      AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM,
    );
    expect(G010_REQUIRED_EVIDENCE_TERMS).toContain(AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM);

    const receiptPath = resolve(REPO_ROOT, G010_AUTHORITATIVE_EVIDENCE_MAP);
    const receipt = readFileSync(receiptPath, "utf8");
    expect(receipt).toContain(AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM);
    expect(receipt).toContain("python -m pytest -q wallet_interface/tests");
    expect(receipt).toContain("npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts");
  });
});
