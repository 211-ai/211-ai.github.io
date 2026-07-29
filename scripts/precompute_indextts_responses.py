#!/usr/bin/env python3
"""Precompute Abby IndexTTS audio for conversation DAG voice responses."""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import difflib
import hashlib
import importlib.util
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import wave
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib import parse as urllib_parse
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from ipfs_accelerate_py.hf_space_inference import (
        HFBucketBackend,
        HFSpaceClient,
        RefreshableGradioFile,
        is_hf_space_transport_error,
        is_retryable_hf_space_error,
        is_stale_gradio_file_error,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised in lean local test envs
    class HFBucketBackend:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("ipfs_accelerate_py.hf_space_inference is unavailable")

    class HFSpaceClient:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("ipfs_accelerate_py.hf_space_inference is unavailable")

    class RefreshableGradioFile:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("ipfs_accelerate_py.hf_space_inference is unavailable")

    def is_hf_space_transport_error(_value: object) -> bool:
        return False

    def is_retryable_hf_space_error(_value: object) -> bool:
        return False

    def is_stale_gradio_file_error(_value: object) -> bool:
        return False

try:
    from ipfs_accelerate_py.voice_jobs import (
        ArtifactPolicy as VoiceArtifactPolicy,
        VoiceJobExecutionError,
        validate_generated_audio_bytes,
    )
    _VOICE_AUDIO_VALIDATOR_IMPORT_ERROR: Exception | None = None
except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover - fail closed
    VoiceArtifactPolicy = None  # type: ignore[assignment,misc]
    VoiceJobExecutionError = None  # type: ignore[assignment,misc]
    validate_generated_audio_bytes = None  # type: ignore[assignment]
    _VOICE_AUDIO_VALIDATOR_IMPORT_ERROR = exc

IPFS_DATASETS_SECRETS_MODULE = REPO_ROOT / "ipfs_datasets_py" / "ipfs_datasets_py" / "utils" / "secrets.py"
DEFAULT_DAG = REPO_ROOT / "docs/211_conversation_dag.json"
DEFAULT_RESULTS = REPO_ROOT / "docs/211_chatbot_simulation_results.json"
DEFAULT_REFERENCE = REPO_ROOT / "tmp_assets/abby-reference.wav"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "wallet_interface/ui/public/assets/audio/precomputed/211-dag-indextts"
DEFAULT_MANIFEST = REPO_ROOT / "docs/211_indextts_precompute_manifest.json"
DEFAULT_PUBLIC_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"
DEFAULT_SLOTTED_RESPONSE_INDEX = REPO_ROOT / "wallet_interface/ui/public/assets/rag/slotted-response-index.json"
DEFAULT_INDEXTTS_SPACE_URL = "https://publicus-indextts-2-demo.hf.space"
DEFAULT_INDEXTTS_MODEL_NAME = "Publicus/IndexTTS-2-Demo"
DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE = 4
DEFAULT_INDEXTTS_MAX_TRAILING_SILENCE_MS = 1_000
INDEXTTS_TOKEN_ENV_NAMES = (
    "HF_TOKEN",
    "WALLET_INDEXTTS_HF_TOKEN",
    "HUGGINGFACEHUB_API_TOKEN",
    "IPFS_DATASETS_PY_HF_API_TOKEN",
    "HUGGINGFACE_API_TOKEN",
    "HUGGINGFACE_HUB_TOKEN",
)
SLOTTED_RESPONSE_FIELDS = (
    "slottedIntentIds",
    "slottedCanonicalQueryTemplates",
    "slottedResponseFrameIds",
    "slottedResponseSignatures",
    "slottedEdgeIds",
)


class IndexTTSQuotaExceededError(RuntimeError):
    def __init__(self, message: str, *, retry_after: str = "") -> None:
        super().__init__(message)
        self.retry_after = retry_after


class IndexTTSUploadResultUnverifiableError(RuntimeError):
    """Raised when a remote upload cannot be mapped to authoritative object URIs."""


def indextts_retry_after_hint(value: Any) -> str:
    match = re.search(r"Try again in (?P<retry>\d{1,2}:\d{2}:\d{2})", str(value or ""), flags=re.IGNORECASE)
    return match.group("retry") if match else ""


def is_indextts_quota_exceeded_error(value: Any) -> bool:
    text = str(value or "")
    lowered = text.casefold()
    return (
        "zerogpu quota exceeded" in lowered
        or ("zerogpu quota" in lowered and "exceed" in lowered)
        or ("quota exceeded" in lowered and "try again in" in lowered)
    )


def raise_if_indextts_quota_exceeded(value: Any) -> None:
    if not is_indextts_quota_exceeded_error(value):
        return
    retry_after = indextts_retry_after_hint(value)
    message = str(value or "IndexTTS ZeroGPU quota exceeded")
    raise IndexTTSQuotaExceededError(message, retry_after=retry_after)


def is_indextts_transient_worker_error(value: Any) -> bool:
    error_type = VoiceJobExecutionError
    if (
        isinstance(error_type, type)
        and isinstance(value, error_type)
        and bool(getattr(value, "retryable", False))
    ):
        return True
    if is_retryable_hf_space_error(value):
        return True
    text = str(value or "")
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "zerogpu worker error",
            "acceleratorerror",
            "queue full",
            "queue_full",
            "temporarily unavailable",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "space queue failed",
            "queue failed",
            "timed out",
            "connection reset",
            "remote disconnected",
            "audio_trailing_silence_exceeded",
        )
    )


def is_indextts_audio_validation_error(value: Any) -> bool:
    error_type = VoiceJobExecutionError
    return (
        isinstance(error_type, type)
        and isinstance(value, error_type)
    )


def batch_failure_result(
    error: Exception,
    *,
    batch_mode: str,
    fallback_reason: str,
    requested_batch_size: int,
    executed_batch_size: int,
    split_depth: int,
) -> dict[str, Any]:
    retry_after = indextts_retry_after_hint(error)
    return {
        "error": f"{type(error).__name__}: {error}",
        "retriable": is_indextts_transient_worker_error(error) or bool(retry_after),
        **({"retryAfter": retry_after} if retry_after else {}),
        "batchMode": batch_mode,
        "batchFallbackReason": fallback_reason,
        "batchRequestedSize": requested_batch_size,
        "batchExecutedSize": executed_batch_size,
        "batchSplitDepth": split_depth,
    }


def stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


_ADDRESS_DIRECTION_WORDS = {
    "n": "North",
    "s": "South",
    "e": "East",
    "w": "West",
    "ne": "North East",
    "nw": "North West",
    "se": "South East",
    "sw": "South West",
}

_STREET_SUFFIX_WORDS = {
    "aly": "Alley",
    "allee": "Alley",
    "aly.": "Alley",
    "ave": "Avenue",
    "ave.": "Avenue",
    "aven": "Avenue",
    "avenu": "Avenue",
    "avenue": "Avenue",
    "blvd": "Boulevard",
    "blvd.": "Boulevard",
    "boul": "Boulevard",
    "boulevard": "Boulevard",
    "cir": "Circle",
    "cir.": "Circle",
    "circle": "Circle",
    "ct": "Court",
    "ct.": "Court",
    "court": "Court",
    "dr": "Drive",
    "dr.": "Drive",
    "drive": "Drive",
    "hwy": "Highway",
    "hwy.": "Highway",
    "highway": "Highway",
    "ln": "Lane",
    "ln.": "Lane",
    "lane": "Lane",
    "loop": "Loop",
    "pkwy": "Parkway",
    "pkwy.": "Parkway",
    "parkway": "Parkway",
    "pl": "Place",
    "pl.": "Place",
    "place": "Place",
    "rd": "Road",
    "rd.": "Road",
    "road": "Road",
    "st": "Street",
    "st.": "Street",
    "street": "Street",
    "ter": "Terrace",
    "ter.": "Terrace",
    "terrace": "Terrace",
    "trl": "Trail",
    "trl.": "Trail",
    "trail": "Trail",
    "way": "Way",
}

_UNIT_WORDS = {
    "apt": "Apartment",
    "apt.": "Apartment",
    "bldg": "Building",
    "bldg.": "Building",
    "fl": "Floor",
    "fl.": "Floor",
    "ste": "Suite",
    "ste.": "Suite",
    "suite": "Suite",
    "unit": "Unit",
}

_STATE_WORDS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

_OMITTED_VOICE_FIELDS = (
    "source",
    "source url",
    "url",
    "website",
    "link",
    "cid",
    "ipfs cid",
    "hash",
    "bundle hash",
    "record id",
    "schema",
    "metadata",
)

_RESOLVE_SECRET = None


def _number_to_words(value: int) -> str:
    if value < 0 or value > 9999:
        return str(value)
    ones = [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if value < 20:
        return ones[value]
    if value < 100:
        return tens[value // 10] if value % 10 == 0 else f"{tens[value // 10]} {ones[value % 10]}"
    if value < 1000:
        rest = value % 100
        return f"{ones[value // 100]} hundred" + (f" {_number_to_words(rest)}" if rest else "")
    rest = value % 1000
    return f"{_number_to_words(value // 1000)} thousand" + (f" {_number_to_words(rest)}" if rest else "")


def _ordinal_to_words(value: int) -> str:
    if value <= 0:
        return "zero"
    irregular = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
        11: "eleventh",
        12: "twelfth",
        13: "thirteenth",
        14: "fourteenth",
        15: "fifteenth",
        16: "sixteenth",
        17: "seventeenth",
        18: "eighteenth",
        19: "nineteenth",
    }
    tens_ordinals = {
        20: "twentieth",
        30: "thirtieth",
        40: "fortieth",
        50: "fiftieth",
        60: "sixtieth",
        70: "seventieth",
        80: "eightieth",
        90: "ninetieth",
    }
    if value in irregular:
        return irregular[value]
    if value in tens_ordinals:
        return tens_ordinals[value]
    if value < 100:
        return f"{_number_to_words(value - value % 10)} {_ordinal_to_words(value % 10)}"
    if value < 10000:
        base = _number_to_words(value - value % 100)
        rest = value % 100
        return f"{base} {_ordinal_to_words(rest)}" if rest else f"{base}th"
    return str(value)


def _normalize_direction_token(token: str) -> str:
    compact = re.sub(r"[^A-Za-z]", "", token).lower()
    return _ADDRESS_DIRECTION_WORDS.get(compact, token)


def _normalize_suffix_token(token: str) -> str:
    return _STREET_SUFFIX_WORDS.get(token.lower(), token)


def _digits_to_words(value: str) -> str:
    digit_words = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
    }
    return " ".join(digit_words.get(char, char) for char in value)


def _normalize_zip_codes(text: str) -> str:
    def replace_state_zip(match: re.Match[str]) -> str:
        if match.group("state") != match.group("state").upper():
            return match.group(0)
        state = _STATE_WORDS.get(match.group("state").upper(), match.group("state"))
        zip_code = _digits_to_words(match.group("zip"))
        plus_four = match.group("plus4")
        if plus_four:
            zip_code = f"{zip_code} dash {_digits_to_words(plus_four)}"
        return f"{state} {zip_code}"

    normalized = re.sub(
        r"\b(?P<state>AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\s+(?P<zip>\d{5})(?:-(?P<plus4>\d{4}))?\b",
        replace_state_zip,
        text,
        flags=re.IGNORECASE,
    )
    direction_pattern = r"(?:N|S|E|W|NE|NW|SE|SW|N\.E\.|N\.W\.|S\.E\.|S\.W\.|North|South|East|West|North East|North West|South East|South West)"
    suffix_pattern = "|".join(sorted((re.escape(value) for value in set(_STREET_SUFFIX_WORDS) | set(_STREET_SUFFIX_WORDS.values())), key=len, reverse=True))
    return re.sub(
        rf"(?<![\d-])(?P<zip>\d{{5}})(?:-(?P<plus4>\d{{4}}))?(?![\d-])(?!(?:\s+(?:{direction_pattern})\b|\s+[A-Z][A-Za-z'.-]+\s+(?:{suffix_pattern})\b))",
        lambda match: (
            f"{_digits_to_words(match.group('zip'))}"
            + (f" dash {_digits_to_words(match.group('plus4'))}" if match.group("plus4") else "")
        ),
        normalized,
    )


def _normalize_address_directions_and_highways(text: str) -> str:
    direction_pattern = r"(?:N|S|E|W|NE|NW|SE|SW|N\.E\.|N\.W\.|S\.E\.|S\.W\.)"
    suffix_pattern = "|".join(sorted((re.escape(value) for value in set(_STREET_SUFFIX_WORDS) | set(_STREET_SUFFIX_WORDS.values())), key=len, reverse=True))

    def replace_numbered_or_named_street(match: re.Match[str]) -> str:
        street = match.group("street")
        numbered = re.fullmatch(r"\d{1,3}(?:st|nd|rd|th)?", street, flags=re.IGNORECASE)
        street_words = _ordinal_to_words(int(re.sub(r"\D", "", street))) if numbered else street
        return (
            f"{match.group('number')} "
            f"{_normalize_direction_token(match.group('direction'))} "
            f"{street_words} "
            f"{_normalize_suffix_token(match.group('suffix'))}"
        )

    normalized = re.sub(
        rf"\b(?P<number>\d{{1,6}})\s+(?P<direction>{direction_pattern})\s+(?P<street>\d{{1,3}}(?:st|nd|rd|th)?|[A-Z][A-Za-z'.-]*(?:\s+[A-Z][A-Za-z'.-]*){{0,4}})\s+(?P<suffix>{suffix_pattern})\b",
        replace_numbered_or_named_street,
        text,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b(?P<number>\d{{1,6}})\s+(?P<direction>{direction_pattern})\s+(?P<street>[A-Z][A-Za-z'.-]+)\b(?=\s+(?:Suite|Room|Floor|Unit|Apartment|Building)\b)",
        lambda match: f"{match.group('number')} {_normalize_direction_token(match.group('direction'))} {match.group('street')}",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b(?P<number>\d{{1,6}})\s+(?P<direction>{direction_pattern})\s+(?P<street>[A-Z][A-Za-z'.-]+)\b(?=\s+(?:[A-Z][a-z]+,?\s+)?(?:OR|WA|CA|CO|Oregon|Washington|California|Colorado)\b|$)",
        lambda match: f"{match.group('number')} {_normalize_direction_token(match.group('direction'))} {match.group('street')}",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b(?P<suffix>{suffix_pattern})\s+(?P<direction>{direction_pattern})\b",
        lambda match: f"{_normalize_suffix_token(match.group('suffix'))} {_normalize_direction_token(match.group('direction'))}",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bHighway\s+(?P<number>\d{1,3})(?:\s+(?P<direction>N|S|E|W))?\b",
        lambda match: (
            f"Highway {_number_to_words(int(match.group('number')))}"
            + (f" {_normalize_direction_token(match.group('direction'))}" if match.group("direction") else "")
        ),
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _domain_to_spoken_site(url: str) -> str:
    parsed = urllib_parse.urlparse(url if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.IGNORECASE) else f"https://{url}")
    host = (parsed.netloc or parsed.path.split("/", 1)[0]).lower()
    host = host.removeprefix("www.")
    if not host:
        return "the website"
    if host in {"211info.org", "gethelp.211info.org"}:
        return "the two one one info website"
    first_label = host.split(".", 1)[0].replace("-", " ").strip()
    return f"the {first_label} website" if first_label else "the website"


def _strip_unspoken_fields(text: str) -> str:
    spoken = str(text or "")
    omitted_pattern = "|".join(re.escape(field) for field in sorted(_OMITTED_VOICE_FIELDS, key=len, reverse=True))
    spoken = re.sub(
        r"(?i)\b(?:phone|eligibility|address|location|hours|email|website)\s*:\s*[^.;]*(?:not listed|not available|unavailable|not provided)[^.;]*(?=$|[.;])",
        " ",
        spoken,
    )
    spoken = re.sub(
        rf"(?i)(?:^|[\s.;])(?:{omitted_pattern})\s*:\s*(?:https?://\S+|www\.\S+|[^\n.;]+)(?=$|[\n.;])",
        " ",
        spoken,
    )
    spoken = re.sub(
        r"(?i)(?:^|[.!?]\s+)[^.!?]*(?:not listed|not available|unavailable|not provided) in this record[^.!?]*[.!?]?",
        " ",
        spoken,
    )
    return re.sub(r"\s*([.;,])\s*(?:[.;,]\s*)+", r"\1 ", spoken)


def _normalize_urls_for_speech(text: str) -> str:
    url_pattern = r"(?i)\b(?:https?://|www\.)[^\s<>)\]]+|\b[A-Za-z0-9][A-Za-z0-9.-]*\.(?:org|com|gov|net|edu)(?:/[^\s<>)\]]*)?"

    def replace_url(match: re.Match[str]) -> str:
        raw_url = match.group(0).rstrip(".,;:")
        trailing = match.group(0)[len(raw_url) :]
        return f"{_domain_to_spoken_site(raw_url)}{trailing}"

    return re.sub(url_pattern, replace_url, text)


def _strip_scraped_page_chrome(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"(?i)\bEmail\s+(?:\(\d{3}\)\s*)?\d{3}[-.]\d{4}\s+Get Directions\s+Visit Website\s+More Details\s+", " ", cleaned)
    cleaned = re.sub(r"(?i)\b(?:Email|Get Directions|Visit Website|More Details|Print\s*&\s*Share|Print PDF)\b", " ", cleaned)
    cleaned = re.sub(r"\bX\s+Print\s*&\s*Share\b", " ", cleaned)
    cleaned = re.sub(r"\bX\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_phone_numbers(text: str) -> str:
    digit_word = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
    }

    def replace_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            return match.group(0)
        return f"{_digits_to_words(digits[:3])}, {_digits_to_words(digits[3:6])}, {_digits_to_words(digits[6:])}"

    normalized = re.sub(
        r"(?:\+?1[\s,.\-–—]*)?(?:\(\d{3}\)|\d{3})[\s,.\-–—]*\d{3}[\s,.\-–—]*\d{4}\b",
        replace_phone,
        text,
    )

    def replace_long_digit_run(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f"{_digits_to_words(digits[:3])}, {_digits_to_words(digits[3:6])}, {_digits_to_words(digits[6:])}"
        return _digits_to_words(digits)

    normalized = re.sub(
        r"(?<!\d)(?:\d[\s,.;:\-–—]+){6,}\d(?!\d)",
        replace_long_digit_run,
        normalized,
    )
    normalized = re.sub(
        r"(?<!\d)(?:\d{1,4}[\s,.;:\-–—]+){2,}\d{1,4}(?!\d)",
        lambda match: replace_long_digit_run(match)
        if 7 <= len(re.sub(r"\D", "", match.group(0))) <= 11
        else match.group(0),
        normalized,
    )
    # Prior generation sometimes emitted already-chunked phone numbers as
    # digit-by-digit strings with hyphens (``5-0-3, 7-7-1, 7-9-1-4``).  Whisper
    # can hear the hyphens as "negative"; remove that acoustic trap before TTS.
    return re.sub(
        r"(?<!\d)(?:\d\s*[-–—]\s*){2,}\d(?!\d)",
        lambda match: " ".join(digit_word[char] for char in re.sub(r"\D", "", match.group(0))),
        normalized,
    )


def _normalize_phone_extensions(text: str) -> str:
    return re.sub(
        r"\b(?:ext\.?|extension|x)\s*#?\s*(?P<extension>\d{1,6})\b",
        lambda match: f"extension {_digits_to_words(match.group('extension'))}",
        text,
        flags=re.IGNORECASE,
    )


def _normalize_range_and_parenthetical_punctuation(text: str) -> str:
    ordinal_word_pattern = (
        "first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
        "eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|"
        "seventeenth|eighteenth|nineteenth|twentieth|thirtieth|fortieth|"
        "fiftieth|sixtieth|seventieth|eightieth|ninetieth|[A-Za-z]+th"
    )
    direction_word_pattern = (
        r"N|S|E|W|NE|NW|SE|SW|N\.E\.|N\.W\.|S\.E\.|S\.W\.|"
        r"North|South|East|West|Northeast|Northwest|Southeast|Southwest|"
        r"North\s+East|North\s+West|South\s+East|South\s+West"
    )
    suffix_pattern = "|".join(
        sorted(
            (re.escape(value) for value in set(_STREET_SUFFIX_WORDS) | set(_STREET_SUFFIX_WORDS.values())),
            key=len,
            reverse=True,
        )
    )
    street_token_pattern = (
        r"(?:\d{1,3}(?:st|nd|rd|th)?|"
        r"(?:[A-Za-z]+\s+){0,3}[A-Za-z]+)"
    )

    def replace_mixed_digit_ordinal(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group("digits"))
        return f"{_digits_to_words(digits)} {match.group('ordinal')}"

    def replace_address_number_hyphenation(match: re.Match[str]) -> str:
        return _digits_to_words(re.sub(r"\D", "", match.group("number")))

    normalized = re.sub(
        r"\b(?P<label>ages?\s+)(?P<start>\d{1,2})\s*[-–—]\s*(?P<end>\d{1,2})\b",
        lambda match: (
            f"{match.group('label')}"
            f"{_number_to_words(int(match.group('start')))} to {_number_to_words(int(match.group('end')))}"
        ),
        text,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"(?<!\w)(?P<digits>\d(?:\s*[-–—]\s*\d)+)\s*[-–—]\s*(?P<ordinal>{ordinal_word_pattern})\b",
        replace_mixed_digit_ordinal,
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b(?P<number>\d{{1,5}}(?:\s*[-–—]\s*\d{{1,5}})+)"
        rf"(?=\s+(?:(?:{direction_word_pattern})\s+)?"
        rf"(?:{street_token_pattern})\s+(?:{suffix_pattern})\b)",
        replace_address_number_hyphenation,
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\((?P<content>[^()]*)\)",
        lambda match: f", {match.group('content').strip()}, " if match.group("content").strip() else " ",
        normalized,
    )
    return normalized


def _title_case_program_name(value: str) -> str:
    acronyms = {
        "CAF",
        "DHS",
        "EBT",
        "HIV",
        "HUD",
        "ID",
        "LGBTQ",
        "LGBTQIA",
        "NARA",
        "NW",
        "SNAP",
        "SSDI",
        "SSI",
        "VA",
        "WIC",
    }
    small_words = {"and", "or", "of", "for", "to", "the", "a", "an", "in", "on", "at", "by", "with"}
    tokens = re.split(r"(\s+|-)", value.strip())
    output: list[str] = []
    word_index = 0
    for token in tokens:
        if not token or token.isspace() or token == "-":
            output.append(token)
            continue
        bare = re.sub(r"[^A-Za-z0-9]", "", token)
        if not bare:
            output.append(token)
            continue
        upper = bare.upper()
        lower = token.lower()
        if upper in acronyms:
            replacement = token.replace(bare, upper)
        elif word_index > 0 and lower in small_words:
            replacement = lower
        elif "'" in token:
            replacement = "'".join(part.capitalize() for part in lower.split("'"))
        else:
            replacement = lower.capitalize()
        replacement = replacement.replace("Peerplus", "Peer Plus")
        replacement = replacement.replace("Sbhc", "school based health center")
        replacement = replacement.replace("Chruch", "Church")
        output.append(replacement)
        word_index += 1
    return re.sub(r"\s+and$", "", "".join(output), flags=re.IGNORECASE)


def _normalize_phone_list_prosody(text: str) -> str:
    digit_word = r"(?:zero|one|two|three|four|five|six|seven|eight|nine)"
    phone = rf"{digit_word}(?: {digit_word}){{2}}, {digit_word}(?: {digit_word}){{2}}, {digit_word}(?: {digit_word}){{3}}"

    def replace_pair(match: re.Match[str]) -> str:
        first = match.group("first")
        second = match.group("second")
        second_extension = match.group("second_extension") or ""
        trailing = match.group("trailing")
        if first == second and second_extension:
            return f"You can call {first}, {second_extension}{trailing}"
        return f"You can call {first}. Another number is {second}{second_extension}{trailing}"

    return re.sub(
        rf"\bPhone:\s*(?P<first>{phone}),\s*(?P<second>{phone})(?P<second_extension>\s+extension\s+(?:{digit_word}\s*){{1,6}})?(?P<trailing>[.;])",
        replace_pair,
        text,
        flags=re.IGNORECASE,
    )


def _normalize_address_prosody(text: str) -> str:
    suffix_pattern = "|".join(sorted((re.escape(value) for value in set(_STREET_SUFFIX_WORDS.values())), key=len, reverse=True))
    state_pattern = "|".join(sorted((re.escape(value) for value in set(_STATE_WORDS.values())), key=len, reverse=True))
    normalized = re.sub(
        rf"\b(?P<street>{suffix_pattern})\s+(?P<city>(?!(?:North|South|East|West)\b)[A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,2}}),?\s+(?P<state>{state_pattern})\b",
        lambda match: f"{match.group('street')}, {match.group('city')}, {match.group('state')}",
        text,
    )
    normalized = re.sub(
        r"\b(?P<street>Street|Avenue|Road|Boulevard|Drive|Lane|Loop|Parkway|Court|Way)\s+(?P<unit>[A-Z])(?P<number>\d{1,4})(?=\s+[A-Z][a-z]+,\s+(?:Oregon|Washington|California|Colorado)\b)",
        lambda match: f"{match.group('street')}, building {match.group('unit')} {_number_to_words(int(match.group('number')))}",
        normalized,
    )
    normalized = re.sub(
        r"\b(?P<label>Suite|Unit|Apartment|Building|Floor)\s+(?P<unit>[A-Za-z0-9-]+)\s+(?=[A-Z][A-Za-z]+,?\s+(?:Oregon|Washington|California|Colorado)\b)",
        lambda match: f"{match.group('label')} {match.group('unit')}, ",
        normalized,
    )
    normalized = re.sub(
        r"\b(?P<street>Street|Avenue|Road|Boulevard|Drive|Lane|Loop|Parkway|Court|Way)\s+(?P<direction>North|South|East|West|North East|North West|South East|South West)\s+(?=[A-Z][a-z]+,?\s+(?:Oregon|Washington|California|Colorado)\b)",
        lambda match: f"{match.group('street')} {match.group('direction')}, ",
        normalized,
    )
    return normalized


def _prefer_primary_voice_contact(text: str) -> str:
    state_pattern = "|".join(sorted((re.escape(value) for value in set(_STATE_WORDS.values())), key=len, reverse=True))
    zip_words = r"(?:zero|one|two|three|four|five|six|seven|eight|nine)(?: (?:zero|one|two|three|four|five|six|seven|eight|nine)){4}(?: dash (?:zero|one|two|three|four|five|six|seven|eight|nine)(?: (?:zero|one|two|three|four|five|six|seven|eight|nine)){3})?"
    address_stop = re.compile(r",\s+(?=\d{2,6}\s+)")

    def replace_address(match: re.Match[str]) -> str:
        address = match.group("address")
        remainder = match.group("remainder")
        split = address_stop.search(address)
        if not split:
            return match.group(0)
        primary = address[: split.start()].strip(" ,")
        return f"The address is {primary}. There may be more locations in the service details.{remainder}"

    spoken = re.sub(
        rf"The address is (?P<address>.*?\b(?:{state_pattern}) {zip_words})(?P<remainder>\. (?:You can call|Phone number:))",
        replace_address,
        text,
    )
    return spoken


def _normalize_sentence_prosody(text: str) -> str:
    spoken = re.sub(
        r"\bI found (?P<name>[A-Z][A-Z0-9 &'(),/-]{3,})\.",
        lambda match: f"I found {_title_case_program_name(match.group('name'))}.",
        text,
    )
    spoken = re.sub(
        r"\bI found (?P<name>[A-Z][A-Z0-9 &'(),/-]{3,})\s+(?=Phone:|Phone number:|Eligibility:|The address is\b)",
        lambda match: f"I found {_title_case_program_name(match.group('name'))}. ",
        spoken,
    )
    spoken = re.sub(
        r"\bI found (VA [^.]*? Community Resource and Referral Center)\s+VA Community Resource and Referral Center\.",
        r"I found \1.",
        spoken,
    )
    spoken = re.sub(
        r"\bI found Saint (?P<name>[A-Z][A-Z0-9 &'(),/-]{3,})\.",
        lambda match: f"I found Saint {_title_case_program_name(match.group('name'))}.",
        spoken,
    )
    spoken = _normalize_phone_list_prosody(spoken)
    spoken = re.sub(
        r"\bAges?\s+(?P<start>\d{1,3})\s*-\s*(?P<end>\d{1,3})\b",
        lambda match: f"Ages {_number_to_words(int(match.group('start')))} to {_number_to_words(int(match.group('end')))}",
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(
        r"\bage\s+(?P<age>\d{1,3})\b",
        lambda match: f"age {_number_to_words(int(match.group('age')))}",
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = _normalize_address_prosody(spoken)
    spoken = _prefer_primary_voice_contact(spoken)
    spoken = spoken.replace("&", "and")
    spoken = re.sub(
        r"\bConfirm details before traveling, since service availability can change\.",
        "Please confirm details before you go, since service availability can change.",
        spoken,
    )
    spoken = re.sub(r"\bPhone:\s*", "You can call ", spoken)
    spoken = re.sub(r"\bPhone number:\s*", "You can call ", spoken)
    spoken = re.sub(r"\bAlternate phone number:\s*", "Another number is ", spoken)
    spoken = re.sub(r"\bAges ([^.]+?) All other\b", r"Ages \1. Other eligibility rules may apply", spoken)
    spoken = re.sub(r"\bI found Need Help Finding Child Care\?\s*Call two one one\.", "For help finding child care, call two one one.", spoken)
    spoken = re.sub(r"\bEligibility:\s*Unrestricted\.\s*anyone\b", "Eligibility: anyone", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bEligibility:\s*Unrestricted[.;]\s*Varies by program\.", "Eligibility varies by program.", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bEligibility:\s*(?P<body>[^.]+?\.)\s*Unrestricted[.;]", r"Eligibility: \g<body>", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bEligibility:\s*Unrestricted[.;]", "Eligibility is unrestricted.", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bEligibility:\s*None\.\s*", "Eligibility: ", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bEligibility:\s*", "Eligibility: ", spoken)
    spoken = re.sub(r"\bEligibility:\s*Individuals and families with minor children in substance use disorder recovery\.", "Eligibility: individuals and families with minor children who are in substance use disorder recovery.", spoken)
    spoken = re.sub(r"\bFPL\b", "federal poverty level", spoken)
    spoken = re.sub(r"\bFederal Poverty Level\b", "federal poverty level", spoken)
    spoken = re.sub(r"\s*\(federal poverty level\)", "", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bFamiles\b", "Families", spoken)
    spoken = re.sub(r"\s+(Veteran must\b)", r". \1", spoken)
    spoken = re.sub(r"\s+(Any discharge\b)", r". \1", spoken)
    spoken = re.sub(r"\s+(Household must\b)", r". \1", spoken)
    spoken = re.sub(r"\s+(Documentation may\b)", r". \1", spoken)
    spoken = re.sub(
        r"\bschool based health center\s+School Based Health Center\b",
        "school-based health center",
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(r"\bschool based health center\b", "school-based health center", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\bMen'S\b", "Men's", spoken)
    spoken = re.sub(r"\s*;\s*", ". ", spoken)
    spoken = _shorten_long_eligibility_for_voice(spoken)
    state_pattern = "|".join(sorted((re.escape(value) for value in set(_STATE_WORDS.values())), key=len, reverse=True))
    zip_words = r"(?:zero|one|two|three|four|five|six|seven|eight|nine)(?: (?:zero|one|two|three|four|five|six|seven|eight|nine)){4}(?: dash (?:zero|one|two|three|four|five|six|seven|eight|nine)(?: (?:zero|one|two|three|four|five|six|seven|eight|nine)){3})?"
    spoken = re.sub(rf"\b(?P<state>{state_pattern}) (?P<zip>{zip_words})\b", r"\g<state>. ZIP code \g<zip>", spoken)
    spoken = re.sub(r"\s+([.,;:!?])", r"\1", spoken)
    return re.sub(r"([.!?])\s*(?=(?:You can call|Another number|Eligibility|Please confirm)\b)", r"\1 ", spoken)


def _shorten_long_eligibility_for_voice(text: str) -> str:
    match = re.search(r"\bEligibility(?: is|:)\s+(?P<body>.*?)(?=\s+Before traveling\b|$)", text)
    if not match:
        return text
    body = match.group("body").strip()
    if len(body) <= 220:
        return text
    first_clause = re.split(r"(?<=[.!?])\s+|(?:\s+[A-Z][a-z]+:)", body, maxsplit=1)[0].strip()
    if len(first_clause) > 180:
        first_clause = first_clause[:180].rsplit(" ", 1)[0].strip() + "."
    replacement = f"Eligibility: {first_clause} More eligibility details may be in the service details."
    return f"{text[:match.start()]}{replacement}{text[match.end():]}"


def _normalize_percentages_and_currency(text: str) -> str:
    def numberish_to_words(value: str) -> str:
        if "." in value:
            left, right = value.split(".", 1)
            return f"{_number_to_words(int(left))} point {_digits_to_words(right)}"
        return _number_to_words(int(value))

    normalized = re.sub(
        r"\b(?P<start>\d{1,3})(?:\.\d+)?\s*-\s*(?P<end>\d{1,3}(?:\.\d+)?)%",
        lambda match: f"{numberish_to_words(match.group('start'))} to {numberish_to_words(match.group('end'))} percent",
        text,
    )
    normalized = re.sub(
        r"\b(?P<value>\d{1,3}(?:\.\d+)?)%",
        lambda match: f"{numberish_to_words(match.group('value'))} percent",
        normalized,
    )
    return re.sub(
        r"\$(?P<amount>\d{1,4})(?:\.(?P<cents>\d{2}))?",
        lambda match: (
            f"{_number_to_words(int(match.group('amount')))} dollars"
            + (f" and {_number_to_words(int(match.group('cents')))} cents" if match.group("cents") else "")
        ),
        normalized,
    )


def _normalize_hours_and_separators(text: str) -> str:
    day_names = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
    text = re.sub(r"\s*[-–]\s*211info\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\*\s*", " for ", text)
    text = re.sub(r"\s+/\s+", ", ", text)
    normalized = re.sub(rf"\b({day_names})(?:/({day_names}))+\b", lambda match: match.group(0).replace("/", ", "), text)
    normalized = re.sub(r"\b([A-Za-z]+)/([A-Za-z]+)\b", r"\1 and \2", normalized)
    normalized = re.sub(r"(?m)(^|\s)-(?=[A-Za-z])", r"\1", normalized)
    normalized = re.sub(r"\s+-\s*", " to ", normalized)
    normalized = re.sub(r"(?<=\d)(am|pm)\b", lambda match: f" {match.group(1).upper()}", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"(?<=\b(?:AM|PM))\s*-\s*(?=\d)", " to ", normalized)
    normalized = re.sub(r"\b9/11\b", "September eleventh", normalized)
    return normalized


def _strip_coordinates(text: str) -> str:
    if re.fullmatch(r"\s*-?\d{1,3}\.\d{3,}\s*", str(text or "")):
        return ""
    cleaned = re.sub(r"(?i)\b(?:lat(?:itude)?|lon(?:gitude)?|lng)\s*[:=]?\s*-?\d+(?:\.\d+)?", " ", text)
    cleaned = re.sub(r"\b-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}\b", " ", cleaned)
    return cleaned


def _normalize_record_list_sentence(text: str) -> str:
    direction_pattern = r"(?:N|S|E|W|NE|NW|SE|SW|N\.E\.|N\.W\.|S\.E\.|S\.W\.)"
    suffix_pattern = "|".join(sorted((re.escape(key) for key in _STREET_SUFFIX_WORDS), key=len, reverse=True))
    address_start = re.compile(
        rf"\b\d{{1,6}}\s+(?:(?:{direction_pattern})\s+)?(?:\d{{1,3}}(?:st|nd|rd|th)?|[A-Za-z][A-Za-z'.-]+)\s+(?:{suffix_pattern})\b",
        re.IGNORECASE,
    )

    def replace_record_list(match: re.Match[str]) -> str:
        listed = _strip_coordinates(match.group("listed"))
        if re.search(r"(?i)\b(?:not listed|not available|unavailable|not provided)\b", listed):
            return " "
        listed = re.sub(r"(?i)\b\d+\s*(?:minute|minutes|min|mins)\b\.?\s*", " ", listed)
        listed = re.sub(r"\s+", " ", listed).strip(" ;,.")
        address_match = address_start.search(listed)
        if address_match:
            listed = listed[address_match.start() :].strip(" ;,.")
        if not listed:
            return " "
        return f"The address is {listed}."

    return re.sub(
        r"(?i)\bThe record lists\s+(?P<listed>.*?)(?=\s+(?:Phone|Eligibility|Source|Confirm)\s*:| Confirm\b|$)",
        replace_record_list,
        text,
    )


def normalize_indextts_spoken_text(text: str) -> str:
    spoken = _strip_scraped_page_chrome(text)
    spoken = re.sub(r"\*\*(.*?)\*\*", r"\1", spoken)
    spoken = re.sub(r"__(.*?)__", r"\1", spoken)
    spoken = _strip_unspoken_fields(spoken)
    spoken = _strip_coordinates(spoken)
    spoken = _normalize_record_list_sentence(spoken)
    spoken = _normalize_urls_for_speech(spoken)
    spoken = _normalize_phone_numbers(spoken)
    spoken = _normalize_phone_extensions(spoken)
    spoken = _normalize_range_and_parenthetical_punctuation(spoken)
    spoken = _normalize_percentages_and_currency(spoken)
    spoken = _normalize_hours_and_separators(spoken)
    spoken = re.sub(r"\bST\s+(?=[A-Z])", "Saint ", spoken)
    spoken = re.sub(r"(?i)\ba grounded\s+211\s+match\s+is\b", "I found", spoken)
    spoken = re.sub(r"(?i)\ba grounded\s+two one one\s+match\s+is\b", "I found", spoken)
    spoken = re.sub(r"(?i)\bgrounded detail\b", "detail", spoken)
    spoken = re.sub(r"(?i)\b211[\s-]?ai\b", "two one one AI", spoken)
    spoken = re.sub(r"(?i)\b211[\s-]?info\b", "two one one info", spoken)
    spoken = re.sub(r"(?<!\d)9\s*-\s*1\s*-\s*1(?!\d)", "nine one one", spoken)
    spoken = re.sub(r"(?<!\d)2\s*-\s*1\s*-\s*1(?!\d)", "two one one", spoken)
    spoken = re.sub(r"(?<!\d)911(?!\d)", "nine one one", spoken)
    spoken = re.sub(r"(?<!\d)211(?!\d)", "two one one", spoken)
    spoken = re.sub(r"\b(?P<tens>\d)\s+(?P<ones>\d)(?P<suffix>st|nd|rd|th)\b", r"\g<tens>\g<ones>\g<suffix>", spoken, flags=re.IGNORECASE)

    direction_pattern = r"(?:N|S|E|W|NE|NW|SE|SW|N\.E\.|N\.W\.|S\.E\.|S\.W\.)"
    suffix_pattern = "|".join(sorted((re.escape(key) for key in _STREET_SUFFIX_WORDS), key=len, reverse=True))

    spoken = re.sub(
        rf"\b(?P<direction>{direction_pattern})\s+(?P<number>\d{{1,3}})(?:st|nd|rd|th)?\s+(?P<suffix>{suffix_pattern})\b",
        lambda match: (
            f"{_normalize_direction_token(match.group('direction'))} "
            f"{_ordinal_to_words(int(match.group('number')))} "
            f"{_normalize_suffix_token(match.group('suffix'))}"
        ),
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(
        rf"\b(?P<number>\d{{1,3}})(?:st|nd|rd|th)?\s+(?P<suffix>{suffix_pattern})\b",
        lambda match: f"{match.group('number')} {_normalize_suffix_token(match.group('suffix'))}"
        if match.group("suffix").lower().rstrip(".") in {"hwy", "highway"}
        else f"{_ordinal_to_words(int(match.group('number')))} {_normalize_suffix_token(match.group('suffix'))}",
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(
        rf"\b(?P<direction>{direction_pattern})\b(?=\s+\d)",
        lambda match: _normalize_direction_token(match.group("direction")),
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = _normalize_address_directions_and_highways(spoken)
    spoken = re.sub(
        rf"\b(?P<suffix>{suffix_pattern})\b",
        lambda match: match.group("suffix")
        if match.group("suffix").isupper()
        else _normalize_suffix_token(match.group("suffix")),
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(
        r"\b(?P<label>apt\.?|ste\.?|suite|unit|bldg\.?|fl\.?)\s+#?\s*(?P<unit>[A-Za-z0-9-]+)\b",
        lambda match: f"{_UNIT_WORDS.get(match.group('label').lower(), match.group('label'))} {match.group('unit')}",
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = re.sub(
        r"\b(?P<number>\d{1,3})(?:st|nd|rd|th)\b",
        lambda match: match.group(0)
        if re.search(r"(?:Suite|Room|Floor|Unit|Building|Apartment)\s+$", spoken[max(0, match.start() - 24) : match.start()], re.IGNORECASE)
        else _ordinal_to_words(int(match.group("number"))),
        spoken,
        flags=re.IGNORECASE,
    )
    spoken = _normalize_zip_codes(spoken)
    spoken = _normalize_sentence_prosody(spoken)
    spoken = re.sub(r"\s+([.,;:!?])", r"\1", spoken)
    spoken = re.sub(r"(?:\.\s*){2,}", ". ", spoken)
    spoken = re.sub(r"\s+", " ", spoken).strip(" ;,")
    return spoken.lstrip(".,; ")


def normalize_numeric_sequence(value: str) -> str:
    normalized = re.sub(r"(\d)[-](\d)", r"\1 \2", str(value or ""))
    normalized = re.sub(r"\b\d+\b", lambda match: _digits_to_words(match.group(0)), normalized)
    normalized = re.sub(r"\s*,\s*", ", ", normalized)
    normalized = re.sub(r"\s*;\s*", "; ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" ,;")


def normalize_slot_value_text(kind: str, value: str) -> str:
    raw_value = " ".join(str(value or "").split())
    if not raw_value:
        return ""

    digits_only = re.sub(r"\D", "", raw_value)
    spoken = raw_value
    normalized_kind = str(kind or "").strip().lower()

    if normalized_kind == "phone" and digits_only:
        if len(digits_only) == 11 and digits_only.startswith("1"):
            digits_only = digits_only[1:]
        if len(digits_only) == 10:
            spoken = f"{_digits_to_words(digits_only[:3])}, {_digits_to_words(digits_only[3:6])}, {_digits_to_words(digits_only[6:])}"
        else:
            spoken = normalize_numeric_sequence(raw_value)
    elif normalized_kind == "zip" and digits_only:
        if len(digits_only) == 9:
            spoken = f"{_digits_to_words(digits_only[:5])} dash {_digits_to_words(digits_only[5:])}"
        elif len(digits_only) == 5:
            spoken = _digits_to_words(digits_only)
        else:
            spoken = normalize_numeric_sequence(raw_value)
    elif normalized_kind == "number" and digits_only:
        if re.fullmatch(r"\d{1,4}", raw_value):
            spoken = _number_to_words(int(raw_value))
        else:
            spoken = normalize_numeric_sequence(raw_value)
    elif normalized_kind == "address":
        spoken = normalize_indextts_spoken_text(raw_value)
        spoken = re.sub(r"^\d{1,6}\b", lambda match: _digits_to_words(match.group(0)), spoken)
        return " ".join(spoken.split())
    elif re.search(r"\d", raw_value):
        spoken = normalize_numeric_sequence(raw_value)

    return " ".join(normalize_indextts_spoken_text(spoken).split())


def infer_slot_kinds_from_record(record: Mapping[str, Any]) -> list[str]:
    slot_kinds = {
        str(item or "").strip().lower()
        for item in (record.get("slotKinds") or [])
        if str(item or "").strip()
    }
    for source_id in record.get("sourceIds") or []:
        match = re.match(r"audio-slot::(?P<kind>[^:]+)::", str(source_id or "").strip())
        if match:
            slot_kinds.add(match.group("kind").strip().lower())
    preferred_order = ["phone", "zip", "number"]
    ordered = [kind for kind in preferred_order if kind in slot_kinds]
    ordered.extend(sorted(slot_kinds - set(ordered)))
    return ordered


def normalize_manifest_record_text(raw_text: str, record: Mapping[str, Any]) -> str:
    for slot_kind in infer_slot_kinds_from_record(record):
        normalized = normalize_slot_value_text(slot_kind, raw_text)
        if normalized:
            return normalized
    return normalize_indextts_spoken_text(raw_text)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _fallback_audio_is_structurally_valid(path: Path) -> bool:
    """Validate common local cache formats when ffprobe is unavailable."""

    if path.suffix.casefold() == ".wav":
        try:
            with wave.open(str(path), "rb") as audio:
                frame_count = audio.getnframes()
                expected_bytes = frame_count * audio.getnchannels() * audio.getsampwidth()
                return (
                    audio.getnchannels() > 0
                    and audio.getsampwidth() > 0
                    and audio.getframerate() > 0
                    and frame_count > 0
                    and len(audio.readframes(frame_count)) == expected_bytes
                )
        except (EOFError, OSError, wave.Error):
            return False

    ffmpeg = shutil.which("ffmpeg")
    if path.suffix.casefold() != ".mp3" or not ffmpeg:
        return False
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-i",
                str(path),
                "-f",
                "null",
                "-",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def local_audio_is_structurally_valid(path: Path) -> bool:
    """Return whether a local WAV/MP3 contains a decodable audio stream."""

    if not path.is_file() or file_size(path) <= 0:
        return False

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            completed = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-count_frames",
                    "-show_entries",
                    "stream=codec_type,codec_name,channels,sample_rate,nb_read_frames",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            payload = json.loads(completed.stdout) if completed.returncode == 0 else {}
            streams = payload.get("streams") if isinstance(payload, Mapping) else None
            valid = bool(
                isinstance(streams, list)
                and any(
                    isinstance(stream, Mapping)
                    and str(stream.get("codec_type") or "").casefold() == "audio"
                    and str(stream.get("codec_name") or "").strip()
                    and int(stream.get("channels") or 0) > 0
                    and int(stream.get("sample_rate") or 0) > 0
                    and int(stream.get("nb_read_frames") or 0) > 0
                    for stream in streams
                )
            )
        except (json.JSONDecodeError, OSError, subprocess.SubprocessError, TypeError, ValueError):
            valid = False
    else:
        valid = _fallback_audio_is_structurally_valid(path)

    return valid


def discard_invalid_local_audio_cache(path: Path) -> bool:
    """Remove an invalid final cache file so its response is regenerated."""

    if not path.exists() or local_audio_is_structurally_valid(path):
        return False
    path.unlink(missing_ok=True)
    return True


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory sync after an atomic media publication."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        # Some filesystems do not support directory fsync.
        pass
    finally:
        os.close(descriptor)


def _replacement_mode(path: Path) -> int:
    try:
        return path.stat().st_mode & 0o777
    except OSError:
        return 0o644


def indextts_max_trailing_silence_ms() -> int | None:
    """Return the configured TTS tail limit, or ``None`` when disabled."""

    raw = os.environ.get(
        "WALLET_INDEXTTS_MAX_TRAILING_SILENCE_MS",
        str(DEFAULT_INDEXTTS_MAX_TRAILING_SILENCE_MS),
    ).strip()
    if raw.casefold() in {"none", "off", "disabled"}:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            "WALLET_INDEXTTS_MAX_TRAILING_SILENCE_MS must be a "
            "non-negative integer or one of: none, off, disabled"
        ) from exc
    if value < 0:
        raise RuntimeError(
            "WALLET_INDEXTTS_MAX_TRAILING_SILENCE_MS must be non-negative"
        )
    return value


def validate_indextts_generated_audio(path: Path, content: bytes) -> dict[str, int]:
    """Apply package-owned TTS quality gates before local publication."""

    if (
        VoiceArtifactPolicy is None
        or validate_generated_audio_bytes is None
    ):
        raise RuntimeError(
            "ipfs_accelerate_py generated-audio validation is unavailable"
        ) from _VOICE_AUDIO_VALIDATOR_IMPORT_ERROR
    media_type = mimetypes.guess_type(path.name)[0] or "audio/wav"
    return validate_generated_audio_bytes(
        content,
        media_type=media_type,
        uri=path.name,
        policy=VoiceArtifactPolicy(
            max_tts_trailing_silence_ms=indextts_max_trailing_silence_ms(),
        ),
    )


def validate_indextts_bucket_audio(
    backend: HFBucketBackend,
    remote_path: str,
) -> dict[str, int]:
    """Download and validate one remote artifact before trusting its cache hit."""

    content = backend.get_file(remote_path)
    parsed_path = urllib_parse.urlsplit(str(remote_path)).path
    return validate_indextts_generated_audio(
        Path(parsed_path or str(remote_path)),
        content,
    )


def discard_unacceptable_local_audio_cache(path: Path) -> bool:
    """Discard structurally invalid or quality-rejected local TTS cache data."""

    if discard_invalid_local_audio_cache(path):
        return True
    if not path.exists():
        return False
    try:
        validate_indextts_generated_audio(path, path.read_bytes())
    except Exception as exc:
        if not is_indextts_audio_validation_error(exc):
            raise
        path.unlink(missing_ok=True)
        return True
    return False


def write_audio_bytes_atomic(path: Path, content: bytes) -> None:
    """Validate and atomically publish one generated local audio file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=path.suffix,
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    mode = _replacement_mode(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            os.fchmod(handle.fileno(), mode)
            handle.flush()
            os.fsync(handle.fileno())
        if not local_audio_is_structurally_valid(temporary_path):
            raise RuntimeError(f"IndexTTS returned invalid audio for {path.name}")
        validate_indextts_generated_audio(path, content)
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def audio_url_for(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    return f"/assets/audio/precomputed/211-dag-indextts/{path.name}"


def hf_bucket_backend(bucket_uri: str) -> HFBucketBackend:
    return HFBucketBackend(bucket_uri)


def bucket_audio_uris(bucket_uri: str, response_id: str) -> dict[str, str]:
    targets = bucket_sync_targets(bucket_uri)
    if not targets:
        return {}
    base_audio_uri = str(targets["audioUri"]).rstrip("/")
    normalized_response_id = str(response_id or "").strip()
    if not normalized_response_id:
        return {}
    return {
        "bucketAudioUri": f"{base_audio_uri}/{normalized_response_id}.wav",
        "bucketMp3Uri": f"{base_audio_uri}/{normalized_response_id}.mp3",
    }


def attach_bucket_audio_uris(entry: dict[str, Any], bucket_uri: str, *, prefer_mp3: bool) -> dict[str, Any]:
    uris = bucket_audio_uris(bucket_uri, str(entry.get("id") or ""))
    if not uris:
        return entry
    entry.update(uris)
    preferred_bucket_uri = uris["bucketMp3Uri"] if prefer_mp3 else uris["bucketAudioUri"]
    entry["preferredBucketAudioUri"] = preferred_bucket_uri
    return entry


def cached_bucket_audio_entry(
    item: Mapping[str, Any],
    *,
    bucket_uri: str,
    prefer_mp3: bool,
) -> dict[str, Any] | None:
    uris = bucket_audio_uris(bucket_uri, str(item.get("id") or ""))
    if not uris:
        return None
    backend = hf_bucket_backend(bucket_uri)
    mp3_exists = backend.exists(f"audio/{item['id']}.mp3")
    if mp3_exists:
        try:
            validate_indextts_bucket_audio(
                backend,
                f"audio/{item['id']}.mp3",
            )
        except Exception as exc:
            if not is_indextts_audio_validation_error(exc):
                raise
            mp3_exists = False
    wav_exists = backend.exists(f"audio/{item['id']}.wav") if (not mp3_exists or not prefer_mp3) else False
    if wav_exists:
        try:
            validate_indextts_bucket_audio(
                backend,
                f"audio/{item['id']}.wav",
            )
        except Exception as exc:
            if not is_indextts_audio_validation_error(exc):
                raise
            wav_exists = False
    if prefer_mp3 and mp3_exists:
        entry = {
            **item,
            "status": "cached_bucket_mp3",
            "audioPath": "",
            "mimeType": "",
            "audioBytes": 0,
            "mp3Path": "",
            "mp3MimeType": "audio/mpeg",
            "mp3Bytes": 0,
            "preferredAudioPath": uris["bucketMp3Uri"],
            "preferredMimeType": "audio/mpeg",
            "wavDeprecated": True,
        }
        return attach_bucket_audio_uris(entry, bucket_uri, prefer_mp3=prefer_mp3)
    if wav_exists:
        entry = {
            **item,
            "status": "cached_bucket",
            "audioPath": "",
            "mimeType": "",
            "audioBytes": 0,
            "mp3Path": "",
            "preferredAudioPath": uris["bucketAudioUri"],
            "preferredMimeType": "audio/wav",
            "wavDeprecated": False,
        }
        return attach_bucket_audio_uris(entry, bucket_uri, prefer_mp3=prefer_mp3)
    return None


def resolve_repo_path(path_text: str) -> Path:
    path = Path(str(path_text or "").strip())
    if path.is_absolute():
        return path
    return REPO_ROOT / path


_WHISPER_MODELS: dict[tuple[str, str], Any] = {}


def prefer_system_torch_installation() -> None:
    user_site = Path.home() / ".local" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    system_site = Path("/usr/local/lib") / f"python{sys.version_info.major}.{sys.version_info.minor}" / "dist-packages"
    user_torch_global_deps = user_site / "torch" / "lib" / "libtorch_global_deps.so"
    system_torch_global_deps = system_site / "torch" / "lib" / "libtorch_global_deps.so"
    if user_torch_global_deps.exists() or not system_torch_global_deps.exists():
        return

    loaded_torch = sys.modules.get("torch")
    loaded_torch_file = Path(str(getattr(loaded_torch, "__file__", "") or "")).resolve() if loaded_torch is not None else None
    if loaded_torch_file is not None and system_site in loaded_torch_file.parents:
        return

    user_site_text = str(user_site)
    system_site_text = str(system_site)
    if system_site_text in sys.path:
        sys.path.remove(system_site_text)
    if user_site_text in sys.path:
        insert_at = sys.path.index(user_site_text)
        sys.path.insert(insert_at, system_site_text)
    else:
        sys.path.insert(0, system_site_text)

    for module_name in list(sys.modules):
        if module_name == "torch" or module_name.startswith("torch."):
            sys.modules.pop(module_name, None)


def whisper_cuda_available() -> bool:
    prefer_system_torch_installation()
    try:
        import torch  # type: ignore
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def resolve_whisper_device(requested_device: str) -> str:
    normalized = str(requested_device or "auto").strip().lower()
    if normalized in {"", "auto"}:
        return "cuda" if whisper_cuda_available() else "cpu"
    if normalized == "cuda" and not whisper_cuda_available():
        raise RuntimeError("Transcript validation requested CUDA, but torch.cuda.is_available() is false on this host.")
    if normalized not in {"cpu", "cuda"}:
        raise ValueError(f"Unsupported transcript validation device: {requested_device}")
    return normalized


def load_whisper_model(model_name: str, *, device: str) -> Any:
    cache_key = (device, model_name)
    model = _WHISPER_MODELS.get(cache_key)
    if model is not None:
        return model

    prefer_system_torch_installation()
    try:
        import whisper  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Transcript validation requires the 'whisper' package. Install it with 'python3 -m pip install openai-whisper'."
        ) from exc

    model = whisper.load_model(model_name, device=device)
    _WHISPER_MODELS[cache_key] = model
    return model


def transcribe_audio_file(audio_path: Path, *, model_name: str, language: str, device: str) -> tuple[str, str, bool]:
    resolved_device = resolve_whisper_device(device)
    model = load_whisper_model(model_name, device=resolved_device)
    use_fp16 = resolved_device == "cuda"
    result = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        fp16=use_fp16,
        verbose=False,
        condition_on_previous_text=False,
    )
    return " ".join(str(result.get("text") or "").split()), resolved_device, use_fp16


def normalize_transcript_comparison_text(text: str, record: Mapping[str, Any]) -> str:
    normalized = normalize_manifest_record_text(text, record).lower()
    normalized = re.sub(r"\band\b", " ", normalized)
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def validate_audio_manifest_entries(
    entries: list[dict[str, Any]],
    *,
    limit: int,
    model_name: str,
    language: str,
    device: str,
    similarity_threshold: float,
) -> dict[str, Any]:
    validated_count = 0
    failures: list[dict[str, Any]] = []

    for entry in entries:
        if validated_count >= limit:
            break
        preferred_path_text = str(entry.get("preferredAudioPath") or entry.get("mp3Path") or entry.get("audioPath") or "").strip()
        if not preferred_path_text:
            continue
        audio_path = resolve_repo_path(preferred_path_text)
        if not audio_path.exists():
            continue

        expected_text = normalize_transcript_comparison_text(str(entry.get("text") or ""), entry)
        transcript_text, resolved_device, use_fp16 = transcribe_audio_file(
            audio_path,
            model_name=model_name,
            language=language,
            device=device,
        )
        normalized_transcript = normalize_transcript_comparison_text(transcript_text, entry)
        similarity = round(difflib.SequenceMatcher(None, expected_text, normalized_transcript).ratio(), 4)
        passed = similarity >= similarity_threshold
        validation_payload = {
            "model": model_name,
            "language": language,
            "device": resolved_device,
            "fp16": use_fp16,
            "audioPath": display_path(audio_path),
            "transcript": transcript_text,
            "normalizedTranscript": normalized_transcript,
            "normalizedExpectedText": expected_text,
            "similarity": similarity,
            "threshold": similarity_threshold,
            "passed": passed,
        }
        entry["transcriptValidation"] = validation_payload
        validated_count += 1

        print(
            f"transcript validation [{validated_count}/{limit}] {entry.get('id', 'unknown')}: "
            f"{'pass' if passed else 'FAIL'} device={resolved_device} fp16={use_fp16} "
            f"similarity={similarity:.4f} transcript={transcript_text!r}"
        )
        if not passed:
            failures.append({
                "id": entry.get("id", "unknown"),
                "audioPath": display_path(audio_path),
                "expected": expected_text,
                "transcript": transcript_text,
                "normalizedTranscript": normalized_transcript,
                "similarity": similarity,
            })

    if limit > 0 and validated_count == 0:
        raise RuntimeError("Transcript validation was requested, but no generated or cached audio files were available to validate.")

    return {
        "enabled": True,
        "validatedCount": validated_count,
        "failureCount": len(failures),
        "model": model_name,
        "language": language,
        "device": resolve_whisper_device(device),
        "similarityThreshold": similarity_threshold,
        "failures": failures,
    }


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path, *, bitrate: str = "64k", force: bool = False) -> None:
    if (
        mp3_path.exists()
        and not force
        and mp3_path.stat().st_mtime >= wav_path.stat().st_mtime
        and local_audio_is_structurally_valid(mp3_path)
    ):
        return
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{mp3_path.stem}.",
        suffix=mp3_path.suffix,
        dir=mp3_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    mode = _replacement_mode(mp3_path)
    try:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            str(temporary_path),
        ]
        subprocess.run(command, check=True)
        temporary_path.chmod(mode)
        with temporary_path.open("rb") as handle:
            os.fsync(handle.fileno())
        if not local_audio_is_structurally_valid(temporary_path):
            raise RuntimeError(f"ffmpeg produced invalid MP3 audio for {mp3_path.name}")
        os.replace(temporary_path, mp3_path)
        _fsync_directory(mp3_path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def maybe_delete_wav(wav_path: Path, mp3_path: Path, *, delete_wav: bool) -> bool:
    if not delete_wav:
        return False
    if not mp3_path.exists() or mp3_path.stat().st_size <= 0:
        return False
    wav_path.unlink(missing_ok=True)
    return True


def load_resolve_secret() -> Any:
    global _RESOLVE_SECRET
    if _RESOLVE_SECRET is not None:
        return _RESOLVE_SECRET
    if not IPFS_DATASETS_SECRETS_MODULE.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "ipfs_datasets_py_utils_secrets",
            IPFS_DATASETS_SECRETS_MODULE,
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        resolve_secret = getattr(module, "resolve_secret", None)
        if callable(resolve_secret):
            _RESOLVE_SECRET = resolve_secret
            return resolve_secret
    except Exception:
        return None
    return None


def load_secret_env() -> None:
    """Best-effort load HF token/billing env from ~/.ipfs_datasets/secrets.json."""
    resolve_secret = load_resolve_secret()
    if resolve_secret and not current_huggingface_token():
        token = (
            resolve_secret(
                "WALLET_INDEXTTS_HF_TOKEN",
                "HF_TOKEN",
                "HUGGINGFACEHUB_API_TOKEN",
                "IPFS_DATASETS_PY_HF_API_TOKEN",
                "HUGGINGFACE_API_TOKEN",
                "HUGGINGFACE_HUB_TOKEN",
            )
            or ""
        ).strip()
        if token and not os.getenv("HF_TOKEN"):
            os.environ["HF_TOKEN"] = token

    if not current_huggingface_token():
        try:
            from huggingface_hub import get_token

            cached_token = str(get_token() or "").strip()
        except Exception:
            cached_token = ""
        if cached_token:
            os.environ["HF_TOKEN"] = cached_token

    path = Path(os.path.expanduser("~/.ipfs_datasets/secrets.json"))
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        billing = data.get("billing") if isinstance(data, Mapping) else None
        if isinstance(billing, Mapping):
            for key in ("WALLET_INDEXTTS_HF_BILL_TO", "IPFS_DATASETS_PY_HF_BILL_TO"):
                value = billing.get(key)
                if value and not os.getenv(key):
                    os.environ[key] = str(value)


def indextts_base_url() -> str:
    return os.getenv("WALLET_INDEXTTS_SPACE_URL", DEFAULT_INDEXTTS_SPACE_URL).strip().rstrip("/")


def indextts_model_name() -> str:
    return os.getenv("WALLET_INDEXTTS_MODEL_NAME", DEFAULT_INDEXTTS_MODEL_NAME).strip() or DEFAULT_INDEXTTS_MODEL_NAME


def current_huggingface_token() -> str:
    for name in INDEXTTS_TOKEN_ENV_NAMES:
        token = str(os.getenv(name) or "").strip()
        if token:
            return token
    return ""


def indextts_timeout() -> float:
    try:
        return max(30.0, float(os.getenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "900")))
    except ValueError:
        return 900.0


def indextts_headers(*, accept: str = "application/json") -> dict[str, str]:
    load_secret_env()
    headers = {
        "Accept": accept,
        "User-Agent": "211-ai-indextts-precompute/1.0",
    }
    token = current_huggingface_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    bill_to = os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus"
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    return headers


def describe_indextts_auth() -> str:
    headers = indextts_headers()
    auth = headers.get("Authorization", "")
    bill_to = headers.get("X-HF-Bill-To", "")
    return f"hf_auth={'yes' if auth.startswith('Bearer ') else 'no'} hf_token_chars={max(0, len(auth) - len('Bearer '))} hf_bill_to={bill_to or 'unset'}"


_INDEXTTS_SPACE_CLIENT: HFSpaceClient | None = None
_INDEXTTS_SPACE_CLIENT_KEY = ""


def indextts_space_client() -> HFSpaceClient:
    global _INDEXTTS_SPACE_CLIENT
    global _INDEXTTS_SPACE_CLIENT_KEY
    load_secret_env()
    cache_key = "|".join(
        (
            indextts_base_url(),
            str(indextts_timeout()),
            current_huggingface_token(),
            str(os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus"),
        )
    )
    if _INDEXTTS_SPACE_CLIENT is not None and cache_key == _INDEXTTS_SPACE_CLIENT_KEY:
        return _INDEXTTS_SPACE_CLIENT
    _INDEXTTS_SPACE_CLIENT = HFSpaceClient(
        indextts_base_url(),
        timeout_seconds=indextts_timeout(),
        headers_factory=lambda: indextts_headers(),
    )
    _INDEXTTS_SPACE_CLIENT_KEY = cache_key
    return _INDEXTTS_SPACE_CLIENT


def bucket_sync_targets(bucket_uri: str) -> dict[str, str]:
    base = str(bucket_uri or "").strip().rstrip("/")
    if not base:
        return {}
    return {
        "bucketUri": base,
        "audioUri": f"{base}/audio",
        "metadataUri": f"{base}/metadata",
    }


def hf_cli_executable() -> str:
    configured = str(os.getenv("HF_CLI_BIN") or "hf").strip() or "hf"
    if os.path.sep in configured:
        if not Path(configured).exists():
            raise RuntimeError(f"HF CLI executable was not found at {configured}")
        return configured
    resolved = shutil.which(configured)
    if not resolved:
        raise RuntimeError("HF CLI executable was not found on PATH. Install it or set HF_CLI_BIN.")
    return resolved


def run_hf_sync(local_path: Path, remote_uri: str) -> dict[str, str]:
    load_secret_env()
    command = [hf_cli_executable(), "sync", str(local_path), str(remote_uri)]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"hf sync failed for {display_path(local_path)} -> {remote_uri}: {output or 'unknown error'}")
    return {
        "localPath": display_path(local_path),
        "remoteUri": str(remote_uri),
        **({"output": output} if output else {}),
    }


def sync_generated_outputs_to_bucket(
    output_dir: Path,
    manifest_path: Path,
    public_manifest_path: Path,
    bucket_uri: str,
) -> dict[str, Any]:
    targets = bucket_sync_targets(bucket_uri)
    if not targets:
        return {}
    if not output_dir.exists():
        raise FileNotFoundError(output_dir)
    with tempfile.TemporaryDirectory(prefix="abby-tts-bucket-sync-") as tmpdir:
        metadata_dir = Path(tmpdir) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, metadata_dir / manifest_path.name)
        shutil.copy2(public_manifest_path, metadata_dir / public_manifest_path.name)
        audio_sync = run_hf_sync(output_dir, targets["audioUri"])
        metadata_sync = run_hf_sync(metadata_dir, targets["metadataUri"])
    return {
        **targets,
        "audioSync": audio_sync,
        "metadataSync": metadata_sync,
    }


def http_json(method: str, url: str, payload: Any | None = None) -> Any:
    base_url = indextts_base_url().rstrip("/")
    if str(url).startswith(base_url):
        path = str(url)[len(base_url) :].lstrip("/")
        return indextts_space_client().request_json(method, path, payload)
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = indextts_headers()
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=indextts_timeout()) as response:
        return json.loads(response.read().decode("utf-8"))


def upload_reference(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    safe_name = path.name or "abby-reference.wav"
    mime_type = mimetypes.guess_type(str(path))[0] or "audio/wav"
    parsed = indextts_space_client().upload_file(safe_name, data, mime_type)
    upload_path = first_upload_path(parsed)
    if not upload_path:
        raise RuntimeError("IndexTTS upload did not return a reference path")
    return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": safe_name}


def first_upload_path(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            found = first_upload_path(item)
            if found:
                return found
    if isinstance(value, Mapping):
        for key in ("path", "name"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            found = first_upload_path(item)
            if found:
                return found
    return ""


def indextts_config() -> dict[str, Any]:
    config = indextts_space_client().get_config()
    return dict(config)


def indextts_fn_index(config: Mapping[str, Any]) -> int:
    api_name = os.getenv("WALLET_INDEXTTS_API_NAME", "/gen_single")
    try:
        return int(
            indextts_space_client().resolve_fn_index(
                api_name,
                config,
                fallback_markers=("tts", "synth", "generate", "infer", "predict"),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"IndexTTS api_name {api_name!r} was not found") from exc


def indextts_batch_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", "/gen_batch").strip()


def indextts_batch_upload_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_BATCH_UPLOAD_API_NAME", "/gen_batch_with_upload").strip()


def indextts_upload_generated_results_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_UPLOAD_RESULTS_API_NAME", "/upload_generated_results").strip()


def indextts_auto_upload_generated_results_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_AUTO_UPLOAD_RESULTS_API_NAME", "/maybe_auto_upload_generated_results").strip()


def lookup_dependency_id_by_api_name(config: Mapping[str, Any], api_name: str) -> int | None:
    try:
        return int(indextts_space_client().resolve_fn_index(api_name, config))
    except Exception:
        return None


def lookup_dependency_input_count(config: Mapping[str, Any], dependency_id: int) -> int | None:
    return indextts_space_client().lookup_dependency_input_count(int(dependency_id), config)


def dependency_api_names(config: Mapping[str, Any]) -> list[str]:
    return indextts_space_client().dependency_api_names(config)


def indextts_contract_name(input_count: int | None) -> str:
    if input_count is None:
        return "unknown"
    if input_count >= 25:
        return "segments-bucket-25-field"
    if input_count == 24:
        return "legacy-24-field"
    return f"{input_count}-field"


def indextts_contract_summary(config: Mapping[str, Any], single_fn_index: int | None = None) -> dict[str, Any]:
    resolved_single_fn_index = int(single_fn_index if single_fn_index is not None else indextts_fn_index(config))
    single_input_count = lookup_dependency_input_count(config, resolved_single_fn_index)
    batch_api_name = indextts_batch_api_name()
    batch_fn_index = lookup_dependency_id_by_api_name(config, batch_api_name)
    batch_input_count = lookup_dependency_input_count(config, batch_fn_index) if batch_fn_index is not None else None
    batch_upload_api_name = indextts_batch_upload_api_name()
    batch_upload_fn_index = lookup_dependency_id_by_api_name(config, batch_upload_api_name)
    batch_upload_input_count = (
        lookup_dependency_input_count(config, batch_upload_fn_index)
        if batch_upload_fn_index is not None
        else None
    )
    upload_results_api_name = indextts_upload_generated_results_api_name()
    upload_results_fn_index = lookup_dependency_id_by_api_name(config, upload_results_api_name)
    auto_upload_results_api_name = indextts_auto_upload_generated_results_api_name()
    auto_upload_results_fn_index = lookup_dependency_id_by_api_name(config, auto_upload_results_api_name)
    remote_bucket_pipeline_ready = bool(
        batch_upload_fn_index is not None
        and (upload_results_fn_index is not None or auto_upload_results_fn_index is not None)
    )
    summary: dict[str, Any] = {
        "singleApiName": os.getenv("WALLET_INDEXTTS_API_NAME", "/gen_single").strip() or "/gen_single",
        "singleFnIndex": resolved_single_fn_index,
        "singleInputCount": single_input_count,
        "singleContract": indextts_contract_name(single_input_count),
        "batchApiName": batch_api_name,
        "batchRegistered": batch_fn_index is not None,
        "batchFnIndex": batch_fn_index,
        "batchInputCount": batch_input_count,
        "batchContract": indextts_contract_name(batch_input_count),
        "batchUploadApiName": batch_upload_api_name,
        "batchUploadRegistered": batch_upload_fn_index is not None,
        "batchUploadFnIndex": batch_upload_fn_index,
        "batchUploadInputCount": batch_upload_input_count,
        "uploadResultsApiName": upload_results_api_name,
        "uploadResultsRegistered": upload_results_fn_index is not None,
        "uploadResultsFnIndex": upload_results_fn_index,
        "autoUploadResultsApiName": auto_upload_results_api_name,
        "autoUploadResultsRegistered": auto_upload_results_fn_index is not None,
        "autoUploadResultsFnIndex": auto_upload_results_fn_index,
        "remoteBucketPipelineReady": remote_bucket_pipeline_ready,
        "registeredApiNames": dependency_api_names(config),
    }
    if batch_fn_index is None:
        summary["recommendedMode"] = "parallel-gen-single"
        summary["deploymentDriftReason"] = (
            f"Configured batch api_name {batch_api_name!r} is not registered by the live Space dependencies"
        )
    elif not remote_bucket_pipeline_ready:
        summary["recommendedMode"] = "gen_batch-local-sync-fallback"
        summary["deploymentDriftReason"] = (
            "The live Space exposes batch synthesis but not the upload-capable batch pipeline "
            f"({batch_upload_api_name!r} plus {upload_results_api_name!r} or {auto_upload_results_api_name!r})"
        )
    else:
        summary["recommendedMode"] = "gen_batch_with_upload"
    return summary


def probe_indextts_endpoint_contract(
    *,
    client: Any | None = None,
    config: Mapping[str, Any] | None = None,
    expected_api_name: str = "/gen_single",
    expected_fn_index: int = 6,
    expected_input_count: int = 25,
    expected_batch_api_name: str = "/gen_batch",
    expected_batch_fn_index: int = 7,
    expected_batch_input_count: int = 25,
    require_batch_match: bool = True,
    require_match: bool = True,
) -> dict[str, Any]:
    """Return a canonical receipt for a read-only IndexTTS config probe.

    Only ``get_config`` is invoked.  The receipt contains a digest of the
    public config instead of the config or headers themselves, and exact API
    name, function index, and input arity drift is rejected by default.
    """

    if (
        isinstance(expected_fn_index, bool)
        or not isinstance(expected_fn_index, int)
        or expected_fn_index < 0
    ):
        raise ValueError("expected_fn_index must be a non-negative integer")
    if (
        isinstance(expected_input_count, bool)
        or not isinstance(expected_input_count, int)
        or expected_input_count <= 0
    ):
        raise ValueError("expected_input_count must be a positive integer")
    if (
        isinstance(expected_batch_fn_index, bool)
        or not isinstance(expected_batch_fn_index, int)
        or expected_batch_fn_index < 0
    ):
        raise ValueError("expected_batch_fn_index must be a non-negative integer")
    if (
        isinstance(expected_batch_input_count, bool)
        or not isinstance(expected_batch_input_count, int)
        or expected_batch_input_count <= 0
    ):
        raise ValueError("expected_batch_input_count must be a positive integer")
    normalized_expected_api = "/" + str(expected_api_name or "").strip().lstrip("/")
    if normalized_expected_api == "/":
        raise ValueError("expected_api_name is required")
    normalized_expected_batch_api = "/" + str(expected_batch_api_name or "").strip().lstrip("/")
    if normalized_expected_batch_api == "/":
        raise ValueError("expected_batch_api_name is required")

    active_client = client
    if config is None:
        active_client = active_client or indextts_space_client()
        observed_config = active_client.get_config()
    else:
        observed_config = config
    if not isinstance(observed_config, Mapping):
        raise ValueError("IndexTTS config probe did not return a mapping")

    dependencies = observed_config.get("dependencies")
    if not isinstance(dependencies, list):
        dependencies = []
    observed_dependency: Mapping[str, Any] | None = None
    observed_batch_dependency: Mapping[str, Any] | None = None
    registered_api_names: list[str] = []
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            continue
        raw_api_name = dependency.get("api_name")
        if not isinstance(raw_api_name, str) or not raw_api_name.strip():
            continue
        api_name = "/" + raw_api_name.strip().lstrip("/")
        registered_api_names.append(api_name)
        if api_name == normalized_expected_api:
            observed_dependency = dependency
        if api_name == normalized_expected_batch_api:
            observed_batch_dependency = dependency

    observed_fn_index: int | None = None
    observed_input_count: int | None = None
    if observed_dependency is not None:
        raw_id = observed_dependency.get("id")
        if isinstance(raw_id, int) and not isinstance(raw_id, bool):
            observed_fn_index = raw_id
        elif isinstance(raw_id, str) and raw_id.strip().isdigit():
            observed_fn_index = int(raw_id.strip())
        inputs = observed_dependency.get("inputs")
        if isinstance(inputs, list):
            observed_input_count = len(inputs)

    observed_batch_fn_index: int | None = None
    observed_batch_input_count: int | None = None
    if observed_batch_dependency is not None:
        raw_batch_id = observed_batch_dependency.get("id")
        if isinstance(raw_batch_id, int) and not isinstance(raw_batch_id, bool):
            observed_batch_fn_index = raw_batch_id
        elif isinstance(raw_batch_id, str) and raw_batch_id.strip().isdigit():
            observed_batch_fn_index = int(raw_batch_id.strip())
        batch_inputs = observed_batch_dependency.get("inputs")
        if isinstance(batch_inputs, list):
            observed_batch_input_count = len(batch_inputs)

    drift_reasons: list[str] = []
    if observed_dependency is None:
        drift_reasons.append("api_name_not_registered")
    if observed_fn_index != expected_fn_index:
        drift_reasons.append("function_index_mismatch")
    if observed_input_count != expected_input_count:
        drift_reasons.append("input_count_mismatch")
    if require_batch_match:
        if observed_batch_dependency is None:
            drift_reasons.append("batch_api_name_not_registered")
        if observed_batch_fn_index != expected_batch_fn_index:
            drift_reasons.append("batch_function_index_mismatch")
        if observed_batch_input_count != expected_batch_input_count:
            drift_reasons.append("batch_input_count_mismatch")

    api_names = sorted(set(registered_api_names))
    batch_registered = "/gen_batch" in api_names
    batch_upload_registered = "/gen_batch_with_upload" in api_names
    result_upload_registered = any(
        name in api_names
        for name in (
            "/upload_generated_results",
            "/maybe_auto_upload_generated_results",
        )
    )
    if batch_upload_registered and result_upload_registered:
        recommended_mode = "gen_batch_with_upload"
    elif batch_registered:
        recommended_mode = "gen_batch-local-sync-fallback"
    else:
        recommended_mode = "parallel-gen-single"

    canonical_config = json.dumps(
        observed_config,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    endpoint_url = str(
        getattr(active_client, "space_url", "") if active_client is not None else ""
    ).strip().rstrip("/") or str(
        indextts_base_url()
    ).strip().rstrip("/")
    identity = {
        "api_name": normalized_expected_api,
        "config_sha256": hashlib.sha256(canonical_config).hexdigest(),
        "endpoint_url": endpoint_url,
        "function_index": observed_fn_index,
        "generation_request_count": 0,
        "input_count": observed_input_count,
        "read_only": True,
        "recommended_mode": recommended_mode,
        "schema_version": "abby_voice_endpoint_contract_probe_v1",
        "upload_request_count": 0,
    }
    contract_id = (
        "abby-voice-endpoint-contract:sha256:"
        + hashlib.sha256(
            json.dumps(
                identity,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )
    receipt = {
        **identity,
        "batch_api_name": normalized_expected_batch_api,
        "batch_function_index": observed_batch_fn_index,
        "batch_input_count": observed_batch_input_count,
        "compatible": not drift_reasons,
        "contract_id": contract_id,
        "drift_reasons": drift_reasons,
        "expected": {
            "api_name": normalized_expected_api,
            "function_index": expected_fn_index,
            "input_count": expected_input_count,
            "batch_api_name": normalized_expected_batch_api,
            "batch_function_index": expected_batch_fn_index,
            "batch_input_count": expected_batch_input_count,
            "require_batch_match": require_batch_match,
        },
        "probe_method": "GET config",
        "registered_api_names": api_names,
    }
    if require_match and drift_reasons:
        raise RuntimeError(
            "IndexTTS endpoint contract drift: " + ", ".join(drift_reasons)
        )
    return receipt


def build_canary_dispatch_manifest(
    regeneration_plan: Any,
    endpoint_contract: Mapping[str, Any],
    *,
    max_items: int = 12,
    max_attempts_per_item: int = 2,
    max_provider_requests: int | None = None,
    cost_microusd_per_request: int = 1,
    max_cost_microusd: int | None = None,
) -> dict[str, Any]:
    """Adapt a package regeneration plan to its canonical canary manifest.

    This thin wrapper never constructs a provider or queue.  Canonical TTS task
    IDs, workset lineage, ordering, limits, and manifest identity are all owned
    by the two packages rather than duplicated in this CLI.
    """

    from ipfs_accelerate_py.voice_jobs.regeneration import (
        RegenerationEndpointContract,
        RegenerationRunnerPolicy,
    )
    from ipfs_datasets_py.voice.regeneration import AbbyVoiceRegenerationPlan

    if not isinstance(regeneration_plan, AbbyVoiceRegenerationPlan):
        raise TypeError("regeneration_plan must be AbbyVoiceRegenerationPlan")
    request_bound = (
        max_items * max_attempts_per_item
        if max_provider_requests is None
        else max_provider_requests
    )
    cost_bound = (
        request_bound * cost_microusd_per_request
        if max_cost_microusd is None
        else max_cost_microusd
    )
    if endpoint_contract.get("compatible") is not True:
        raise ValueError("canary requires a compatible endpoint contract receipt")
    contract = RegenerationEndpointContract.from_mapping(endpoint_contract)
    policy = RegenerationRunnerPolicy(
        max_items=max_items,
        max_attempts_per_item=max_attempts_per_item,
        max_provider_requests=request_bound,
        cost_microusd_per_request=cost_microusd_per_request,
        max_cost_microusd=cost_bound,
    )
    manifest = regeneration_plan.canary_dispatch_manifest(
        endpoint_contract=contract,
        size=max_items,
        runner_policy=policy,
    )
    return manifest.to_dict()


def ensure_upload_capable_batch_contract(config: Mapping[str, Any], single_fn_index: int | None = None) -> dict[str, Any]:
    summary = indextts_contract_summary(config, single_fn_index)
    if summary.get("remoteBucketPipelineReady"):
        return summary
    raise RuntimeError(str(summary.get("deploymentDriftReason") or "IndexTTS remote bucket pipeline is not available"))


def indextts_batch_available(config: Mapping[str, Any]) -> bool:
    return lookup_dependency_id_by_api_name(config, indextts_batch_api_name()) is not None


def indextts_batch_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_BATCH_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    api_name = indextts_batch_api_name()
    value = lookup_dependency_id_by_api_name(config, api_name)
    if value is not None:
        return value
    raise RuntimeError(f"IndexTTS batch api_name {api_name!r} was not found")


def request_data(
    text: str,
    reference_audio: Mapping[str, Any],
    voice_description: str,
    *,
    input_count: int | None = None,
) -> list[Any]:
    data = [
        "Same as the voice reference",
        reference_audio,
        text,
        None,
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        voice_description,
        False,
        120,
    ]
    if input_count is None:
        input_count = 24
    if input_count >= 25:
        data.append(0)
    data.extend(
        [
            True,
            0.8,
            30,
            0.8,
            0.0,
            3,
            10.0,
            1500,
        ]
    )
    return data


def batch_request_data(
    texts: Sequence[str],
    reference_audio: Mapping[str, Any],
    voice_description: str,
    *,
    input_count: int | None = None,
) -> list[Any]:
    text_list = [str(text) for text in texts]
    raw_template = os.getenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{texts}", json.dumps(text_list))
            .replace("{text}", json.dumps(json.dumps(text_list)))
            .replace("{voice_description}", json.dumps(voice_description))
            .replace("{reference_audio}", json.dumps(reference_audio))
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise RuntimeError("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE must render to a JSON array")
        return parsed
    if input_count is None:
        input_count = 25
    data = [
        "Same as the voice reference",
        reference_audio,
        json.dumps(text_list),
        None,
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        voice_description,
        False,
        120,
    ]
    if input_count >= 25:
        # The newer batch-capable Gradio contract inserts segments_bucket_max_size
        # before the decoding arguments.
        data.append(len(text_list) if len(text_list) > 1 else 0)
    data.extend(
        [
            True,
            0.8,
            30,
            0.8,
            0.0,
            3,
            10.0,
            1500,
        ]
    )
    return data


def batch_upload_request_data(
    texts: Sequence[str],
    reference_audio: Mapping[str, Any],
    voice_description: str,
    bucket_uri: str,
    *,
    input_count: int | None = None,
    upload_subdir: str | None = None,
    upload_mode: str | None = None,
    auto_upload_enabled: bool | None = None,
) -> list[Any]:
    text_list = [str(text) for text in texts]
    resolved_subdir = (
        os.getenv("WALLET_INDEXTTS_BATCH_UPLOAD_SUBDIR", "")
        if upload_subdir is None
        else str(upload_subdir)
    ).strip()
    resolved_mode = (
        os.getenv("WALLET_INDEXTTS_BATCH_UPLOAD_MODE", "auto")
        if upload_mode is None
        else str(upload_mode)
    ).strip() or "auto"
    if auto_upload_enabled is None:
        resolved_auto_upload = (
            os.getenv("WALLET_INDEXTTS_BATCH_AUTO_UPLOAD_ENABLED", "1").strip().lower()
            not in {"0", "false", "no", "off"}
        )
    else:
        resolved_auto_upload = bool(auto_upload_enabled)
    raw_template = os.getenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{texts}", json.dumps(text_list))
            .replace("{text}", json.dumps(json.dumps(text_list)))
            .replace("{voice_description}", json.dumps(voice_description))
            .replace("{reference_audio}", json.dumps(reference_audio))
            .replace("{bucket_uri}", json.dumps(str(bucket_uri or "")))
            .replace("{upload_subdir}", json.dumps(resolved_subdir))
            .replace("{upload_mode}", json.dumps(resolved_mode))
            .replace("{auto_upload_enabled}", json.dumps(resolved_auto_upload))
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise RuntimeError("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE must render to a JSON array")
        return parsed

    resolved_input_count = 29 if input_count is None else input_count
    if (
        isinstance(resolved_input_count, bool)
        or not isinstance(resolved_input_count, int)
        or resolved_input_count < 24
    ):
        raise ValueError("batch upload input_count must be an integer of at least 24")
    if resolved_input_count > 29:
        raise RuntimeError(
            f"Unsupported {resolved_input_count}-field batch upload contract; "
            "set WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE explicitly"
        )

    # Fields 1-25 match /gen_batch. Legacy upload deployments exposed only
    # field 26 (bucket URI); the live Publicus endpoint adds fields 27-29.
    base_input_count = min(resolved_input_count, 25)
    base = list(
        batch_request_data(
            texts,
            reference_audio,
            voice_description,
            input_count=base_input_count,
        )
    )
    upload_tail = [
        str(bucket_uri or ""),
        resolved_subdir,
        resolved_mode,
        resolved_auto_upload,
    ]
    base.extend(upload_tail[: max(0, resolved_input_count - 25)])
    return base


def wait_for_result(session_hash: str) -> dict[str, Any]:
    try:
        return indextts_space_client().wait_for_queue_result(
            session_hash,
            timeout_seconds=indextts_timeout(),
            poll_interval_seconds=0.5,
        )
    except Exception as exc:
        raise_if_indextts_quota_exceeded(exc)
        raise


def find_audio_reference(value: Any) -> Any:
    if isinstance(value, Mapping):
        if str(value.get("mime_type") or value.get("mimeType") or "").startswith("audio/"):
            return value
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "")
            if pathish and (pathish.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in pathish or "/gradio_api/file=" in pathish):
                return value
        for item in value.values():
            found = find_audio_reference(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_audio_reference(item)
            if found:
                return found
    return None


def find_audio_references(value: Any) -> list[Any]:
    refs: list[Any] = []
    seen: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, str):
            lowered = item.casefold().split("?", 1)[0]
            if lowered.endswith((".wav", ".mp3", ".flac", ".ogg")):
                if item not in seen:
                    seen.add(item)
                    refs.append(item)
            return
        if isinstance(item, Mapping):
            direct = find_audio_reference(item)
            if direct is item:
                key = json.dumps(item, sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    refs.append(item)
                return
            for child in item.values():
                visit(child)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return refs


def gradio_update_value(value: Any) -> Any:
    if isinstance(value, Mapping) and value.get("__type__") == "update":
        return value.get("value")
    return value


def gradio_output_values(result: Mapping[str, Any]) -> list[Any]:
    data = result.get("data")
    if isinstance(data, list):
        return [gradio_update_value(item) for item in data]
    return []


def gradio_file_key(reference: Any) -> str:
    if isinstance(reference, Mapping):
        return str(reference.get("url") or reference.get("path") or reference.get("name") or json.dumps(reference, sort_keys=True, default=str))
    return str(reference)


def gradio_reference_filename(reference: Any) -> str:
    """Extract a safe basename from a Gradio file reference."""
    if isinstance(reference, Mapping):
        raw_value = (
            reference.get("path")
            or reference.get("name")
            or reference.get("url")
            or ""
        )
    else:
        raw_value = reference
    raw = urllib_parse.unquote(str(raw_value or "").strip())
    if not raw:
        raise IndexTTSUploadResultUnverifiableError(
            "IndexTTS upload result contained an empty file reference"
        )
    parsed = urllib_parse.urlparse(raw)
    candidate = parsed.path or raw
    if "/file=" in candidate:
        candidate = candidate.rsplit("/file=", 1)[1]
    filename = Path(candidate).name
    if (
        not filename
        or filename in {".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filename)
        or Path(filename).suffix.casefold() not in {".wav", ".mp3", ".flac", ".ogg"}
    ):
        raise IndexTTSUploadResultUnverifiableError(
            f"IndexTTS upload result did not expose a safe audio filename: {raw!r}"
        )
    return filename


def hf_bucket_upload_target(bucket_uri: str, upload_subdir: str = "") -> str:
    base = str(bucket_uri or "").strip().rstrip("/")
    parsed = urllib_parse.urlparse(base)
    if parsed.scheme != "hf" or parsed.netloc != "buckets" or len([part for part in parsed.path.split("/") if part]) < 2:
        raise IndexTTSUploadResultUnverifiableError(
            f"Cannot derive uploaded object URIs from invalid HF bucket URI {base!r}"
        )
    suffix = str(upload_subdir or "").strip().strip("/")
    if suffix:
        parts = suffix.split("/")
        if any(
            part in {"", ".", ".."}
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part)
            for part in parts
        ):
            raise IndexTTSUploadResultUnverifiableError(
                f"Cannot derive uploaded object URIs from unsafe bucket subdirectory {suffix!r}"
            )
        return f"{base}/{suffix}"
    return base


def dedupe_gradio_references(references: Sequence[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for reference in references:
        key = gradio_file_key(reference)
        if key and key not in seen:
            seen.add(key)
            deduped.append(reference)
    return deduped


def find_file_reference(value: Any, *, suffixes: Sequence[str]) -> Any:
    suffix_tuple = tuple(suffix.lower() for suffix in suffixes)
    if isinstance(value, Mapping):
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "").lower()
            if pathish.endswith(suffix_tuple) or any(f"/file=" in pathish and suffix in pathish for suffix in suffix_tuple):
                return value
        for item in value.values():
            found = find_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, str) and value.lower().endswith(suffix_tuple):
        return value
    return None


def extract_audio_files_from_zip(data: bytes) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith("/") or not name.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
                continue
            extracted.append({"name": name, "_inline_bytes": archive.read(name)})
    return extracted


def batch_audio_references(result: Mapping[str, Any]) -> list[Any]:
    outputs = gradio_output_values(result)
    if len(outputs) >= 2:
        generated_files = find_audio_references(outputs[1])
        if generated_files:
            return dedupe_gradio_references(generated_files)
    if len(outputs) >= 3:
        zip_ref = find_file_reference(outputs[2], suffixes=(".zip",))
        if zip_ref:
            try:
                archive, _mime_type = fetch_gradio_file(zip_ref)
                extracted = extract_audio_files_from_zip(archive)
                if extracted:
                    return extracted
            except Exception:
                pass
    return dedupe_gradio_references(find_audio_references(result))


def fetch_gradio_file(ref: Any) -> tuple[bytes, str]:
    if isinstance(ref, Mapping) and isinstance(ref.get("_inline_bytes"), (bytes, bytearray)):
        name = str(ref.get("name") or ref.get("path") or "")
        return bytes(ref["_inline_bytes"]), mimetypes.guess_type(name)[0] or "audio/wav"
    if isinstance(ref, Mapping):
        mime_type = str(ref.get("mime_type") or ref.get("mimeType") or "")
    else:
        mime_type = ""
    data, resolved_mime_type = indextts_space_client().fetch_file(ref)
    return data, mime_type or resolved_mime_type or "audio/wav"


def synthesize(text: str, config: Mapping[str, Any], fn_index: int, reference_audio: Mapping[str, Any], voice_description: str) -> dict[str, Any]:
    start = time.perf_counter()
    input_count = lookup_dependency_input_count(config, fn_index)
    session_hash = indextts_space_client().queue_join(
        int(fn_index),
        request_data(text, reference_audio, voice_description, input_count=input_count),
    )
    result = wait_for_result(session_hash)
    audio_ref = find_audio_reference(result)
    if not audio_ref:
        raise RuntimeError("IndexTTS completed without an audio file")
    audio, mime_type = fetch_gradio_file(audio_ref)
    return {
        "audio": audio,
        "mimeType": "audio/wav" if audio.startswith(b"RIFF") and b"WAVE" in audio[:16] else mime_type,
        "latencyMs": int((time.perf_counter() - start) * 1000),
    }


def direct_batch_synthesis(
    texts: Sequence[str],
    config: Mapping[str, Any],
    reference_audio: Mapping[str, Any],
    voice_description: str,
) -> list[dict[str, Any]]:
    text_list = [str(text) for text in texts]
    if not text_list:
        return []
    start = time.perf_counter()
    batch_fn_index = indextts_batch_fn_index(config)
    batch_input_count = lookup_dependency_input_count(config, batch_fn_index)
    session_hash = indextts_space_client().queue_join(
        int(batch_fn_index),
        batch_request_data(
            text_list,
            reference_audio,
            voice_description,
            input_count=batch_input_count,
        ),
    )
    result = wait_for_result(session_hash)
    audio_refs = batch_audio_references(result)
    if len(audio_refs) < len(text_list):
        raise RuntimeError(f"IndexTTS batch returned {len(audio_refs)} audio files for {len(text_list)} texts")
    batch_latency_ms = int((time.perf_counter() - start) * 1000)
    outputs: list[dict[str, Any]] = []
    for ref in audio_refs[: len(text_list)]:
        audio, mime_type = fetch_gradio_file(ref)
        outputs.append(
            {
                "audio": audio,
                "mimeType": "audio/wav" if audio.startswith(b"RIFF") and b"WAVE" in audio[:16] else mime_type,
                "latencyMs": batch_latency_ms,
                "batchLatencyMs": batch_latency_ms,
                "batchMode": "batch",
            }
        )
    return outputs


def direct_batch_upload_synthesis(
    texts: Sequence[str],
    config: Mapping[str, Any],
    reference_audio: Mapping[str, Any],
    voice_description: str,
    bucket_uri: str,
    response_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Trigger gen_batch_with_upload on the Space. The Space generates audio
    and uploads it directly to bucket_uri; no audio bytes are downloaded locally.
    Returns per-item results only when the actual uploaded filenames can be
    derived from the endpoint response."""
    text_list = [str(text) for text in texts]
    if not text_list:
        return []
    response_id_list = [str(response_id) for response_id in response_ids]
    if len(response_id_list) != len(text_list):
        raise ValueError("response_ids must contain exactly one ID per text")
    start = time.perf_counter()
    batch_upload_api_name = indextts_batch_upload_api_name()
    batch_upload_fn_index = lookup_dependency_id_by_api_name(config, batch_upload_api_name)
    if batch_upload_fn_index is None:
        raise RuntimeError(
            f"IndexTTS batch upload api_name {batch_upload_api_name!r} was not found in the live Space config"
        )
    batch_upload_input_count = lookup_dependency_input_count(config, batch_upload_fn_index)
    request_payload = batch_upload_request_data(
        text_list,
        reference_audio,
        voice_description,
        bucket_uri,
        input_count=batch_upload_input_count,
    )
    if len(request_payload) != batch_upload_input_count:
        raise IndexTTSUploadResultUnverifiableError(
            f"IndexTTS batch upload request rendered {len(request_payload)} fields "
            f"for a {batch_upload_input_count}-field live contract"
        )
    if len(request_payload) < 29:
        raise IndexTTSUploadResultUnverifiableError(
            "Legacy batch upload contract does not expose enough request fields "
            "to derive the effective remote upload target"
        )

    request_bucket_uri = str(request_payload[25] or "").strip()
    request_upload_subdir = str(request_payload[26] or "").strip()
    request_upload_mode = str(request_payload[27] or "auto").strip() or "auto"
    raw_auto_upload = request_payload[28]
    auto_upload_enabled = (
        raw_auto_upload
        if isinstance(raw_auto_upload, bool)
        else str(raw_auto_upload or "").strip().lower() in {"1", "true", "yes", "on"}
    )
    if not auto_upload_enabled:
        raise IndexTTSUploadResultUnverifiableError(
            "Batch upload request has automatic upload disabled"
        )
    per_item_upload_modes = {"auto", "batch_files", "all_artifacts"}
    if request_upload_mode not in per_item_upload_modes and not (
        request_upload_mode == "single_preview" and len(text_list) == 1
    ):
        raise IndexTTSUploadResultUnverifiableError(
            f"Upload mode {request_upload_mode!r} does not upload one authoritative file per response"
        )
    upload_target = hf_bucket_upload_target(
        request_bucket_uri,
        request_upload_subdir,
    )

    session_hash = indextts_space_client().queue_join(
        int(batch_upload_fn_index),
        request_payload,
    )
    result = wait_for_result(session_hash)
    output_values = gradio_output_values(result)
    uploaded_references = (
        dedupe_gradio_references(find_audio_references(output_values[1]))
        if len(output_values) >= 2
        else []
    )
    if len(uploaded_references) != len(text_list):
        raise IndexTTSUploadResultUnverifiableError(
            f"IndexTTS batch upload returned {len(uploaded_references)} authoritative "
            f"audio filename(s) for {len(text_list)} response(s)"
        )
    filenames = [gradio_reference_filename(reference) for reference in uploaded_references]
    if len(set(filenames)) != len(filenames):
        raise IndexTTSUploadResultUnverifiableError(
            "IndexTTS batch upload returned duplicate audio filenames"
        )

    batch_latency_ms = int((time.perf_counter() - start) * 1000)
    outputs: list[dict[str, Any]] = []
    for response_id, filename in zip(response_id_list, filenames):
        remote_uri = f"{upload_target}/{filename}"
        suffix = Path(filename).suffix.casefold()
        mime_type = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
        }.get(suffix, mimetypes.guess_type(filename)[0] or "application/octet-stream")
        output = {
            "responseId": response_id,
            "uploadedFilename": filename,
            "preferredBucketAudioUri": remote_uri,
            "preferredMimeType": mime_type,
            "latencyMs": batch_latency_ms,
            "batchLatencyMs": batch_latency_ms,
            "batchMode": "batch-upload",
        }
        if suffix == ".mp3":
            output["bucketMp3Uri"] = remote_uri
        else:
            output["bucketAudioUri"] = remote_uri
        outputs.append(output)
    return outputs


def annotate_split_batch_outputs(
    outputs: Sequence[Mapping[str, Any]],
    *,
    root_batch_size: int,
    executed_batch_size: int,
    split_depth: int,
    fallback_reason: str,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for output in outputs:
        item = dict(output)
        base_mode = str(item.get("batchMode") or "batch")
        if split_depth > 0:
            if base_mode.endswith("-split-fallback"):
                item["batchMode"] = base_mode
            elif base_mode == "batch":
                item["batchMode"] = "batch-split-fallback"
            elif base_mode in {"sequential", "sequential-fallback"}:
                item["batchMode"] = "sequential-split-fallback"
            elif base_mode in {"parallel", "parallel-fallback"}:
                item["batchMode"] = "parallel-split-fallback"
            else:
                item["batchMode"] = f"{base_mode}-split-fallback"
            item["batchRequestedSize"] = root_batch_size
            item["batchExecutedSize"] = executed_batch_size
            item["batchSplitDepth"] = split_depth
        if fallback_reason:
            existing_reason = str(item.get("batchFallbackReason") or "").strip()
            item["batchFallbackReason"] = fallback_reason if not existing_reason else f"{fallback_reason} | {existing_reason}"
        annotated.append(item)
    return annotated


def adaptive_split_batch_synthesis(
    texts: Sequence[str],
    config: Mapping[str, Any],
    single_fn_index: int,
    reference_audio: Mapping[str, Any],
    voice_description: str,
    *,
    require_batch: bool,
    root_batch_size: int | None = None,
    split_depth: int = 0,
    fallback_reason: str = "",
) -> list[dict[str, Any]]:
    text_list = [str(text) for text in texts]
    if not text_list:
        return []
    requested_batch_size = root_batch_size or len(text_list)
    try:
        outputs = direct_batch_synthesis(text_list, config, reference_audio, voice_description)
        if split_depth > 0:
            outputs = annotate_split_batch_outputs(
                outputs,
                root_batch_size=requested_batch_size,
                executed_batch_size=len(text_list),
                split_depth=split_depth,
                fallback_reason=fallback_reason,
            )
        return outputs
    except Exception as exc:
        if isinstance(exc, IndexTTSQuotaExceededError):
            raise
        if (
            is_hf_space_transport_error(exc)
            or is_stale_gradio_file_error(exc)
        ):
            # Splitting cannot repair a disconnected response stream or an
            # expired server-local FileData path. Let the package-owned upload
            # lease refresh the reference and retry the logical chunk.
            raise
        failure_reason = f"{type(exc).__name__}: {exc}"
        inherited_reason = fallback_reason or failure_reason
        if len(text_list) > 1 and is_indextts_transient_worker_error(exc):
            midpoint = max(1, len(text_list) // 2)
            left = adaptive_split_batch_synthesis(
                text_list[:midpoint],
                config,
                single_fn_index,
                reference_audio,
                voice_description,
                require_batch=require_batch,
                root_batch_size=requested_batch_size,
                split_depth=split_depth + 1,
                fallback_reason=inherited_reason,
            )
            right = adaptive_split_batch_synthesis(
                text_list[midpoint:],
                config,
                single_fn_index,
                reference_audio,
                voice_description,
                require_batch=require_batch,
                root_batch_size=requested_batch_size,
                split_depth=split_depth + 1,
                fallback_reason=inherited_reason,
            )
            return [*left, *right]
        if require_batch:
            return [
                batch_failure_result(
                    exc,
                    batch_mode="batch-failed",
                    fallback_reason=inherited_reason,
                    requested_batch_size=requested_batch_size,
                    executed_batch_size=len(text_list),
                    split_depth=split_depth,
                )
                for _text in text_list
            ]
        output = {
            **synthesize(text_list[0], config, single_fn_index, reference_audio, voice_description),
            "batchMode": "sequential-split-fallback",
        }
        return annotate_split_batch_outputs(
            [output],
            root_batch_size=requested_batch_size,
            executed_batch_size=1,
            split_depth=max(1, split_depth),
            fallback_reason=inherited_reason,
        )


def synthesize_batch(
    texts: Sequence[str],
    config: Mapping[str, Any],
    single_fn_index: int,
    reference_audio: Mapping[str, Any],
    voice_description: str,
    *,
    parallel_workers: int = 1,
) -> list[dict[str, Any]]:
    text_list = [str(text) for text in texts]
    if not text_list:
        return []
    batch_enabled = os.getenv("WALLET_INDEXTTS_BATCH_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
    require_batch = os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "").strip().lower() in {"1", "true", "yes"}
    attempted_batch = bool(batch_enabled)
    batch_available = indextts_batch_available(config)
    batch_fallback_reason = ""
    if batch_enabled and not batch_available:
        batch_fallback_reason = f"IndexTTS batch api_name {indextts_batch_api_name()!r} was not found in the live Space config"
        if require_batch:
            raise RuntimeError(batch_fallback_reason)
        batch_enabled = False
    if batch_enabled:
        try:
            return adaptive_split_batch_synthesis(
                text_list,
                config,
                single_fn_index,
                reference_audio,
                voice_description,
                require_batch=require_batch,
                root_batch_size=len(text_list),
            )
        except Exception as exc:
            batch_fallback_reason = f"{type(exc).__name__}: {exc}"
            if require_batch:
                raise

    worker_count = max(1, min(int(parallel_workers or 1), len(text_list)))
    fallback_mode = "parallel-fallback" if attempted_batch else "parallel"
    if worker_count > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(synthesize, text, config, single_fn_index, reference_audio, voice_description)
                for text in text_list
            ]
            return [
                {
                    **future.result(),
                    "batchMode": fallback_mode,
                    **({"batchFallbackReason": batch_fallback_reason} if batch_fallback_reason else {}),
                }
                for future in futures
            ]

    return [
        {
            **synthesize(text, config, single_fn_index, reference_audio, voice_description),
            "batchMode": "sequential-fallback" if attempted_batch else "sequential",
            **({"batchFallbackReason": batch_fallback_reason} if batch_fallback_reason else {}),
        }
        for text in text_list
    ]


def add_response_source(
    by_text: dict[str, dict[str, Any]],
    *,
    text: str,
    source: str,
    source_id: str,
    route: str = "",
    service_tag: str = "",
    location_tag: str = "",
) -> None:
    raw_text = " ".join(str(text or "").split())
    if not raw_text:
        return
    normalized = normalize_indextts_spoken_text(raw_text)
    if not normalized:
        return
    text_hash = stable_id(normalized)
    item = by_text.setdefault(
        normalized,
        {
            "id": f"abby-tts-{text_hash}",
            "textHash": text_hash,
            "text": normalized,
            "originalTexts": [],
            "routes": set(),
            "serviceTags": set(),
            "locationTags": set(),
            "sourceTypes": set(),
            "sourceIds": [],
        },
    )
    if raw_text != normalized and raw_text not in item["originalTexts"]:
        item["originalTexts"].append(raw_text)
    if route:
        item["routes"].add(route)
    if service_tag:
        item["serviceTags"].add(service_tag)
    if location_tag:
        item["locationTags"].add(location_tag)
    item["sourceTypes"].add(source)
    if source_id and source_id not in item["sourceIds"]:
        item["sourceIds"].append(source_id)


def add_response_record(
    by_text: dict[str, dict[str, Any]],
    record: Mapping[str, Any],
    *,
    default_source: str = "manifest.response",
) -> None:
    raw_text = " ".join(str(record.get("text") or "").split())
    if not raw_text:
        return
    normalized = normalize_manifest_record_text(raw_text, record)
    if not normalized:
        return
    text_hash = stable_id(normalized)
    item = by_text.setdefault(
        normalized,
        {
            "id": f"abby-tts-{text_hash}",
            "textHash": text_hash,
            "text": normalized,
            "originalTexts": [],
            "routes": set(),
            "serviceTags": set(),
            "locationTags": set(),
            "sourceTypes": set(),
            "sourceIds": [],
            "priorityScore": 0.0,
            "priorityRank": None,
        },
    )
    priority_score = float(record.get("priorityScore") or 0.0)
    if priority_score > float(item.get("priorityScore") or 0.0):
        item["priorityScore"] = priority_score
    raw_priority_rank = record.get("priorityRank")
    if raw_priority_rank is not None and str(raw_priority_rank).strip() != "":
        priority_rank = int(raw_priority_rank)
        current_rank = item.get("priorityRank")
        if current_rank is None or priority_rank < int(current_rank):
            item["priorityRank"] = priority_rank
    if raw_text != normalized and raw_text not in item["originalTexts"]:
        item["originalTexts"].append(raw_text)
    for original_text in record.get("originalTexts") or []:
        collapsed = " ".join(str(original_text or "").split())
        if collapsed and collapsed != normalized and collapsed not in item["originalTexts"]:
            item["originalTexts"].append(collapsed)
    for route in record.get("routes") or []:
        normalized_route = str(route or "").strip()
        if normalized_route:
            item["routes"].add(normalized_route)
    for service_tag in record.get("serviceTags") or []:
        normalized_service_tag = str(service_tag or "").strip()
        if normalized_service_tag:
            item["serviceTags"].add(normalized_service_tag)
    for location_tag in record.get("locationTags") or []:
        normalized_location_tag = str(location_tag or "").strip()
        if normalized_location_tag:
            item["locationTags"].add(normalized_location_tag)
    source_types = [str(source or "").strip() for source in (record.get("sourceTypes") or [])]
    if not any(source_types):
        source_types = [default_source]
    for source_type in source_types:
        if source_type:
            item["sourceTypes"].add(source_type)
    for source_id in record.get("sourceIds") or []:
        normalized_source_id = str(source_id or "").strip()
        if normalized_source_id and normalized_source_id not in item["sourceIds"]:
            item["sourceIds"].append(normalized_source_id)
    for field in SLOTTED_RESPONSE_FIELDS:
        values = [str(value or "").strip() for value in (record.get(field) or [])]
        normalized_values = {value for value in values if value}
        if not normalized_values:
            continue
        existing = item.setdefault(field, set())
        if not isinstance(existing, set):
            existing = set(existing)
            item[field] = existing
        existing.update(normalized_values)


def empty_slotted_annotation() -> dict[str, set[str]]:
    return {
        "slottedIntentIds": set(),
        "slottedCanonicalQueryTemplates": set(),
        "slottedResponseFrameIds": set(),
        "slottedResponseSignatures": set(),
        "slottedEdgeIds": set(),
    }


def add_slotted_annotation(
    annotation: dict[str, set[str]],
    *,
    intent_id: str = "",
    canonical_query_template: str = "",
    response_frame_id: str = "",
    response_signature: str = "",
    edge_id: str = "",
) -> None:
    if intent_id:
        annotation["slottedIntentIds"].add(intent_id)
    if canonical_query_template:
        annotation["slottedCanonicalQueryTemplates"].add(canonical_query_template)
    if response_frame_id:
        annotation["slottedResponseFrameIds"].add(response_frame_id)
    if response_signature:
        annotation["slottedResponseSignatures"].add(response_signature)
    if edge_id:
        annotation["slottedEdgeIds"].add(edge_id)


def merge_slotted_annotation(target: dict[str, set[str]], source: Mapping[str, Sequence[str]] | None) -> None:
    if not source:
        return
    for key in target:
        for value in source.get(key, ()):
            normalized = str(value or "").strip()
            if normalized:
                target[key].add(normalized)


def slotted_annotation_payload(annotation: dict[str, set[str]]) -> dict[str, list[str]]:
    return {key: sorted(values) for key, values in annotation.items() if values}


def normalize_slotted_audio_lookup_text(text: str) -> str:
    collapsed = " ".join(str(text or "").split())
    if not collapsed:
        return ""
    return normalize_indextts_spoken_text(collapsed)


def load_slotted_response_annotations(index_path: Path) -> dict[str, dict[str, dict[str, set[str]]]]:
    if not index_path.exists():
        return {"byRecordId": {}, "byNormalizedAssistantText": {}}

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    intents = payload.get("intents") or []
    response_frames = payload.get("responseFrames") or []
    edges = payload.get("edges") or []
    intents_by_id = {str(intent.get("id") or ""): intent for intent in intents}
    response_frames_by_id = {str(frame.get("id") or ""): frame for frame in response_frames}
    by_record_id: dict[str, dict[str, set[str]]] = {}
    by_normalized_assistant_text: dict[str, dict[str, set[str]]] = {}

    def ensure_record_annotation(record_id: str) -> dict[str, set[str]]:
        return by_record_id.setdefault(record_id, empty_slotted_annotation())

    def ensure_text_annotation(text: str) -> dict[str, set[str]]:
        return by_normalized_assistant_text.setdefault(text, empty_slotted_annotation())

    def annotate_example(
        *,
        record_id: str,
        assistant_text: str = "",
        intent_id: str = "",
        canonical_query_template: str = "",
        response_frame_id: str = "",
        response_signature: str = "",
        edge_id: str = "",
    ) -> None:
        if record_id:
            add_slotted_annotation(
                ensure_record_annotation(record_id),
                intent_id=intent_id,
                canonical_query_template=canonical_query_template,
                response_frame_id=response_frame_id,
                response_signature=response_signature,
                edge_id=edge_id,
            )
        normalized_assistant_text = normalize_slotted_audio_lookup_text(assistant_text)
        if normalized_assistant_text:
            add_slotted_annotation(
                ensure_text_annotation(normalized_assistant_text),
                intent_id=intent_id,
                canonical_query_template=canonical_query_template,
                response_frame_id=response_frame_id,
                response_signature=response_signature,
                edge_id=edge_id,
            )

    for intent in intents:
        intent_id = str(intent.get("id") or "")
        canonical_query_template = str(intent.get("canonicalQueryTemplate") or "")
        for example in intent.get("examples") or []:
            annotate_example(
                record_id=str(example.get("recordId") or ""),
                intent_id=intent_id,
                canonical_query_template=canonical_query_template,
            )

    for frame in response_frames:
        response_frame_id = str(frame.get("id") or "")
        response_signature = str(frame.get("responseSignature") or "")
        for example in frame.get("examples") or []:
            annotate_example(
                record_id=str(example.get("recordId") or ""),
                assistant_text=str(example.get("assistant") or ""),
                response_frame_id=response_frame_id,
                response_signature=response_signature,
            )

    for edge in edges:
        edge_id = str(edge.get("id") or "")
        intent = intents_by_id.get(str(edge.get("source") or ""), {})
        response_frame = response_frames_by_id.get(str(edge.get("target") or ""), {})
        intent_id = str(intent.get("id") or "")
        canonical_query_template = str(intent.get("canonicalQueryTemplate") or "")
        response_frame_id = str(response_frame.get("id") or "")
        response_signature = str(response_frame.get("responseSignature") or "")
        for example in edge.get("examples") or []:
            annotate_example(
                record_id=str(example.get("recordId") or ""),
                assistant_text=str(example.get("assistant") or ""),
                intent_id=intent_id,
                canonical_query_template=canonical_query_template,
                response_frame_id=response_frame_id,
                response_signature=response_signature,
                edge_id=edge_id,
            )

    return {
        "byRecordId": by_record_id,
        "byNormalizedAssistantText": by_normalized_assistant_text,
    }


def annotate_audio_responses_with_slotted_metadata(
    responses: list[dict[str, Any]],
    index_path: Path | None,
) -> None:
    if index_path is None:
        return
    annotations = load_slotted_response_annotations(index_path)
    by_record_id = annotations.get("byRecordId") or {}
    by_normalized_assistant_text = annotations.get("byNormalizedAssistantText") or {}
    if not by_record_id and not by_normalized_assistant_text:
        return

    for item in responses:
        annotation = empty_slotted_annotation()
        for field in SLOTTED_RESPONSE_FIELDS:
            for value in item.get(field) or []:
                normalized_value = str(value or "").strip()
                if normalized_value:
                    annotation[field].add(normalized_value)
        for source_id in item.get("sourceIds") or []:
            merge_slotted_annotation(annotation, by_record_id.get(str(source_id or "")))
        merge_slotted_annotation(annotation, by_normalized_assistant_text.get(str(item.get("text") or "")))
        for original_text in item.get("originalTexts") or []:
            normalized_original = normalize_slotted_audio_lookup_text(str(original_text or ""))
            if normalized_original:
                merge_slotted_annotation(annotation, by_normalized_assistant_text.get(normalized_original))
        item.update(slotted_annotation_payload(annotation))


def finalize_audio_responses(by_text: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    for item in by_text.values():
        response = {
            "id": str(item.get("id") or ""),
            "textHash": str(item.get("textHash") or ""),
            "text": str(item.get("text") or ""),
            "originalTexts": list(item.get("originalTexts") or []),
            "routes": sorted(item.get("routes") or []),
            "serviceTags": sorted(item.get("serviceTags") or []),
            "locationTags": sorted(item.get("locationTags") or []),
            "sourceTypes": sorted(item.get("sourceTypes") or []),
            "sourceIds": list(item.get("sourceIds") or []),
        }
        priority_score = float(item.get("priorityScore") or 0.0)
        if priority_score:
            response["priorityScore"] = priority_score
        priority_rank = item.get("priorityRank")
        if priority_rank is not None:
            response["priorityRank"] = int(priority_rank)
        for field in SLOTTED_RESPONSE_FIELDS:
            values = item.get(field) or []
            if values:
                response[field] = sorted(values)
        responses.append(response)
    responses.sort(
        key=lambda item: (
            -float(item.get("priorityScore") or 0.0),
            int(item.get("priorityRank") or 10**9),
            str(item["id"]),
        )
    )
    return responses


def load_audio_responses(
    dag_path: Path,
    results_path: Path,
    *,
    include_assistant: bool = True,
    include_voice: bool = True,
    slotted_response_index: Path | None = None,
) -> list[dict[str, Any]]:
    by_text: dict[str, dict[str, Any]] = {}
    if include_voice:
        dag = json.loads(dag_path.read_text(encoding="utf-8"))
        for node in dag.get("nodes", []):
            add_response_source(
                by_text,
                text=str(node.get("voiceResponse") or ""),
                source="dag.voiceResponse",
                source_id=str(node.get("id") or ""),
                route=str(node.get("route") or ""),
                service_tag=str(node.get("serviceTag") or ""),
                location_tag=str(node.get("locationTag") or ""),
            )
    if include_assistant:
        results = json.loads(results_path.read_text(encoding="utf-8"))
        for result in results.get("results", []):
            scenario_id = str(result.get("id") or "")
            for turn_index, turn in enumerate(result.get("turns", []), start=1):
                add_response_source(
                    by_text,
                    text=str(turn.get("assistant") or ""),
                    source="simulation.assistant",
                    source_id=f"{scenario_id}#turn-{turn_index}",
                    route=str(turn.get("route") or ""),
                )
    responses = finalize_audio_responses(by_text)
    annotate_audio_responses_with_slotted_metadata(responses, slotted_response_index)
    return responses


def load_audio_responses_from_manifest(
    manifest_path: Path,
    *,
    slotted_response_index: Path | None = None,
) -> list[dict[str, Any]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    response_records = payload if isinstance(payload, list) else payload.get("responses") or []
    by_text: dict[str, dict[str, Any]] = {}
    for record in response_records:
        if isinstance(record, Mapping):
            add_response_record(by_text, record)
    responses = finalize_audio_responses(by_text)
    annotate_audio_responses_with_slotted_metadata(responses, slotted_response_index)
    return responses


def write_progress(path: Path | None, entries: list[dict[str, Any]], total: int, started_at: float) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    status_counts = Counter(str(entry.get("status") or "unknown") for entry in entries)
    payload = {
        "schemaVersion": 1,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsedSeconds": round(time.time() - started_at, 3),
        "completed": len(entries),
        "total": total,
        "statusCounts": dict(sorted(status_counts.items())),
        "lastResponse": entries[-1] if entries else None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace one local JSON receipt."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--space-url",
        default=os.getenv("WALLET_INDEXTTS_SPACE_URL", DEFAULT_INDEXTTS_SPACE_URL).strip() or DEFAULT_INDEXTTS_SPACE_URL,
        help="Override the IndexTTS Space base URL for this invocation.",
    )
    parser.add_argument(
        "--model-name",
        default=os.getenv("WALLET_INDEXTTS_MODEL_NAME", DEFAULT_INDEXTTS_MODEL_NAME).strip() or DEFAULT_INDEXTTS_MODEL_NAME,
        help="Provider/model identity recorded in generated manifests.",
    )
    parser.add_argument("--dag", type=Path, default=DEFAULT_DAG)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument(
        "--response-manifest",
        type=Path,
        default=None,
        help="Load deduplicated pregenerated text responses from a manifest instead of --dag/--results.",
    )
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--public-manifest", type=Path, default=DEFAULT_PUBLIC_MANIFEST)
    parser.add_argument("--slotted-response-index", type=Path, default=DEFAULT_SLOTTED_RESPONSE_INDEX)
    parser.add_argument("--voice-description", default="Same as the voice reference")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many deduplicated responses before applying --limit.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--mp3", dest="write_mp3", action="store_true", default=True)
    parser.add_argument("--no-mp3", dest="write_mp3", action="store_false")
    parser.add_argument("--mp3-bitrate", default="64k")
    parser.add_argument(
        "--remote-batch-size",
        type=int,
        default=int(
            os.getenv(
                "WALLET_INDEXTTS_REMOTE_BATCH_SIZE",
                str(DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE),
            )
            or str(DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE)
        ),
        help="Send this many uncached responses to the IndexTTS batch endpoint at once when available.",
    )
    batch_requirement = parser.add_mutually_exclusive_group()
    batch_requirement.add_argument(
        "--require-batch",
        dest="require_batch",
        action="store_const",
        const=True,
        default=None,
        help="Fail closed when the configured batch endpoint is unavailable or a batch cannot be completed.",
    )
    batch_requirement.add_argument(
        "--allow-single-fallback",
        dest="require_batch",
        action="store_const",
        const=False,
        help="Explicitly permit gen_single fallback when batch generation is unavailable.",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=int(os.getenv("WALLET_INDEXTTS_PARALLEL_WORKERS", "1") or "1"),
        help="Use this many concurrent gen_single requests when the batch endpoint is unavailable or disabled.",
    )
    parser.add_argument("--delete-wav-after-mp3", action="store_true", default=True)
    parser.add_argument("--keep-wav", dest="delete_wav_after_mp3", action="store_false")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=None,
        help="Stop starting new synthesis jobs after this many seconds. Existing cached MP3s are still recorded in the manifest.",
    )
    parser.add_argument("--progress-json", type=Path, default=None, help="Write resumable progress after every response.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--voice-responses-only", action="store_true")
    parser.add_argument("--assistant-responses-only", action="store_true")
    parser.add_argument(
        "--validate-transcripts",
        action="store_true",
        help="Transcribe generated or cached audio with Whisper and compare it to the expected normalized spoken text.",
    )
    parser.add_argument(
        "--transcript-validation-limit",
        type=int,
        default=1,
        help="Validate up to this many generated or cached audio files when --validate-transcripts is enabled.",
    )
    parser.add_argument(
        "--transcript-validation-model",
        default=os.getenv("WALLET_INDEXTTS_TRANSCRIPTION_MODEL", "tiny.en"),
        help="Whisper model name to use for transcript validation.",
    )
    parser.add_argument(
        "--transcript-validation-language",
        default=os.getenv("WALLET_INDEXTTS_TRANSCRIPTION_LANGUAGE", "en"),
        help="Language hint passed to Whisper for transcript validation.",
    )
    parser.add_argument(
        "--transcript-validation-device",
        default=os.getenv("WALLET_INDEXTTS_TRANSCRIPTION_DEVICE", "auto"),
        help="Whisper device for transcript validation: auto, cpu, or cuda.",
    )
    parser.add_argument(
        "--transcript-validation-threshold",
        type=float,
        default=0.72,
        help="Minimum normalized transcript similarity required for validation to pass.",
    )
    parser.add_argument(
        "--transcript-validation-soft-fail",
        action="store_true",
        help="Record transcript validation failures in the manifest but still exit successfully.",
    )
    parser.add_argument(
        "--print-indextts-contract",
        action="store_true",
        help="Fetch the live IndexTTS Gradio config, print the detected single/batch contract summary, and exit.",
    )
    parser.add_argument(
        "--regeneration-plan",
        type=Path,
        default=None,
        help="Canonical package-owned regeneration plan used with --canary-dispatch-manifest.",
    )
    parser.add_argument(
        "--canary-dispatch-manifest",
        type=Path,
        default=None,
        help="Write a bounded no-dispatch canary manifest and exit after a read-only contract probe.",
    )
    parser.add_argument("--canary-size", type=int, default=12)
    parser.add_argument("--canary-max-attempts-per-item", type=int, default=2)
    parser.add_argument("--canary-max-provider-requests", type=int, default=None)
    parser.add_argument("--canary-cost-microusd-per-request", type=int, default=1)
    parser.add_argument("--canary-max-cost-microusd", type=int, default=None)
    parser.add_argument("--expected-single-api-name", default="/gen_single")
    parser.add_argument("--expected-single-fn-index", type=int, default=6)
    parser.add_argument("--expected-single-input-count", type=int, default=25)
    parser.add_argument("--expected-batch-api-name", default="/gen_batch")
    parser.add_argument("--expected-batch-fn-index", type=int, default=7)
    parser.add_argument("--expected-batch-input-count", type=int, default=25)
    parser.add_argument(
        "--allow-batch-contract-drift",
        action="store_true",
        help="Probe only the single endpoint contract; intended for explicitly selected legacy Spaces.",
    )
    parser.add_argument(
        "--bucket-uri",
        default=os.getenv("WALLET_INDEXTTS_BUCKET_URI", "").strip(),
        help="If set, sync generated audio to <bucket-uri>/audio and local manifests to <bucket-uri>/metadata using the hf CLI.",
    )
    parser.add_argument(
        "--require-upload-capable-batch",
        action="store_true",
        help="Fail unless the live Space exposes upload-capable batch endpoints for remote bucket workflows.",
    )
    parser.add_argument(
        "--prune-local-audio-after-sync",
        action="store_true",
        help="Delete local audio files from --output-dir after a successful bucket sync. Keeps disk usage bounded.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if str(args.space_url or "").strip():
        os.environ["WALLET_INDEXTTS_SPACE_URL"] = str(args.space_url).strip()
    if str(args.model_name or "").strip():
        os.environ["WALLET_INDEXTTS_MODEL_NAME"] = str(args.model_name).strip()
    if args.require_batch is not None:
        os.environ["WALLET_INDEXTTS_REQUIRE_BATCH"] = "1" if args.require_batch else "0"
    started_at = time.time()
    include_assistant = not args.voice_responses_only
    include_voice = not args.assistant_responses_only
    if args.response_manifest is not None and (args.voice_responses_only or args.assistant_responses_only):
        raise ValueError("--response-manifest cannot be combined with --voice-responses-only or --assistant-responses-only")
    if args.validate_transcripts and args.transcript_validation_limit < 1:
        raise ValueError("--transcript-validation-limit must be at least 1 when --validate-transcripts is enabled")
    if not 0.0 <= args.transcript_validation_threshold <= 1.0:
        raise ValueError("--transcript-validation-threshold must be between 0.0 and 1.0")
    if args.parallel_workers < 1:
        raise ValueError("--parallel-workers must be at least 1")
    if args.validate_transcripts:
        resolve_whisper_device(args.transcript_validation_device)
    if args.print_indextts_contract:
        load_secret_env()
        print(f"IndexTTS auth: {describe_indextts_auth()}")
        summary = probe_indextts_endpoint_contract(
            expected_api_name=args.expected_single_api_name,
            expected_fn_index=args.expected_single_fn_index,
            expected_input_count=args.expected_single_input_count,
            expected_batch_api_name=args.expected_batch_api_name,
            expected_batch_fn_index=args.expected_batch_fn_index,
            expected_batch_input_count=args.expected_batch_input_count,
            require_batch_match=not args.allow_batch_contract_drift,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        if args.require_upload_capable_batch:
            config = indextts_config()
            fn_index = indextts_fn_index(config)
            ensure_upload_capable_batch_contract(config, fn_index)
        return
    if args.canary_dispatch_manifest is not None:
        if args.regeneration_plan is None:
            raise ValueError(
                "--canary-dispatch-manifest requires --regeneration-plan"
            )
        from ipfs_datasets_py.voice.regeneration import read_regeneration_plan

        load_secret_env()
        endpoint_contract = probe_indextts_endpoint_contract(
            expected_api_name=args.expected_single_api_name,
            expected_fn_index=args.expected_single_fn_index,
            expected_input_count=args.expected_single_input_count,
            expected_batch_api_name=args.expected_batch_api_name,
            expected_batch_fn_index=args.expected_batch_fn_index,
            expected_batch_input_count=args.expected_batch_input_count,
            require_batch_match=not args.allow_batch_contract_drift,
        )
        plan = read_regeneration_plan(args.regeneration_plan)
        canary_manifest = build_canary_dispatch_manifest(
            plan,
            endpoint_contract,
            max_items=args.canary_size,
            max_attempts_per_item=args.canary_max_attempts_per_item,
            max_provider_requests=args.canary_max_provider_requests,
            cost_microusd_per_request=args.canary_cost_microusd_per_request,
            max_cost_microusd=args.canary_max_cost_microusd,
        )
        write_json_atomic(args.canary_dispatch_manifest, canary_manifest)
        print(f"Wrote {args.canary_dispatch_manifest}")
        return
    if args.response_manifest is not None:
        responses = load_audio_responses_from_manifest(
            args.response_manifest,
            slotted_response_index=args.slotted_response_index,
        )
    else:
        responses = load_audio_responses(
            args.dag,
            args.results,
            include_assistant=include_assistant,
            include_voice=include_voice,
            slotted_response_index=args.slotted_response_index,
        )
    if args.offset:
        responses = responses[max(0, args.offset) :]
    if args.limit is not None:
        responses = responses[: max(0, args.limit)]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []
    fatal_exception: Exception | None = None
    if args.dry_run:
        for item in responses:
            manifest_entries.append({**item, "status": "planned", "audioPath": "", "mp3Path": ""})
    else:
        config: dict[str, Any] | None = None
        fn_index: int | None = None
        reference: RefreshableGradioFile | None = None
        contract_summary: dict[str, Any] | None = None
        remote_batch_size = max(1, int(args.remote_batch_size or 1))
        pending: list[tuple[int, dict[str, Any], Path, Path]] = []

        def ensure_remote_client() -> tuple[dict[str, Any], int, Any]:
            nonlocal config, fn_index, reference, contract_summary
            if config is not None and fn_index is not None and reference is not None:
                return config, fn_index, reference
            load_secret_env()
            if not args.reference_audio.exists():
                raise FileNotFoundError(args.reference_audio)
            print(f"IndexTTS auth: {describe_indextts_auth()}")
            config = indextts_config()
            fn_index = indextts_fn_index(config)
            if os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "").strip().lower() in {"1", "true", "yes"}:
                probe_indextts_endpoint_contract(
                    config=config,
                    expected_api_name=args.expected_single_api_name,
                    expected_fn_index=args.expected_single_fn_index,
                    expected_input_count=args.expected_single_input_count,
                    expected_batch_api_name=args.expected_batch_api_name,
                    expected_batch_fn_index=args.expected_batch_fn_index,
                    expected_batch_input_count=args.expected_batch_input_count,
                    require_batch_match=not args.allow_batch_contract_drift,
                )
            contract_summary = indextts_contract_summary(config, fn_index)
            if args.require_upload_capable_batch:
                contract_summary = ensure_upload_capable_batch_contract(config, fn_index)
            if contract_summary.get("deploymentDriftReason"):
                print(f"IndexTTS batch drift: {contract_summary['deploymentDriftReason']}")
            reference = RefreshableGradioFile(
                lambda: upload_reference(args.reference_audio)
            )
            return config, fn_index, reference.get()

        def _record_upload_batch_results(
            batch: list[tuple[int, dict[str, Any], Path, Path]],
            results: list[dict[str, Any]],
        ) -> None:
            """Record results from direct_batch_upload_synthesis (no local audio bytes)."""
            for (index, item, _audio_path, _mp3_path), result in zip(batch, results):
                preferred_mp3_uri = str(result.get("bucketMp3Uri") or "")
                preferred_wav_uri = str(result.get("bucketAudioUri") or "")
                preferred_uri = preferred_mp3_uri or preferred_wav_uri
                preferred_mime = str(
                    result.get("preferredMimeType")
                    or ("audio/mpeg" if preferred_mp3_uri else "audio/wav")
                )
                entry = {
                    **item,
                    "status": "uploaded",
                    "audioPath": "",
                    "mimeType": "",
                    "audioBytes": 0,
                    "mp3Path": "",
                    "preferredAudioPath": preferred_uri,
                    "preferredMimeType": preferred_mime,
                    "wavDeprecated": bool(preferred_mp3_uri),
                    "latencyMs": int(result.get("latencyMs") or 0),
                    "batchMode": str(result.get("batchMode") or "batch-upload"),
                }
                if result.get("batchLatencyMs") is not None:
                    entry["batchLatencyMs"] = result["batchLatencyMs"]
                if result.get("bucketMp3Uri"):
                    entry["mp3Path"] = str(result["bucketMp3Uri"])
                    entry["mp3MimeType"] = "audio/mpeg"
                    entry["bucketMp3Uri"] = str(result["bucketMp3Uri"])
                if result.get("bucketAudioUri"):
                    entry["bucketAudioUri"] = str(result["bucketAudioUri"])
                if result.get("preferredBucketAudioUri"):
                    entry["preferredBucketAudioUri"] = str(result["preferredBucketAudioUri"])
                if result.get("uploadedFilename"):
                    entry["uploadedFilename"] = str(result["uploadedFilename"])
                manifest_entries.append(entry)
                print(f"[{index}/{len(responses)}] uploaded {item['id']} -> {preferred_uri}")
                write_progress(args.progress_json, manifest_entries, len(responses), started_at)

        def flush_pending() -> None:
            if not pending:
                return
            batch = list(pending)
            pending.clear()
            texts = [item["text"] for _, item, _, _ in batch]
            try:
                active_config, active_fn_index, active_reference = ensure_remote_client()
                use_upload_path = bool(
                    args.bucket_uri
                    and contract_summary is not None
                    and contract_summary.get("remoteBucketPipelineReady")
                )
                if use_upload_path:
                    response_ids = [item["id"] for _, item, _, _ in batch]
                    print(f"uploading remote chunk of {len(batch)} response(s) via {indextts_batch_upload_api_name()}")
                    try:
                        if reference is None:
                            raise RuntimeError(
                                "IndexTTS reference upload was not initialized"
                            )
                        results = reference.run(
                            lambda refreshed_reference: direct_batch_upload_synthesis(
                                texts,
                                active_config,
                                refreshed_reference,
                                args.voice_description,
                                args.bucket_uri,
                                response_ids,
                            ),
                            max_retries=2,
                            retry_backoff_seconds=2.0,
                            on_retry=lambda error, attempt: print(
                                "refreshing expired IndexTTS reference before "
                                f"remote retry {attempt}: "
                                f"{type(error).__name__}: {error}"
                            ),
                        )
                        if len(results) != len(batch):
                            raise IndexTTSUploadResultUnverifiableError(
                                "IndexTTS batch upload returned "
                                f"{len(results)} result(s) for "
                                f"{len(batch)} response(s)"
                            )
                        upload_backend = hf_bucket_backend(args.bucket_uri)
                        for result in results:
                            preferred_uri = str(
                                result.get("preferredBucketAudioUri")
                                or result.get("bucketMp3Uri")
                                or result.get("bucketAudioUri")
                                or ""
                            )
                            if not preferred_uri:
                                raise IndexTTSUploadResultUnverifiableError(
                                    "IndexTTS batch upload omitted an "
                                    "authoritative audio URI"
                                )
                            try:
                                validate_indextts_bucket_audio(
                                    upload_backend,
                                    preferred_uri,
                                )
                            except Exception as validation_error:
                                if is_indextts_audio_validation_error(
                                    validation_error
                                ):
                                    raise
                                raise IndexTTSUploadResultUnverifiableError(
                                    "IndexTTS uploaded audio could not be "
                                    "independently validated"
                                ) from validation_error
                    except Exception as exc:
                        if isinstance(exc, IndexTTSQuotaExceededError):
                            raise
                        if (
                            not isinstance(exc, IndexTTSUploadResultUnverifiableError)
                            and not is_indextts_transient_worker_error(exc)
                        ):
                            raise
                        print(
                            f"remote upload chunk was not safely usable; falling back to local generation + canonical bucket sync: "
                            f"{type(exc).__name__}: {exc}"
                        )
                    else:
                        _record_upload_batch_results(batch, results)
                        return
                print(f"processing remote chunk of {len(batch)} response(s)")
                if reference is None:
                    raise RuntimeError(
                        "IndexTTS reference upload was not initialized"
                    )
                results = reference.run(
                    lambda refreshed_reference: synthesize_batch(
                        texts,
                        active_config,
                        active_fn_index,
                        refreshed_reference,
                        args.voice_description,
                        parallel_workers=args.parallel_workers,
                    ),
                    max_retries=2,
                    retry_backoff_seconds=2.0,
                    on_retry=lambda error, attempt: print(
                        "refreshing expired IndexTTS reference before "
                        f"remote retry {attempt}: "
                        f"{type(error).__name__}: {error}"
                    ),
                )
                if len(results) != len(batch):
                    raise RuntimeError(f"IndexTTS batch returned {len(results)} result(s) for {len(batch)} response(s)")
                for (index, item, audio_path, mp3_path), result in zip(batch, results):
                    if result.get("error"):
                        entry = {
                            **item,
                            "status": "failed",
                            "audioPath": "",
                            "mp3Path": "",
                            "error": str(result.get("error") or "Unknown batch failure"),
                            "batchMode": result.get("batchMode", "batch" if len(batch) > 1 else "single"),
                        }
                        for key in ("batchFallbackReason", "batchRequestedSize", "batchExecutedSize", "batchSplitDepth", "retryAfter"):
                            if result.get(key) is not None:
                                entry[key] = result[key]
                        if result.get("retriable"):
                            entry["retriable"] = True
                        manifest_entries.append(entry)
                        print(f"[{index}/{len(responses)}] failed {item['id']}: {entry['error']}")
                        write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                        continue
                    write_audio_bytes_atomic(audio_path, result["audio"])
                    if args.write_mp3:
                        convert_wav_to_mp3(audio_path, mp3_path, bitrate=args.mp3_bitrate, force=True)
                        validate_indextts_generated_audio(
                            mp3_path,
                            mp3_path.read_bytes(),
                        )
                    wav_deleted = maybe_delete_wav(audio_path, mp3_path, delete_wav=args.write_mp3 and args.delete_wav_after_mp3)
                    entry = {
                        **item,
                        "status": "generated_mp3" if wav_deleted else "generated",
                        "audioPath": "" if wav_deleted else display_path(audio_path),
                        "mimeType": "" if wav_deleted else result["mimeType"],
                        "audioBytes": 0 if wav_deleted else file_size(audio_path),
                        "latencyMs": result["latencyMs"],
                        "batchMode": result.get("batchMode", "batch" if len(batch) > 1 else "single"),
                        "wavDeprecated": bool(wav_deleted),
                    }
                    if result.get("batchLatencyMs") is not None:
                        entry["batchLatencyMs"] = result["batchLatencyMs"]
                    if result.get("batchFallbackReason"):
                        entry["batchFallbackReason"] = result["batchFallbackReason"]
                    for key in ("batchRequestedSize", "batchExecutedSize", "batchSplitDepth"):
                        if result.get(key) is not None:
                            entry[key] = result[key]
                    if args.write_mp3 and mp3_path.exists():
                        entry.update(
                            {
                                "mp3Path": display_path(mp3_path),
                                "mp3MimeType": "audio/mpeg",
                                "mp3Bytes": file_size(mp3_path),
                                "preferredAudioPath": display_path(mp3_path),
                                "preferredMimeType": "audio/mpeg",
                            }
                        )
                    else:
                        entry.update({"mp3Path": "", "preferredAudioPath": display_path(audio_path), "preferredMimeType": result["mimeType"]})
                    attach_bucket_audio_uris(entry, args.bucket_uri, prefer_mp3=bool(args.write_mp3))
                    manifest_entries.append(entry)
                    print(f"[{index}/{len(responses)}] generated {mp3_path.name if mp3_path.exists() else audio_path.name}")
                    write_progress(args.progress_json, manifest_entries, len(responses), started_at)
            except Exception as exc:
                retry_after = exc.retry_after if isinstance(exc, IndexTTSQuotaExceededError) else indextts_retry_after_hint(exc)
                retriable = is_indextts_transient_worker_error(exc) or bool(retry_after)
                for index, item, _audio_path, _mp3_path in batch:
                    print(f"[{index}/{len(responses)}] failed {item['id']}: {exc}")
                    manifest_entries.append(
                        {
                            **item,
                            "status": "failed",
                            "audioPath": "",
                            "mp3Path": "",
                            "error": f"{type(exc).__name__}: {exc}",
                            **({"retriable": True} if retriable else {}),
                            **({"retryAfter": retry_after} if retry_after else {}),
                        }
                    )
                    write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                if isinstance(exc, IndexTTSQuotaExceededError) or args.stop_on_error:
                    raise

        for index, item in enumerate(responses, start=1):
            if args.max_runtime_seconds is not None and time.time() - started_at >= args.max_runtime_seconds:
                print(f"[{index}/{len(responses)}] stopping before new work: max runtime reached")
                break
            audio_path = args.output_dir / f"{item['id']}.wav"
            mp3_path = args.output_dir / f"{item['id']}.mp3"
            if not args.force:
                if discard_unacceptable_local_audio_cache(mp3_path):
                    print(f"[{index}/{len(responses)}] dropped invalid audio cache {mp3_path.name}")
                if discard_unacceptable_local_audio_cache(audio_path):
                    print(f"[{index}/{len(responses)}] dropped invalid audio cache {audio_path.name}")
            if not audio_path.exists() and mp3_path.exists() and not args.force:
                entry = {
                    **item,
                    "status": "cached_mp3",
                    "audioPath": "",
                    "mimeType": "",
                    "audioBytes": 0,
                    "mp3Path": display_path(mp3_path),
                    "mp3MimeType": "audio/mpeg",
                    "mp3Bytes": file_size(mp3_path),
                    "preferredAudioPath": display_path(mp3_path),
                    "preferredMimeType": "audio/mpeg",
                    "wavDeprecated": True,
                }
                attach_bucket_audio_uris(entry, args.bucket_uri, prefer_mp3=bool(args.write_mp3))
                manifest_entries.append(entry)
                print(f"[{index}/{len(responses)}] cached {mp3_path.name}")
                write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                continue
            if audio_path.exists() and not args.force:
                if args.write_mp3:
                    convert_wav_to_mp3(audio_path, mp3_path, bitrate=args.mp3_bitrate, force=False)
                    validate_indextts_generated_audio(
                        mp3_path,
                        mp3_path.read_bytes(),
                    )
                wav_deleted = maybe_delete_wav(audio_path, mp3_path, delete_wav=args.write_mp3 and args.delete_wav_after_mp3)
                entry = {
                    **item,
                    "status": "cached_mp3" if wav_deleted else "cached",
                    "audioPath": "" if wav_deleted else display_path(audio_path),
                    "mimeType": "" if wav_deleted else "audio/wav",
                    "audioBytes": 0 if wav_deleted else file_size(audio_path),
                    "wavDeprecated": bool(wav_deleted),
                }
                if args.write_mp3 and mp3_path.exists():
                    entry.update(
                        {
                            "mp3Path": display_path(mp3_path),
                            "mp3MimeType": "audio/mpeg",
                            "mp3Bytes": file_size(mp3_path),
                            "preferredAudioPath": display_path(mp3_path),
                            "preferredMimeType": "audio/mpeg",
                        }
                    )
                else:
                    entry.update({"mp3Path": "", "preferredAudioPath": display_path(audio_path), "preferredMimeType": "audio/wav"})
                attach_bucket_audio_uris(entry, args.bucket_uri, prefer_mp3=bool(args.write_mp3))
                manifest_entries.append(entry)
                print(f"[{index}/{len(responses)}] cached {audio_path.name}")
                write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                continue
            if not args.force and args.bucket_uri:
                cached_bucket_entry = cached_bucket_audio_entry(
                    item,
                    bucket_uri=args.bucket_uri,
                    prefer_mp3=bool(args.write_mp3),
                )
                if cached_bucket_entry is not None:
                    manifest_entries.append(cached_bucket_entry)
                    print(f"[{index}/{len(responses)}] cached bucket {item['id']}")
                    write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                    continue
            print(f"[{index}/{len(responses)}] queued {item['id']}: {item['text']}")
            pending.append((index, item, audio_path, mp3_path))
            if len(pending) >= remote_batch_size:
                try:
                    flush_pending()
                except Exception as exc:
                    fatal_exception = exc
                    break
        if pending:
            try:
                flush_pending()
            except Exception as exc:
                fatal_exception = exc

    payload = {
        "schemaVersion": 1,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": indextts_model_name(),
        "spaceUrl": indextts_base_url(),
        "referenceAudio": str(args.reference_audio),
        "voiceDescription": args.voice_description,
        "responseCount": len(manifest_entries),
        "sources": {
            "dag": "" if args.response_manifest is not None else str(args.dag),
            "results": "" if args.response_manifest is not None else str(args.results),
            "responseManifest": str(args.response_manifest) if args.response_manifest is not None else "",
            "slottedResponseIndex": str(args.slotted_response_index) if args.slotted_response_index.exists() else "",
            "includeAssistantResponses": include_assistant,
            "includeVoiceResponses": include_voice,
            "idScheme": "abby-tts-{sha256(spoken_normalized_text)[:20]}",
        },
        "normalization": {
            "emergencyNumbers": {
                "211": "two one one",
                "911": "nine one one",
            },
            "addresses": {
                "directions": _ADDRESS_DIRECTION_WORDS,
                "streetSuffixes": _STREET_SUFFIX_WORDS,
                "unitLabels": _UNIT_WORDS,
                "numberedStreetOrdinals": True,
            },
        },
        "mp3": {
            "enabled": bool(args.write_mp3),
            "bitrate": args.mp3_bitrate,
            "preferred": bool(args.write_mp3),
            "wavDeprecated": bool(args.write_mp3 and args.delete_wav_after_mp3),
        },
        "batchInference": {
            "remoteBatchSize": max(1, int(args.remote_batch_size or 1)),
            "parallelWorkers": max(1, int(args.parallel_workers or 1)),
            "batchApiName": indextts_batch_api_name(),
            "enabled": os.getenv("WALLET_INDEXTTS_BATCH_ENABLED", "1").strip().lower() not in {"0", "false", "no"},
            "requiresBatch": os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "").strip().lower() in {"1", "true", "yes"},
        },
        "responses": manifest_entries,
    }
    bucket_targets = bucket_sync_targets(args.bucket_uri)
    if bucket_targets:
        payload["bucketUpload"] = {
            **bucket_targets,
            "enabled": True,
            "tool": "hf sync",
            "sourceOfTruth": "bucket",
        }
    if isinstance(fatal_exception, IndexTTSQuotaExceededError):
        payload["batchInference"]["rateLimitDetected"] = {
            "type": type(fatal_exception).__name__,
            "message": str(fatal_exception),
            "retryAfter": fatal_exception.retry_after,
        }
    if not args.dry_run and 'contract_summary' in locals() and contract_summary is not None:
        payload["batchInference"]["contract"] = contract_summary
    if args.validate_transcripts:
        payload["transcriptValidation"] = validate_audio_manifest_entries(
            manifest_entries,
            limit=args.transcript_validation_limit,
            model_name=args.transcript_validation_model,
            language=args.transcript_validation_language,
            device=args.transcript_validation_device,
            similarity_threshold=args.transcript_validation_threshold,
        )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.public_manifest.parent.mkdir(parents=True, exist_ok=True)
    public_payload = {
        **payload,
        "referenceAudio": "abby-reference.wav",
        "responses": [
            {
                **entry,
                "audioUrl": audio_url_for(str(entry.get("audioPath") or "")),
                "mp3Url": audio_url_for(str(entry.get("mp3Path") or "")),
                "preferredAudioUrl": audio_url_for(str(entry.get("preferredAudioPath") or entry.get("audioPath") or "")),
            }
            for entry in manifest_entries
        ],
    }
    args.public_manifest.write_text(json.dumps(public_payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.manifest}")
    print(f"Wrote {args.public_manifest}")
    if bucket_targets and not args.dry_run:
        sync_summary = sync_generated_outputs_to_bucket(args.output_dir, args.manifest, args.public_manifest, args.bucket_uri)
        print(f"Synced generated audio to {sync_summary['audioUri']}")
        print(f"Synced manifests to {sync_summary['metadataUri']}")
        if getattr(args, "prune_local_audio_after_sync", False):
            pruned = 0
            for audio_file in args.output_dir.glob("abby-tts-*"):
                if audio_file.suffix.lower() in {".wav", ".mp3"}:
                    audio_file.unlink(missing_ok=True)
                    pruned += 1
            if pruned:
                print(f"Pruned {pruned} local audio file(s) from {display_path(args.output_dir)} after bucket sync.")
    if fatal_exception is not None:
        raise fatal_exception
    if args.validate_transcripts and payload["transcriptValidation"]["failureCount"] and not args.transcript_validation_soft_fail:
        failure_summary = payload["transcriptValidation"]["failures"]
        raise RuntimeError(f"Transcript validation failed for {len(failure_summary)} audio file(s): {failure_summary}")


if __name__ == "__main__":
    try:
        main()
    except IndexTTSQuotaExceededError as exc:
        print(f"IndexTTS quota exhausted: {exc}", file=sys.stderr)
        raise SystemExit(75) from exc
