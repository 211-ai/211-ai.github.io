#!/usr/bin/env python3
"""Evaluate symbolic retrieval reliability on v2 variant lattices (VAS2-021/022).

Uses the same sparse hashed-token embeddings as the slotted DAG intents.
For each non-negative P0/P1 variant, embed user_text and rank intent nodes by
cosine-like sparse overlap; success if top-k intents share expected route or
surface-aligned route family.

Usage:
  python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --write
  python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --check
  python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --write --repair
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.simulate_211_conversations import generate_memory_embeddings  # noqa: E402

VARIANTS = REPO / "data" / "voice_app_surface_full_coverage" / "variants"
DAG = REPO / "docs" / "phone_dialog_generation" / "slotted_response_dag.json"
REPORT = (
    REPO
    / "data"
    / "voice_app_surface_full_coverage"
    / "reports"
    / "retrieval-reliability.json"
)
REPORT_AFTER = (
    REPO
    / "data"
    / "voice_app_surface_full_coverage"
    / "reports"
    / "retrieval-reliability-after-repair.json"
)
CHANGELOG = (
    REPO
    / "data"
    / "voice_app_surface_full_coverage"
    / "reports"
    / "retrieval-repair-changelog.md"
)
PROGRAM_ID = "voice-app-surface-full-coverage-v2"

# Thresholds (program defaults; symbolic offline).
TOP1_MIN = 0.55
TOP3_MIN = 0.75
# Cancel-like negatives only (authority-gated open attempts are excluded).
NEG_DENY_MIN = 0.70
MAX_EVAL_PER_SURFACE = 80  # sample for speed


def _sparse_dot(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(float(v) * float(b[k]) for k, v in a.items() if k in b)


def _norm(a: dict[str, float]) -> float:
    return math.sqrt(sum(float(v) * float(v) for v in a.values())) or 1.0


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    return _sparse_dot(a, b) / (_norm(a) * _norm(b))


def load_variants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tier in ("p0", "p1", "p2"):
        d = VARIANTS / tier
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    row["_tier"] = tier
                    rows.append(row)
    return rows


def sample_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sid = str(r.get("surface_id") or "unknown")
        by_surface.setdefault(sid, []).append(r)
    out: list[dict[str, Any]] = []
    for sid, items in sorted(by_surface.items()):
        # Prefer non-negative first for ranking sample
        pos = [x for x in items if not x.get("negative")]
        neg = [x for x in items if x.get("negative")]
        # deterministic stride sample
        def take(lst: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
            if len(lst) <= n:
                return lst
            step = max(1, len(lst) // n)
            return [lst[i] for i in range(0, len(lst), step)][:n]

        out.extend(take(pos, MAX_EVAL_PER_SURFACE))
        out.extend(take(neg, min(20, MAX_EVAL_PER_SURFACE // 2)))
    return out


def load_intents(dag: dict[str, Any]) -> list[dict[str, Any]]:
    intents = list(dag.get("nodes", {}).get("intents") or [])
    # Prefer intents that carry embeddings; drop empty
    out = []
    for it in intents:
        emb = it.get("embedding")
        text = str(it.get("canonicalQueryTemplate") or "").strip()
        if not text:
            continue
        if not isinstance(emb, dict) or not emb:
            continue
        out.append(it)
    return out


def expected_routes_for_variant(v: dict[str, Any]) -> set[str]:
    routes: set[str] = set()
    er = str(v.get("expected_route") or "").strip()
    if er:
        routes.add(er)
    la = str(v.get("logical_action") or "")
    mapping = {
        "open_app_surface": {"app_surface_navigation"},
        "read_calendar": {"calendar_event_support"},
        "create_calendar_reminder": {"calendar_event_support"},
        "read_provider_messages": {"provider_contact_support"},
        "leave_provider_message": {"provider_contact_support"},
        "open_wallet_documents": {"wallet_document_support"},
        "open_service_detail": {"grounded_211_answer"},
        "schedule_service_callback": {"service_interaction_support"},
        "no_action": {"template_guided_fallback", "clarifying_prompt", "repeat_or_restate"},
    }
    routes |= mapping.get(la, set())
    return routes


def intent_routes(intent: dict[str, Any]) -> set[str]:
    routes = intent.get("routes") or {}
    if isinstance(routes, dict):
        return {str(k) for k in routes.keys()}
    if isinstance(routes, list):
        return {str(x) for x in routes}
    return set()


def evaluate(dag: dict[str, Any], variants: list[dict[str, Any]]) -> dict[str, Any]:
    intents = load_intents(dag)
    if not intents:
        return {"error": "no intents with embeddings", "meets_thresholds": False}

    sample = sample_variants(variants)
    pos = [v for v in sample if not v.get("negative")]
    neg = [v for v in sample if v.get("negative")]

    # Embed queries
    pos_texts = [str(v.get("user_text") or "") for v in pos]
    embeddings, _info = generate_memory_embeddings(
        pos_texts, provider="deterministic_sparse_fallback"
    ) if pos_texts else ([], {})

    top1_hits = 0
    top3_hits = 0
    per_surface: dict[str, Counter[str]] = {}
    failures: list[dict[str, Any]] = []

    for v, emb in zip(pos, embeddings):
        sid = str(v.get("surface_id") or "unknown")
        expected = expected_routes_for_variant(v)
        scored: list[tuple[float, dict[str, Any]]] = []
        for it in intents:
            score = _cos(emb, it["embedding"])
            scored.append((score, it))
        scored.sort(key=lambda x: -x[0])
        top = scored[:3]
        top_routes = [intent_routes(it) for _, it in top]
        hit1 = bool(top_routes and (top_routes[0] & expected))
        hit3 = any(r & expected for r in top_routes)
        if hit1:
            top1_hits += 1
        if hit3:
            top3_hits += 1
        else:
            failures.append(
                {
                    "surface_id": sid,
                    "user_text": v.get("user_text"),
                    "expected_routes": sorted(expected),
                    "top1_routes": sorted(top_routes[0]) if top_routes else [],
                    "top1_score": top[0][0] if top else 0.0,
                }
            )
        bucket = per_surface.setdefault(sid, Counter())
        bucket["n"] += 1
        bucket["top1"] += int(hit1)
        bucket["top3"] += int(hit3)

    # Negatives split into two classes:
    # 1) pure cancel/no_action → retrieval should prefer content-only / low score
    # 2) open-attempt on never_voice/staff → authority plane denies; retrieval may still
    #    match navigation neighborhoods (not counted against retrieval reliability).
    content_only = {
        "clarifying_prompt",
        "repeat_or_restate",
        "template_guided_fallback",
        "speech_unclear_clarification",
    }
    cancel_like = 0
    cancel_ok = 0
    authority_gated = 0
    if neg:
        neg_texts = [str(v.get("user_text") or "") for v in neg]
        neg_embs, _ = generate_memory_embeddings(
            neg_texts, provider="deterministic_sparse_fallback"
        )
        for v, emb in zip(neg, neg_embs):
            la = str(v.get("logical_action") or "")
            text = str(v.get("user_text") or "").lower()
            is_cancel = la == "no_action" or any(
                k in text
                for k in (
                    "cancel",
                    "never mind",
                    "don't open",
                    "stop",
                    "no thanks",
                    "abort",
                    "forget it",
                    "not now",
                )
            )
            if not is_cancel and la == "open_app_surface":
                authority_gated += 1
                continue
            cancel_like += 1
            best = None
            best_score = -1.0
            for it in intents:
                score = _cos(emb, it["embedding"])
                if score > best_score:
                    best_score = score
                    best = it
            routes = intent_routes(best) if best else set()
            if best_score < 0.2 or (routes & content_only) or not (
                routes
                & {
                    "app_surface_navigation",
                    "calendar_event_support",
                    "wallet_document_support",
                }
            ):
                cancel_ok += 1

    n_pos = max(1, len(pos))
    top1 = top1_hits / n_pos if pos else 0.0
    top3 = top3_hits / n_pos if pos else 0.0
    neg_rate = (cancel_ok / cancel_like) if cancel_like else 1.0

    surface_stats = {
        sid: {
            "n": c["n"],
            "top1": c["top1"] / c["n"] if c["n"] else 0.0,
            "top3": c["top3"] / c["n"] if c["n"] else 0.0,
        }
        for sid, c in sorted(per_surface.items())
    }

    meets = top1 >= TOP1_MIN and top3 >= TOP3_MIN and neg_rate >= NEG_DENY_MIN
    fail_reasons = []
    if top1 < TOP1_MIN:
        fail_reasons.append(f"top1 {top1:.3f} < {TOP1_MIN}")
    if top3 < TOP3_MIN:
        fail_reasons.append(f"top3 {top3:.3f} < {TOP3_MIN}")
    if neg_rate < NEG_DENY_MIN:
        fail_reasons.append(f"negative_deny_rate {neg_rate:.3f} < {NEG_DENY_MIN}")

    return {
        "schema": "voice-app-surface-full-coverage/retrieval-reliability@1",
        "program_id": PROGRAM_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "intent_count": len(intents),
        "evaluated_positive": len(pos),
        "evaluated_negative": len(neg),
        "negative_cancel_like": cancel_like,
        "negative_authority_gated_opens": authority_gated,
        "top1_rate": round(top1, 4),
        "top3_rate": round(top3, 4),
        "negative_deny_rate": round(neg_rate, 4),
        "thresholds": {
            "top1_min": TOP1_MIN,
            "top3_min": TOP3_MIN,
            "negative_deny_min": NEG_DENY_MIN,
        },
        "meets_thresholds": meets,
        "failures": fail_reasons,
        "failure_samples": failures[:25],
        "per_surface": surface_stats,
        "note": (
            "Open-attempt negatives for never_voice/staff_only are authority-gated "
            "and excluded from negative_deny_rate; cancel-like negatives are scored."
        ),
    }


def apply_repair(report: dict[str, Any]) -> list[str]:
    """Document-only repair notes; optional soft threshold adjust is not done.

    Real repair adds pad exemplars already in fold; here we write changelog
    listing weak surfaces for operator follow-up.
    """
    notes: list[str] = []
    for sid, stats in (report.get("per_surface") or {}).items():
        if stats.get("top3", 1.0) < TOP3_MIN:
            notes.append(
                f"- **{sid}**: top3={stats.get('top3'):.3f} n={stats.get('n')} — "
                "prefer additional paraphrase exemplars in next lattice regen."
            )
    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Retrieval repair changelog (VAS2-022)",
        "",
        f"Generated: `{datetime.now(UTC).isoformat()}`",
        "",
        f"Baseline top1={report.get('top1_rate')} top3={report.get('top3_rate')} "
        f"neg={report.get('negative_deny_rate')} meets={report.get('meets_thresholds')}",
        "",
        "## Weak surfaces",
        "",
    ]
    body.extend(notes or ["- None below threshold in sample."])
    body.append("")
    CHANGELOG.write_text("\n".join(body), encoding="utf-8")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--after-repair", action="store_true")
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()

    if not DAG.is_file():
        print(f"missing DAG {DAG}", file=sys.stderr)
        return 1
    dag = json.loads(DAG.read_text(encoding="utf-8"))
    variants = load_variants()
    if not variants:
        print("no variants found", file=sys.stderr)
        return 1

    if args.write or args.repair or not REPORT.is_file():
        report = evaluate(dag, variants)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "wrote": str(REPORT.relative_to(REPO)),
                    "top1": report.get("top1_rate"),
                    "top3": report.get("top3_rate"),
                    "neg": report.get("negative_deny_rate"),
                    "meets": report.get("meets_thresholds"),
                },
                indent=2,
            )
        )
        if args.repair or not report.get("meets_thresholds"):
            apply_repair(report)
            # Re-eval after repair notes (same metrics; repair is content changelog)
            after = dict(report)
            after["generated_at"] = datetime.now(UTC).isoformat()
            after["repair_applied"] = True
            after["repair_changelog"] = str(CHANGELOG.relative_to(REPO))
            # If still failing, mark partial with residual
            REPORT_AFTER.write_text(json.dumps(after, indent=2, sort_keys=True) + "\n")
            print(f"wrote {REPORT_AFTER}")

    if args.check:
        path = REPORT_AFTER if args.after_repair and REPORT_AFTER.is_file() else REPORT
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 1
        data = json.loads(path.read_text())
        # Soft-pass if sample is thin but rates are near threshold after fold
        # Program: require meets_thresholds for hard green; else fail with residual.
        if not data.get("meets_thresholds"):
            print(
                "retrieval reliability FAILED:",
                data.get("failures"),
                file=sys.stderr,
            )
            return 1
        print(
            "retrieval reliability OK:",
            "top1=",
            data.get("top1_rate"),
            "top3=",
            data.get("top3_rate"),
            "neg=",
            data.get("negative_deny_rate"),
            "authority_gated_neg=",
            data.get("negative_authority_gated_opens"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
