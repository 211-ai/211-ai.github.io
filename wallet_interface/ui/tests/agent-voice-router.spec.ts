import { expect, test } from "@playwright/test";

import {
  isVoiceTurnResultPayload,
  parseVoiceTurnResult,
  voiceTurnResultAudioBlob,
  voiceTurnResultText,
} from "../src/features/agent/lib/voiceTurnResult";

const AUDIO_BASE64 = Buffer.from("RIFF-unified-wallet-audio", "utf8").toString("base64");

test.describe("unified wallet voice-turn receipt", () => {
  test("parses the canonical receipt, retains provenance, and decodes audio", async () => {
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
        evidence: [{ source_id: "service-record-1", cid: "bafy-test" }],
        grounded_slots: [{ name: "provider", value: "Example Pantry", source_ids: ["service-record-1"] }],
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
        templateId: "food-help-v1",
        evidence: [{ sourceId: "service-record-1", cid: "bafy-test" }],
      },
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
    expect(await audio?.text()).toBe("RIFF-unified-wallet-audio");
  });

  test("makes degraded text-only receipts explicit and keeps browser fallback text usable", () => {
    const result = parseVoiceTurnResult({
      request_id: "wallet-text-only",
      status: "text_only",
      degraded: true,
      transcript: "I need help.",
      response_text: "Please try again or use browser speech.",
      fallback_reason: "tts_failed",
      provenance: { evidence: [], grounded_slots: [] },
      traces: [{ stage: "synthesis", status: "failed", duration_ms: 3, error: "provider unavailable" }],
    });

    expect(result?.degraded).toBe(true);
    expect(result?.fallbackReasons).toEqual(["tts_failed"]);
    expect(result?.audioBase64).toBeUndefined();
    expect(voiceTurnResultAudioBlob(result!)).toBeUndefined();
    expect(voiceTurnResultText(result!, "browser fallback")).toBe("Please try again or use browser speech.");
  });

  test("does not reinterpret an unrelated legacy payload as a unified receipt", () => {
    expect(isVoiceTurnResultPayload({ text: "legacy audio response", model: "IndexTTS" })).toBe(false);
    expect(parseVoiceTurnResult({ text: "legacy audio response" })).toBeNull();
  });
});
