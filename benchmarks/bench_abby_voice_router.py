#!/usr/bin/env python3
"""Deterministic offline benchmark and quality gate for the Abby voice router.

The benchmark intentionally uses in-memory collaborators.  It measures the
router's contract overhead, the legacy response-cache hit path, and provider
fallback behavior without downloading a model or contacting a remote service.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ipfs_accelerate_py"))

from ipfs_accelerate_py.router_deps import RouterDeps  # noqa: E402
from ipfs_accelerate_py.voice_router import (  # noqa: E402
    GroundedSlot,
    VoiceGroundingSource,
    VoiceProviderCapabilities,
    VoiceResponsePlan,
    VoiceTurnRequest,
    VoiceTurnResult,
    clear_voice_router_caches,
    process_voice_turn,
    register_voice_provider,
    text_to_speech,
)


GOLDEN_PATH = ROOT / "data/abby_voice/eval/golden_voice_turns.jsonl"


def _load_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _plan(row: Mapping[str, Any]) -> VoiceResponsePlan | None:
    raw = row.get("response_plan")
    if raw is None:
        return None
    evidence = tuple(
        VoiceGroundingSource(
            source_id=item["source_id"],
            cid=item.get("cid"),
            text=item.get("text"),
            facts=item.get("facts", {}),
        )
        for item in raw.get("evidence", [])
    )
    slots = tuple(
        GroundedSlot(item["name"], item.get("value"), tuple(item.get("source_ids", [])))
        for item in raw.get("slots", [])
    )
    return VoiceResponsePlan(
        template_id=raw["template_id"],
        template=raw["template"],
        slots=slots,
        evidence=evidence,
        confidence=raw.get("confidence", 1.0),
        intent=raw.get("intent"),
    )


@dataclass
class BenchSpeech:
    name: str
    transcript: str
    fail_synthesis: bool = False
    calls: int = 0

    def transcribe(self, audio: object, **kwargs: object) -> str:
        self.calls += 1
        return self.transcript

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.calls += 1
        if self.fail_synthesis:
            raise RuntimeError("offline synthetic provider failure")
        return b"RIFF\x00\x00\x00\x00WAVEoffline-benchmark-audio"


@dataclass
class BenchTemplate:
    row: Mapping[str, Any]
    provider_name: str = "offline-golden-graphrag"

    def retrieve(self, transcript: str, **kwargs: object) -> VoiceResponsePlan | None:
        return _plan(self.row)


def _run(row: Mapping[str, Any]) -> VoiceTurnResult:
    speech = BenchSpeech("offline-speech", row["observed_transcript"])
    return process_voice_turn(
        VoiceTurnRequest(
            audio=("benchmark-audio-" + row["case_id"]).encode(),
            request_id="benchmark-" + row["case_id"],
            locale=row["locale"],
            output_format="wav",
        ),
        stt_provider=speech,
        template_provider=BenchTemplate(row),
        tts_provider=speech,
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]


def _wer(reference: str, hypothesis: str) -> float:
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    previous = list(range(len(hyp) + 1))
    for i, word in enumerate(ref, 1):
        current = [i]
        for j, candidate in enumerate(hyp, 1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (word != candidate),
            ))
        previous = current
    return previous[-1] / max(1, len(ref))


def _cache_measurement() -> dict[str, Any]:
    clear_voice_router_caches()
    deps = RouterDeps()
    provider = BenchSpeech("offline-cache-provider", "unused")
    text = "A cache-safe synthetic response."
    started = time.perf_counter()
    first = text_to_speech(text, provider_instance=provider, output_format="wav", deps=deps)
    first_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    second = text_to_speech(text, provider_instance=provider, output_format="wav", deps=deps)
    second_ms = (time.perf_counter() - started) * 1000
    synth_calls = provider.calls
    return {
        "first_ms": round(first_ms, 3),
        "cached_ms": round(second_ms, 3),
        "cache_hit": first == second and synth_calls == 1,
        "provider_synthesis_calls": synth_calls,
    }


def _fallback_measurement() -> dict[str, Any]:
    class Primary(BenchSpeech):
        def __init__(self) -> None:
            super().__init__("offline-primary", "unused", fail_synthesis=True)

    class Secondary(BenchSpeech):
        def __init__(self) -> None:
            super().__init__("offline-secondary", "unused")

    register_voice_provider(
        "offline-primary",
        Primary,
        capabilities=VoiceProviderCapabilities(transcription=False, synthesis=True),
    )
    register_voice_provider(
        "offline-secondary",
        Secondary,
        capabilities=VoiceProviderCapabilities(transcription=False, synthesis=True),
    )
    durations: list[float] = []
    results: list[VoiceTurnResult] = []
    for index in range(8):
        started = time.perf_counter()
        results.append(process_voice_turn(
            VoiceTurnRequest(
                transcript="I need help",
                request_id=f"fallback-{index}",
                tts_provider="offline-primary",
                tts_providers=("offline-secondary",),
            ),
            template_provider=None,
        ))
        durations.append((time.perf_counter() - started) * 1000)
    return {
        "p95_ms": round(_percentile(durations, 95), 3),
        "all_audio_present": all(item.audio for item in results),
        "fallback_recorded": all("tts_provider_fallback" in item.fallback_reasons for item in results),
        "selected_provider": results[-1].provenance.tts_provider,
    }


def run_benchmark(*, iterations: int = 5) -> dict[str, Any]:
    rows = _load_rows()
    route_durations: list[float] = []
    results: list[VoiceTurnResult] = []
    for _ in range(max(1, iterations)):
        for row in rows:
            started = time.perf_counter()
            results.append(_run(row))
            route_durations.append((time.perf_counter() - started) * 1000)

    grounded = [row for row in rows if row.get("response_plan") is not None]
    grounded_results = [item for row, item in zip(rows * max(1, iterations), results) if row.get("response_plan") is not None]
    wer_values = [_wer(row["reference_transcript"], result.transcript) for row, result in zip(rows * max(1, iterations), results)]
    slot_total = 0
    slot_exact = 0
    for row, result in zip(rows * max(1, iterations), results):
        expected_slots = (row.get("response_plan") or {}).get("slots", [])
        actual = {slot.name: slot for slot in result.provenance.grounded_slots}
        for slot in expected_slots:
            slot_total += 1
            slot_exact += int(
                slot["name"] in actual
                and str(actual[slot["name"]].value) == str(slot["value"])
                and set(actual[slot["name"]].source_ids) == set(slot["source_ids"])
            )

    checks = {
        "golden_cases_present": len(rows) >= 8,
        "stt_wer_le_5_percent": statistics.mean(wer_values) <= 0.05,
        "retrieval_success_for_plans": all(item.provenance.template_id for item in grounded_results),
        "slot_fidelity_100_percent": slot_total > 0 and slot_exact == slot_total,
        "crisis_policy_present": any(
            row["category"] == "crisis" and "911" in result.spoken_text and "now" in result.spoken_text.lower()
            for row, result in zip(rows * max(1, iterations), results)
        ),
        "spoken_output_readable": all(
            not any(token in result.spoken_text.lower() for token in ("http://", "https://", "ipfs://", "<speak>"))
            for result in results
        ),
    }
    cache = _cache_measurement()
    fallback = _fallback_measurement()
    checks["cache_hit_without_second_synthesis"] = cache["cache_hit"]
    checks["fallback_receipt_and_audio"] = fallback["fallback_recorded"] and fallback["all_audio_present"]
    checks["route_p95_under_1000ms"] = _percentile(route_durations, 95) <= 1000
    checks["fallback_p95_under_1000ms"] = fallback["p95_ms"] <= 1000
    return {
        "benchmark_version": "abby_voice_router_benchmark_v1",
        "mode": "offline",
        "cases": len(rows),
        "iterations": max(1, iterations),
        "metrics": {
            "wer_mean": round(statistics.mean(wer_values), 6),
            "retrieval_plan_cases": len(grounded),
            "slot_fidelity": round(slot_exact / max(1, slot_total), 6),
            "route_p50_ms": round(_percentile(route_durations, 50), 3),
            "route_p95_ms": round(_percentile(route_durations, 95), 3),
            "route_max_ms": round(max(route_durations), 3),
            "cache": cache,
            "fallback": fallback,
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use only synthetic in-memory collaborators")
    parser.add_argument("--check", action="store_true", help="return non-zero when an acceptance gate fails")
    parser.add_argument("--iterations", type=int, default=5, help="repetitions per golden case")
    args = parser.parse_args()
    if not args.offline:
        parser.error("--offline is required; this benchmark never contacts remote services")
    report = run_benchmark(iterations=args.iterations)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
