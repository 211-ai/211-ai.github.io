# ruff: noqa: E501
"""IndexTTS / Gradio / Whisper / voice-reply / speech-normalisation helpers."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import io
import json
import math
import mimetypes
import os
import re
import struct
import threading
import time
import uuid
import wave
import zipfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: E402

from ipfs_accelerate_py import HFSpaceClient  # noqa: E402

from ._app import _prepare_hf_router_environment  # noqa: E402


def _indextts_space_base_url() -> str:
    override = str(getattr(_INDEXTTS_ACTIVE_SPACE_URL, "value", "") or "").strip().rstrip("/")
    if override:
        return override
    return os.getenv("WALLET_INDEXTTS_SPACE_URL", "https://publicus-indextts-2-demo.hf.space").strip().rstrip("/")


def _indextts_fallback_space_base_url() -> str:
    return os.getenv("WALLET_INDEXTTS_FALLBACK_SPACE_URL", "https://indexteam-indextts-2-demo.hf.space").strip().rstrip("/")


def _indextts_space_base_urls() -> list[str]:
    urls: list[str] = []
    for candidate in (_indextts_space_base_url(), _indextts_fallback_space_base_url()):
        normalized = str(candidate or "").strip().rstrip("/")
        if normalized and normalized not in urls:
            urls.append(normalized)
    return urls


def _indextts_model_name() -> str:
    primary_model = os.getenv("WALLET_INDEXTTS_MODEL_NAME", "Publicus/IndexTTS-2-Demo").strip()
    fallback_model = os.getenv("WALLET_INDEXTTS_FALLBACK_MODEL_NAME", "IndexTeam/IndexTTS-2-Demo").strip()
    active_space = _indextts_space_base_url().strip().rstrip("/")
    if active_space and active_space == _indextts_fallback_space_base_url():
        return fallback_model or primary_model
    return primary_model


def _indextts_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_API_NAME", "gen_single").strip()


def _indextts_batch_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", "gen_batch").strip()


def _indextts_timeout_seconds() -> float:
    override = getattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value", None)
    if override is not None:
        try:
            return max(5.0, float(override))
        except Exception:
            pass
    try:
        return max(5.0, float(os.getenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "180")))
    except Exception:
        return 180.0


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
    def replace_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            return match.group(0)
        return f"{_digits_to_words(digits[:3])}, {_digits_to_words(digits[3:6])}, {_digits_to_words(digits[6:])}"

    return re.sub(
        r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b",
        replace_phone,
        text,
    )


def _normalize_phone_extensions(text: str) -> str:
    return re.sub(
        r"\b(?:ext\.?|extension|x)\s*#?\s*(?P<extension>\d{1,6})\b",
        lambda match: f"extension {_digits_to_words(match.group('extension'))}",
        text,
        flags=re.IGNORECASE,
    )


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


def _normalize_indextts_spoken_text(text: str) -> str:
    spoken = _strip_scraped_page_chrome(text)
    spoken = _strip_unspoken_fields(spoken)
    spoken = _strip_coordinates(spoken)
    spoken = _normalize_record_list_sentence(spoken)
    spoken = _normalize_urls_for_speech(spoken)
    spoken = _normalize_phone_numbers(spoken)
    spoken = _normalize_phone_extensions(spoken)
    spoken = _normalize_percentages_and_currency(spoken)
    spoken = _normalize_hours_and_separators(spoken)
    spoken = re.sub(r"\bST\s+(?=[A-Z])", "Saint ", spoken)
    spoken = re.sub(r"(?i)\ba grounded\s+211\s+match\s+is\b", "I found", spoken)
    spoken = re.sub(r"(?i)\ba grounded\s+two one one\s+match\s+is\b", "I found", spoken)
    spoken = re.sub(r"(?i)\bgrounded detail\b", "detail", spoken)
    spoken = re.sub(r"(?i)\b211[\s-]?ai\b", "two one one AI", spoken)
    spoken = re.sub(r"(?i)\b211[\s-]?info\b", "two one one info", spoken)
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


def _indextts_headers(*, accept: str = "application/json") -> dict[str, str]:
    headers = {"Accept": accept}
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
    if token:
        headers["Authorization"] = f"Bearer {token}"
    bill_to = (
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    return headers


def _configured_hf_token() -> str:
    return (
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


def _publicus_indextts_credential_warning() -> dict[str, Any] | None:
    space_url = _indextts_space_base_url().lower()
    if "publicus-indextts" not in space_url and "publicus/indextts" not in (os.getenv("WALLET_INDEXTTS_MODEL_NAME", "").lower()):
        return None
    token_present = bool(_configured_hf_token())
    if token_present:
        return None
    bill_to = (
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip() or "publicus"
    return {
        "code": "publicus_indextts_missing_hf_token",
        "message": (
            "Publicus IndexTTS is configured without a Hugging Face token. "
            "Set WALLET_INDEXTTS_HF_TOKEN or HF_TOKEN and keep X-HF-Bill-To set to the Publicus account."
        ),
        "spaceUrl": _indextts_space_base_url(),
        "modelName": os.getenv("WALLET_INDEXTTS_MODEL_NAME", "Publicus/IndexTTS-2-Demo"),
        "billTo": bill_to,
        "envVars": ["WALLET_INDEXTTS_HF_TOKEN", "HF_TOKEN", "WALLET_INDEXTTS_HF_BILL_TO"],
    }


def _voice_proxy_runtime_warnings() -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    publicus_warning = _publicus_indextts_credential_warning()
    if publicus_warning:
        warnings.append(publicus_warning)
    return warnings


def _http_json(method: str, url: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = _indextts_headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{url} did not return a JSON object")
    return parsed


def _http_bytes(url: str) -> tuple[bytes, str]:
    request = urllib_request.Request(url, headers=_indextts_headers(accept="audio/*, application/octet-stream"))
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        return response.read(), response.headers.get("Content-Type") or "audio/wav"


_INDEXTTS_CACHE_LOCK = threading.Lock()
_INDEXTTS_CONFIG_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_INDEXTTS_FN_INDEX_CACHE: dict[tuple[str, str], int] = {}
_INDEXTTS_REFERENCE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def _voice_llm_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_VOICE_LLM_TIMEOUT_SECONDS", "20")))
    except Exception:
        return 20.0


def _clean_voice_reply_text(text: str, *, prompt: str = "", fallback_text: str = "") -> str:
    cleaned = str(text or "").strip()
    prompt = str(prompt or "").strip()
    if prompt and cleaned.startswith(prompt):
        cleaned = cleaned[len(prompt) :].strip()
    for marker in ("Assistant:", "Abby:", "Response:", "Answer:"):
        index = cleaned.rfind(marker)
        if index >= 0:
            cleaned = cleaned[index + len(marker) :].strip()
            break
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = str(fallback_text or "").strip()
    max_chars = 520
    if len(cleaned) > max_chars:
        trimmed = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
        cleaned = trimmed or cleaned[:max_chars].strip()
    return cleaned


def _generate_indextts_voice_reply_text(
    *,
    mode: str,
    text: str,
    system_prompt: str | None,
    user_prompt: str | None,
    fallback_text: str | None,
) -> tuple[str, dict[str, Any]]:
    timings: dict[str, Any] = {}
    fallback = str(fallback_text or "").strip()
    prompt = str(text or "").strip()
    if str(mode or "").strip().lower() != "voice-reply":
        reply_text = prompt or fallback
        if not reply_text:
            raise ValueError("text is required")
        return reply_text, timings

    user_text = str(user_prompt or "").strip()
    system_text = str(system_prompt or "").strip()
    if not prompt:
        prompt = "\n\n".join(part for part in (system_text, f"Caller request: {user_text}" if user_text else "") if part)
    if not prompt:
        raise ValueError("text or user_prompt is required")

    llm_start = time.perf_counter()
    try:
        kwargs = _prepare_hf_router_environment(
            {
                "max_new_tokens": int(os.getenv("WALLET_VOICE_LLM_MAX_NEW_TOKENS", "120")),
                "temperature": float(os.getenv("WALLET_VOICE_LLM_TEMPERATURE", "0.2")),
                "timeout": _voice_llm_timeout_seconds(),
            }
        )
        from ipfs_datasets_py import llm_router  # noqa: WPS433

        provider = os.getenv("WALLET_VOICE_LLM_PROVIDER", "hf_inference_api").strip() or "hf_inference_api"
        model_name = (
            os.getenv("WALLET_VOICE_LLM_MODEL")
            or os.getenv("WALLET_AI_ROUTER_LLM_MODEL")
            or "Qwen/Qwen3.5-2B"
        ).strip()
        generated = llm_router.generate_text(
            prompt,
            model_name=model_name,
            provider=provider,
            **kwargs,
        )
        timings["llm_request_ms"] = max(0, int((time.perf_counter() - llm_start) * 1000))
        timings["llm_provider"] = provider
        timings["llm_model"] = model_name
        return _clean_voice_reply_text(generated, prompt=prompt, fallback_text=fallback), timings
    except Exception as exc:
        timings["llm_request_ms"] = max(0, int((time.perf_counter() - llm_start) * 1000))
        timings["llm_error"] = str(exc)[:240]
        if fallback:
            return fallback, timings
        raise


def _indextts_cache_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("WALLET_INDEXTTS_CACHE_TTL_SECONDS", "3600")))
    except Exception:
        return 3600.0


_INDEXTTS_SPACE_CLIENT: HFSpaceClient | None = None
_INDEXTTS_SPACE_CLIENT_KEY = ""
_INDEXTTS_ACTIVE_SPACE_URL = threading.local()
_INDEXTTS_ACTIVE_TIMEOUT_SECONDS = threading.local()
_INDEXTTS_FAST_FAIL_MODE = threading.local()
_INDEXTTS_FORCE_REQUIRE_BATCH = threading.local()


@contextmanager
def _indextts_use_space_base_url(base_url: str):
    previous = getattr(_INDEXTTS_ACTIVE_SPACE_URL, "value", None)
    _INDEXTTS_ACTIVE_SPACE_URL.value = str(base_url or "").strip().rstrip("/")
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(_INDEXTTS_ACTIVE_SPACE_URL, "value")
            except AttributeError:
                pass
        else:
            _INDEXTTS_ACTIVE_SPACE_URL.value = previous


@contextmanager
def _indextts_use_timeout_seconds(seconds: float | None):
    previous = getattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value", None)
    _INDEXTTS_ACTIVE_TIMEOUT_SECONDS.value = None if seconds is None else float(seconds)
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value")
            except AttributeError:
                pass
        else:
            _INDEXTTS_ACTIVE_TIMEOUT_SECONDS.value = previous


def _indextts_attempt_timeout_seconds(space_index: int, total_spaces: int) -> float:
    default_timeout = _indextts_timeout_seconds()
    if total_spaces > 1 and space_index == 0:
        return min(default_timeout, 20.0)
    if total_spaces > 1 and space_index == total_spaces - 1:
        return min(default_timeout, 45.0)
    return default_timeout


def _indextts_degraded_fast_fail_enabled() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_DEGRADED_FAST_FAIL", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


@contextmanager
def _indextts_fast_fail_mode(enabled: bool):
    previous = getattr(_INDEXTTS_FAST_FAIL_MODE, "value", False)
    _INDEXTTS_FAST_FAIL_MODE.value = bool(enabled)
    try:
        yield
    finally:
        _INDEXTTS_FAST_FAIL_MODE.value = previous


def _indextts_is_fast_fail_mode() -> bool:
    return bool(getattr(_INDEXTTS_FAST_FAIL_MODE, "value", False))


@contextmanager
def _indextts_force_require_batch(enabled: bool):
    previous = getattr(_INDEXTTS_FORCE_REQUIRE_BATCH, "value", False)
    _INDEXTTS_FORCE_REQUIRE_BATCH.value = bool(enabled)
    try:
        yield
    finally:
        _INDEXTTS_FORCE_REQUIRE_BATCH.value = previous


def _indextts_require_batch_mode() -> bool:
    if bool(getattr(_INDEXTTS_FORCE_REQUIRE_BATCH, "value", False)):
        return True
    return str(os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "")).strip().lower() in {"1", "true", "yes"}


def _indextts_space_client() -> HFSpaceClient:
    global _INDEXTTS_SPACE_CLIENT
    global _INDEXTTS_SPACE_CLIENT_KEY
    cache_key = "|".join(
        [
            _indextts_space_base_url(),
            str(_indextts_timeout_seconds()),
            os.getenv("WALLET_INDEXTTS_API_NAME", ""),
            os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", ""),
            os.getenv("WALLET_INDEXTTS_HF_BILL_TO", ""),
            os.getenv("IPFS_DATASETS_PY_HF_BILL_TO", ""),
            os.getenv("HF_TOKEN", ""),
            os.getenv("HUGGINGFACEHUB_API_TOKEN", ""),
            os.getenv("IPFS_DATASETS_PY_HF_API_TOKEN", ""),
        ]
    )
    if _INDEXTTS_SPACE_CLIENT is not None and cache_key == _INDEXTTS_SPACE_CLIENT_KEY:
        return _INDEXTTS_SPACE_CLIENT
    _INDEXTTS_SPACE_CLIENT = HFSpaceClient(
        _indextts_space_base_url(),
        timeout_seconds=_indextts_timeout_seconds(),
        headers_factory=lambda: _indextts_headers(),
    )
    _INDEXTTS_SPACE_CLIENT_KEY = cache_key
    return _INDEXTTS_SPACE_CLIENT


def _indextts_config() -> dict[str, Any]:
    cache_key = (_indextts_space_base_url(), _indextts_api_name())
    now = time.time()
    with _INDEXTTS_CACHE_LOCK:
        cached = _INDEXTTS_CONFIG_CACHE.get(cache_key)
        if cached and now - float(cached.get("created_at", 0)) < _indextts_cache_ttl_seconds():
            return dict(cached["config"])
    config = _indextts_space_client().get_config()
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_CONFIG_CACHE[cache_key] = {"created_at": now, "config": dict(config)}
    return config


def _indextts_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    cache_key = (_indextts_space_base_url(), _indextts_api_name())
    with _INDEXTTS_CACHE_LOCK:
        if cache_key in _INDEXTTS_FN_INDEX_CACHE:
            return _INDEXTTS_FN_INDEX_CACHE[cache_key]
    api_name = _indextts_api_name()
    try:
        fn_index = int(
            _indextts_space_client().resolve_fn_index(
                api_name,
                config,
                fallback_markers=("tts", "synth", "generate", "infer", "predict"),
            )
        )
    except Exception as exc:
        raise ValueError(f"IndexTTS api_name {api_name!r} was not found in Gradio config") from exc
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_FN_INDEX_CACHE[cache_key] = fn_index
    return fn_index


def _indextts_batch_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_BATCH_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    api_name = _indextts_batch_api_name()
    if not api_name:
        raise ValueError("WALLET_INDEXTTS_BATCH_API_NAME is empty")
    cache_key = (_indextts_space_base_url(), f"batch:{api_name}")
    with _INDEXTTS_CACHE_LOCK:
        if cache_key in _INDEXTTS_FN_INDEX_CACHE:
            return _INDEXTTS_FN_INDEX_CACHE[cache_key]
    try:
        fn_index = int(_indextts_space_client().resolve_fn_index(api_name, config))
    except Exception as exc:
        raise ValueError(f"IndexTTS batch api_name {api_name!r} was not found in Gradio config") from exc
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_FN_INDEX_CACHE[cache_key] = fn_index
    return fn_index


def _indextts_queue_join(fn_index: int, data: Sequence[Any]) -> str:
    return _indextts_space_client().queue_join(int(fn_index), list(data))


def _is_opaque_indextts_queue_failure(detail: str) -> bool:
    normalized = str(detail or "").lower()
    return "space queue failed" in normalized and (
        "error=null" in normalized or "{'error': none}" in normalized
    )


def _indextts_allow_direct_predict_fallback() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_ALLOW_DIRECT_PREDICT_FALLBACK", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _indextts_execute_with_queue_fallback(
    *,
    fn_index: int,
    data: Sequence[Any],
    timings: dict[str, Any],
    api_name: str,
) -> Mapping[str, Any]:
    stage_start = time.perf_counter()
    session_hash = _indextts_queue_join(fn_index, data)
    timings["queue_join_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))

    stage_start = time.perf_counter()
    queue_error: Exception | None = None
    should_retry_queue = True
    try:
        result = _indextts_wait_for_result(session_hash)
        timings["queue_wait_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        timings["result_path"] = "queue"
        return result
    except Exception as exc:
        timings["queue_wait_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        timings["queue_error"] = str(exc)
        if _indextts_is_fast_fail_mode():
            raise
        if not _indextts_allow_direct_predict_fallback():
            raise
        if not _is_opaque_indextts_queue_failure(str(exc)):
            should_retry_queue = False
        queue_error = exc

    if _indextts_is_fast_fail_mode():
        if queue_error is not None:
            raise queue_error
        raise ValueError("IndexTTS fast-fail mode reached fallback guard without queue error")

    if _indextts_degraded_fast_fail_enabled():
        if queue_error is not None:
            raise queue_error
        raise ValueError("IndexTTS degraded fast-fail mode reached fallback guard without queue error")

    if should_retry_queue:
        # Opaque queue failures are commonly transient. Retry one fresh queue session
        # before using direct predict as a compatibility fallback.
        retry_start = time.perf_counter()
        retry_session_hash = _indextts_queue_join(fn_index, data)
        timings["queue_retry_join_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
        retry_start = time.perf_counter()
        try:
            result = _indextts_wait_for_result(retry_session_hash)
            timings["queue_retry_wait_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
            timings["result_path"] = "queue-retry"
            return result
        except Exception as retry_exc:
            timings["queue_retry_wait_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
            timings["queue_retry_error"] = str(retry_exc)
            if not _is_opaque_indextts_queue_failure(str(retry_exc)):
                raise
            queue_error = retry_exc

    api_name_fallback_start = time.perf_counter()
    try:
        api_name_result = _indextts_space_client().call_api_name(
            api_name,
            data,
            timeout_seconds=_indextts_timeout_seconds(),
            poll_interval_seconds=0.5,
        )
        timings["api_name_fallback_ms"] = max(0, int((time.perf_counter() - api_name_fallback_start) * 1000))
        timings["result_path"] = "api-name-fallback"
        return api_name_result if isinstance(api_name_result, Mapping) else {"data": api_name_result}
    except Exception as api_name_exc:
        timings["api_name_fallback_ms"] = max(0, int((time.perf_counter() - api_name_fallback_start) * 1000))
        timings["api_name_fallback_error"] = str(api_name_exc)

    direct_start = time.perf_counter()
    try:
        direct_result = _indextts_space_client().call_endpoint(fn_index, data)
        timings["direct_predict_ms"] = max(0, int((time.perf_counter() - direct_start) * 1000))
        timings["result_path"] = "direct-predict-fallback"
        return {"data": direct_result if isinstance(direct_result, list) else [direct_result]}
    except Exception as direct_predict_exc:
        timings["direct_predict_ms"] = max(0, int((time.perf_counter() - direct_start) * 1000))
        timings["direct_predict_error"] = str(direct_predict_exc)
        if queue_error is not None:
            raise queue_error
        raise


def _indextts_degraded_error_payload(exc: Exception, operation: str) -> dict[str, Any]:
    return {
        "code": "indextts_temporarily_unavailable",
        "message": "IndexTTS is temporarily unavailable across configured spaces.",
        "operation": operation,
        "retryable": True,
        "degraded": True,
        "fallbackRecommended": "local-audio",
        "detail": str(exc),
        "spaceUrls": _indextts_space_base_urls(),
    }


def _indextts_endpoint_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS", "95")))
    except Exception:
        return 95.0


def _indextts_endpoint_retry_count() -> int:
    try:
        return max(0, min(2, int(os.getenv("WALLET_INDEXTTS_ENDPOINT_RETRIES", "1"))))
    except Exception:
        return 1


def _run_indextts_with_endpoint_timeout(operation: str, fn):
    timeout_seconds = _indextts_endpoint_timeout_seconds()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(f"IndexTTS {operation} exceeded endpoint timeout ({timeout_seconds:.0f}s)") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _run_indextts_with_endpoint_retry(operation: str, fn):
    retries = _indextts_endpoint_retry_count()
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _run_indextts_with_endpoint_timeout(operation, fn)
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            # Short pause before retrying to avoid immediately re-hitting a transient failure.
            time.sleep(0.2)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"IndexTTS {operation} failed without an explicit error")


def _run_indextts_gradio_tts(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    errors_by_space: dict[str, str] = {}
    space_urls = _indextts_space_base_urls()
    for index, space_url in enumerate(space_urls):
        with _indextts_use_space_base_url(space_url), _indextts_use_timeout_seconds(
            _indextts_attempt_timeout_seconds(index, len(space_urls))
        ), _indextts_fast_fail_mode(index < (len(space_urls) - 1)):
            try:
                return _run_indextts_gradio_tts_for_space(
                    text=text,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            except Exception as exc:
                last_error = exc
                errors_by_space[space_url] = str(exc)
                continue
    detail = "; ".join(f"{url}: {message}" for url, message in errors_by_space.items())
    if last_error is not None:
        raise ValueError(f"IndexTTS failed across configured spaces ({detail})") from last_error
    raise ValueError("IndexTTS failed: no configured spaces available")


def _run_indextts_gradio_tts_for_space(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    total_start = time.perf_counter()
    timings: dict[str, Any] = {}
    raw_prompt = str(text or "").strip()
    if not raw_prompt:
        raise ValueError("text is required")
    prompt = _normalize_indextts_spoken_text(raw_prompt)
    stage_start = time.perf_counter()
    config = _indextts_config()
    timings["config_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    uploaded_reference = _indextts_upload_reference_audio(reference_audio, reference_audio_name, reference_audio_mime_type)
    timings["reference_upload_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    fn_index = _indextts_fn_index(config)
    timings["fn_index_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    data = _indextts_request_data(
        text=prompt,
        voice_description=voice_description,
        reference_audio=uploaded_reference,
    )
    result = _indextts_execute_with_queue_fallback(
        fn_index=fn_index,
        data=data,
        timings=timings,
        api_name=_indextts_api_name(),
    )
    audio_ref = _find_gradio_audio_reference(result)
    if not audio_ref:
        # Some Space revisions return batch-shaped outputs (including zip bundles)
        # even for single-item invocations. Reuse batch extraction and keep the
        # first generated audio to preserve the single-route contract.
        batch_refs = _indextts_batch_audio_references(result)
        if batch_refs:
            audio_ref = batch_refs[0]
    if not audio_ref:
        raise ValueError("IndexTTS completed without an audio file in the Gradio output")
    stage_start = time.perf_counter()
    audio_bytes, mime_type = _fetch_gradio_file(audio_ref)
    timings["file_fetch_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
        mime_type = "audio/wav"
    timings["total_ms"] = max(0, int((time.perf_counter() - total_start) * 1000))
    return {
        "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
        "mimeType": mime_type or "audio/wav",
        "model": _indextts_model_name(),
        "spaceUrl": _indextts_space_base_url(),
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus",
        "referenceAudio": str(uploaded_reference.get("orig_name") or uploaded_reference.get("path") or "")
        if isinstance(uploaded_reference, Mapping)
        else "",
        "text": prompt,
        "originalText": raw_prompt if raw_prompt != prompt else "",
        "latency": timings,
    }


def _run_indextts_gradio_batch_tts(
    *,
    texts: Sequence[str],
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    errors_by_space: dict[str, str] = {}
    space_urls = _indextts_space_base_urls()
    for index, space_url in enumerate(space_urls):
        with _indextts_use_space_base_url(space_url), _indextts_use_timeout_seconds(
            _indextts_attempt_timeout_seconds(index, len(space_urls))
        ), _indextts_fast_fail_mode(index < (len(space_urls) - 1)):
            try:
                return _run_indextts_gradio_batch_tts_for_space(
                    texts=texts,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            except Exception as exc:
                last_error = exc
                errors_by_space[space_url] = str(exc)
                continue
    detail = "; ".join(f"{url}: {message}" for url, message in errors_by_space.items())
    if last_error is not None:
        raise ValueError(f"IndexTTS batch failed across configured spaces ({detail})") from last_error
    raise ValueError("IndexTTS batch failed: no configured spaces available")


def _run_indextts_gradio_batch_tts_for_space(
    *,
    texts: Sequence[str],
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    total_start = time.perf_counter()
    raw_prompts = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not raw_prompts:
        raise ValueError("texts is required")
    prompts = [_normalize_indextts_spoken_text(text) for text in raw_prompts]
    config = _indextts_config()
    uploaded_reference = _indextts_upload_reference_audio(reference_audio, reference_audio_name, reference_audio_mime_type)
    timings: dict[str, Any] = {}
    try:
        stage_start = time.perf_counter()
        fn_index = _indextts_batch_fn_index(config)
        timings["batch_fn_index_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        data = _indextts_batch_request_data(
            texts=prompts,
            voice_description=voice_description,
            reference_audio=uploaded_reference,
        )
        result = _indextts_execute_with_queue_fallback(
            fn_index=fn_index,
            data=data,
            timings=timings,
            api_name=_indextts_batch_api_name(),
        )
        audio_refs = _indextts_batch_audio_references(result)
        if len(audio_refs) < len(prompts):
            raise ValueError(f"IndexTTS batch returned {len(audio_refs)} audio files for {len(prompts)} texts")
        items: list[dict[str, Any]] = []
        fetch_start = time.perf_counter()
        for index, audio_ref in enumerate(audio_refs[: len(prompts)]):
            audio_bytes, mime_type = _fetch_gradio_file(audio_ref)
            if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
                mime_type = "audio/wav"
            items.append(
                {
                    "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mimeType": mime_type or "audio/wav",
                    "text": prompts[index],
                    "originalText": raw_prompts[index] if raw_prompts[index] != prompts[index] else "",
                }
            )
        timings["file_fetch_ms"] = max(0, int((time.perf_counter() - fetch_start) * 1000))
        mode = "batch"
    except Exception as exc:
        if _indextts_require_batch_mode():
            raise
        fallback_start = time.perf_counter()
        items = [
            _run_indextts_gradio_tts_for_space(
                text=raw_prompt,
                voice_description=voice_description,
                reference_audio=reference_audio,
                reference_audio_name=reference_audio_name,
                reference_audio_mime_type=reference_audio_mime_type,
            )
            for raw_prompt in raw_prompts
        ]
        timings["sequential_fallback_ms"] = max(0, int((time.perf_counter() - fallback_start) * 1000))
        mode = "sequential-fallback"
        timings["batch_error"] = str(exc)
    timings["total_ms"] = max(0, int((time.perf_counter() - total_start) * 1000))
    return {
        "items": items,
        "batchSize": len(items),
        "mode": mode,
        "model": _indextts_model_name(),
        "spaceUrl": _indextts_space_base_url(),
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus",
        "latency": timings,
    }


def _indextts_single_batch_fallback_enabled() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_SINGLE_BATCH_FALLBACK", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _run_indextts_tts_with_batch_fallback(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    try:
        return _run_indextts_gradio_tts(
            text=text,
            voice_description=voice_description,
            reference_audio=reference_audio,
            reference_audio_name=reference_audio_name,
            reference_audio_mime_type=reference_audio_mime_type,
        )
    except Exception as single_exc:
        if not _indextts_single_batch_fallback_enabled():
            raise
        try:
            with _indextts_force_require_batch(True):
                batch = _run_indextts_gradio_batch_tts(
                    texts=[text],
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
        except Exception as batch_exc:
            raise ValueError(
                f"IndexTTS single failed and batch fallback failed: single={single_exc}; batch={batch_exc}"
            ) from batch_exc
        items = batch.get("items") if isinstance(batch, Mapping) else None
        if not isinstance(items, list) or not items:
            raise ValueError("IndexTTS batch fallback returned no items") from single_exc
        first_item = items[0] if isinstance(items[0], Mapping) else {}
        response: dict[str, Any] = {
            "audioBase64": str(first_item.get("audioBase64") or ""),
            "mimeType": str(first_item.get("mimeType") or "audio/wav"),
            "model": str(batch.get("model") or _indextts_model_name()) if isinstance(batch, Mapping) else _indextts_model_name(),
            "spaceUrl": str(batch.get("spaceUrl") or _indextts_space_base_url()) if isinstance(batch, Mapping) else _indextts_space_base_url(),
            "provider": str(batch.get("provider") or "huggingface-zero-gpu-gradio") if isinstance(batch, Mapping) else "huggingface-zero-gpu-gradio",
            "billTo": str(batch.get("billTo") or os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus")
            if isinstance(batch, Mapping)
            else (os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus"),
            "referenceAudio": "",
            "text": str(first_item.get("text") or text),
            "originalText": str(first_item.get("originalText") or ""),
            "latency": {
                "result_path": "single-batch-fallback",
                "single_error": str(single_exc),
                "batch_latency": dict(batch.get("latency") or {}) if isinstance(batch, Mapping) else {},
            },
        }
        if not response["audioBase64"]:
            raise ValueError("IndexTTS batch fallback did not return audioBase64") from single_exc
        return response


def _indextts_upload_reference_audio(
    audio: bytes | None,
    file_name: str | None,
    mime_type: str | None = None,
) -> dict[str, Any] | None:
    if audio:
        guessed_type = mime_type or mimetypes.guess_type(file_name or "")[0] or "audio/wav"
        parsed = _indextts_space_client().upload_file(file_name or "reference.wav", audio, guessed_type)
        upload_path = _first_upload_path(parsed)
        if not upload_path:
            raise RuntimeError("IndexTTS upload did not return a reference path")
        return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(file_name or "reference.wav")}
    path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_PATH", "").strip()
    if path and os.path.exists(path):
        stat = os.stat(path)
        cache_key = (os.path.abspath(path), f"{stat.st_mtime_ns}:{stat.st_size}")
        with _INDEXTTS_CACHE_LOCK:
            cached = _INDEXTTS_REFERENCE_CACHE.get(cache_key)
            if cached:
                return dict(cached)
        with open(path, "rb") as handle:
            data = handle.read()
        mime_type = mimetypes.guess_type(path)[0] or "audio/wav"
        parsed = _indextts_space_client().upload_file(os.path.basename(path), data, mime_type)
        upload_path = _first_upload_path(parsed)
        if not upload_path:
            raise RuntimeError("IndexTTS upload did not return a reference path")
        uploaded = {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(path)}
        with _INDEXTTS_CACHE_LOCK:
            _INDEXTTS_REFERENCE_CACHE[cache_key] = dict(uploaded)
        return uploaded
    remote_path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH", "").strip()
    if remote_path:
        return {"path": remote_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(remote_path) or "reference.wav"}
    cache_key = ("default-abby-reference", "v1")
    with _INDEXTTS_CACHE_LOCK:
        cached = _INDEXTTS_REFERENCE_CACHE.get(cache_key)
        if cached:
            return dict(cached)
    parsed = _indextts_space_client().upload_file("abby-reference.wav", _default_indextts_reference_wav(), "audio/wav")
    upload_path = _first_upload_path(parsed)
    if not upload_path:
        raise RuntimeError("IndexTTS upload did not return a reference path")
    uploaded = {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": "abby-reference.wav"}
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_REFERENCE_CACHE[cache_key] = dict(uploaded)
    return uploaded


def _default_indextts_reference_wav() -> bytes:
    sample_rate = 24_000
    duration_seconds = 1.5
    frames = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            envelope = min(1.0, index / 2_400, (frames - index) / 2_400)
            value = int(10_000 * envelope * math.sin(2.0 * math.pi * 220.0 * index / sample_rate))
            wav.writeframesraw(struct.pack("<h", value))
    return buffer.getvalue()


def _gradio_upload_file(data: bytes, file_name: str, mime_type: str) -> dict[str, Any]:
    boundary = f"----211AiIndexTts{uuid.uuid4().hex}"
    safe_name = os.path.basename(file_name or "reference.wav")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="files"; filename="{safe_name}"\r\n'.encode(),
            f"Content-Type: {mime_type or 'application/octet-stream'}\r\n\r\n".encode(),
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    headers = _indextts_headers()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request = urllib_request.Request(
        f"{_indextts_space_base_url()}/gradio_api/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    upload_path = _first_upload_path(parsed)
    if not upload_path:
        raise ValueError("IndexTTS upload did not return a Gradio file path")
    return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": safe_name}


def _first_upload_path(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            found = _first_upload_path(item)
            if found:
                return found
    if isinstance(value, Mapping):
        for key in ("path", "name"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            found = _first_upload_path(item)
            if found:
                return found
    return ""


def _indextts_request_data(
    *,
    text: str,
    voice_description: str | None,
    reference_audio: Mapping[str, Any] | None,
) -> list[Any]:
    raw_template = os.getenv("WALLET_INDEXTTS_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{text}", text)
            .replace("{voice_description}", voice_description or "")
            .replace("{reference_audio}", json.dumps(reference_audio) if reference_audio else "null")
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise ValueError("WALLET_INDEXTTS_DATA_TEMPLATE must render to a JSON array")
        return parsed
    # IndexTeam/IndexTTS-2-Demo /gen_single Gradio input order.
    return [
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
        voice_description or "",
        False,
        120,
        True,
        0.8,
        30,
        0.8,
        0.0,
        3,
        10.0,
        1500,
    ]


def _indextts_batch_request_data(
    *,
    texts: Sequence[str],
    voice_description: str | None,
    reference_audio: Mapping[str, Any] | None,
) -> list[Any]:
    text_list = [str(text) for text in texts]
    raw_template = os.getenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{texts}", json.dumps(text_list))
            .replace("{text}", json.dumps(json.dumps(text_list)))
            .replace("{voice_description}", json.dumps(voice_description or ""))
            .replace("{reference_audio}", json.dumps(reference_audio) if reference_audio else "null")
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise ValueError("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE must render to a JSON array")
        return parsed
    # Publicus/IndexTTS-2-Demo /gen_batch uses a Gradio Textbox, but the
    # backend batch parser expects a JSON-encoded list string in that textbox.
    return [
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
        voice_description or "",
        False,
        120,
        len(text_list) if len(text_list) > 1 else 0,
        True,
        0.8,
        30,
        0.8,
        0.0,
        3,
        10.0,
        1500,
    ]


def _indextts_wait_for_result(session_hash: str) -> dict[str, Any]:
    try:
        return _indextts_space_client().wait_for_queue_result(
            session_hash,
            timeout_seconds=_indextts_timeout_seconds(),
            poll_interval_seconds=0.5,
        )
    except Exception as exc:
        detail = _normalize_indextts_queue_failure(exc)
        raise ValueError(f"IndexTTS Gradio queue failed: {detail}") from exc


def _normalize_indextts_queue_failure(error: Exception) -> str:
    detail = str(error or "").strip() or type(error).__name__
    normalized = detail.replace('"', "'").lower()
    if "space queue failed" in normalized and "{'error': none}" in normalized:
        return (
            "Space queue failed without diagnostic details (error=null). "
            "The Hugging Face Space may be overloaded or dropped the job; retry shortly."
        )
    return detail


def _find_gradio_audio_reference(value: Any) -> Any:
    if isinstance(value, Mapping):
        if str(value.get("mime_type") or value.get("mimeType") or "").startswith("audio/"):
            return value
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "")
            if pathish and (pathish.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in pathish or "/gradio_api/file=" in pathish):
                return value
        for item in value.values():
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, str) and (value.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in value or "/gradio_api/file=" in value):
        return value
    return None


def _find_gradio_audio_references(value: Any) -> list[Any]:
    found: list[Any] = []
    seen: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            direct = _find_gradio_audio_reference(item)
            if direct is item:
                key = json.dumps(item, sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    found.append(item)
                return
            for child in item.values():
                visit(child)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if isinstance(item, str):
            direct = _find_gradio_audio_reference(item)
            if direct:
                key = str(direct)
                if key not in seen:
                    seen.add(key)
                    found.append(direct)

    visit(value)
    return found


def _gradio_update_value(value: Any) -> Any:
    if isinstance(value, Mapping) and value.get("__type__") == "update":
        return value.get("value")
    return value


def _gradio_output_values(result: Mapping[str, Any]) -> list[Any]:
    data = result.get("data")
    if isinstance(data, list):
        return [_gradio_update_value(item) for item in data]
    return []


def _gradio_file_key(reference: Any) -> str:
    if isinstance(reference, Mapping):
        return str(reference.get("url") or reference.get("path") or reference.get("name") or json.dumps(reference, sort_keys=True, default=str))
    return str(reference)


def _dedupe_gradio_references(references: Sequence[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for reference in references:
        key = _gradio_file_key(reference)
        if key and key not in seen:
            seen.add(key)
            deduped.append(reference)
    return deduped


def _indextts_batch_audio_references(result: Mapping[str, Any]) -> list[Any]:
    outputs = _gradio_output_values(result)
    if len(outputs) >= 2:
        generated_files = _find_gradio_audio_references(outputs[1])
        if generated_files:
            return _dedupe_gradio_references(generated_files)
    if len(outputs) >= 3:
        zip_ref = _find_gradio_file_reference(outputs[2], suffixes=(".zip",))
        if zip_ref:
            try:
                archive, _mime_type = _fetch_gradio_file(zip_ref)
                extracted = _extract_audio_files_from_zip(archive)
                if extracted:
                    return extracted
            except Exception:
                pass
    return _dedupe_gradio_references(_find_gradio_audio_references(result))


def _find_gradio_file_reference(value: Any, *, suffixes: Sequence[str]) -> Any:
    suffix_tuple = tuple(suffix.lower() for suffix in suffixes)
    if isinstance(value, Mapping):
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "").lower()
            if pathish.endswith(suffix_tuple) or any("/file=" in pathish and suffix in pathish for suffix in suffix_tuple):
                return value
        for item in value.values():
            found = _find_gradio_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_gradio_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, str) and value.lower().endswith(suffix_tuple):
        return value
    return None


def _extract_audio_files_from_zip(data: bytes) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith("/") or not name.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
                continue
            extracted.append({"name": name, "_inline_bytes": archive.read(name)})
    return extracted


def _fetch_gradio_file(reference: Any) -> tuple[bytes, str]:
    if isinstance(reference, Mapping) and isinstance(reference.get("_inline_bytes"), (bytes, bytearray)):
        name = str(reference.get("name") or reference.get("path") or "")
        return bytes(reference["_inline_bytes"]), mimetypes.guess_type(name)[0] or "audio/wav"
    data, detected_type = _indextts_space_client().fetch_file(reference)
    path = str(reference.get("path") or reference.get("name") or "") if isinstance(reference, Mapping) else str(reference or "")
    mime_type = str(reference.get("mime_type") or reference.get("mimeType") or "") if isinstance(reference, Mapping) else ""
    return data, mime_type or detected_type or mimetypes.guess_type(path)[0] or "audio/wav"


def _hf_whisper_model_name(model_name: str | None = None) -> str:
    return (model_name or os.getenv("WALLET_HF_WHISPER_MODEL_NAME") or "openai/whisper-large-v3-turbo").strip()


def _run_hf_whisper_stt(
    audio: bytes,
    *,
    audio_name: str | None = None,
    audio_type: str | None = None,
    language: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    if not audio:
        raise ValueError("audio is required")
    token = (
        resolve_secret(
            "WALLET_HF_WHISPER_TOKEN",
            "IPFS_DATASETS_PY_HF_API_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACEHUB_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
        )
        or ""
    ).strip()
    if not token:
        raise ValueError("Hugging Face token is required for Whisper STT")
    selected_model = _hf_whisper_model_name(model_name)
    base_url = (
        os.getenv("WALLET_HF_WHISPER_BASE_URL", "https://router.huggingface.co/hf-inference/models")
        .strip()
        .rstrip("/")
    )
    content_type = (audio_type or mimetypes.guess_type(audio_name or "")[0] or "audio/wav").strip()
    if content_type in {"application/octet-stream", "binary/octet-stream"}:
        content_type = mimetypes.guess_type(audio_name or "")[0] or "audio/wav"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
    }
    bill_to = (
        os.getenv("WALLET_HF_WHISPER_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    if language:
        headers["X-Wallet-STT-Language"] = language
    url = f"{base_url}/{urllib_parse.quote(selected_model, safe='/')}"
    request = urllib_request.Request(url, data=audio, headers=headers, method="POST")
    with urllib_request.urlopen(request, timeout=_hf_whisper_timeout_seconds()) as response:
        raw = response.read()
    result = json.loads(raw.decode("utf-8"))
    text = _extract_hf_whisper_text(result)
    return {
        "model": selected_model,
        "modelName": selected_model,
        "provider": "huggingface-whisper",
        "text": text,
    }


def _extract_hf_whisper_text(payload: Any) -> str:
    if isinstance(payload, Mapping):
        for key in ("text", "transcription", "transcript", "generated_text", "output_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("items", "results", "segments", "chunks", "output", "data"):
            nested = payload.get(key)
            extracted = _extract_hf_whisper_text(nested)
            if extracted:
                return extracted
        return ""
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        pieces: list[str] = []
        for item in payload:
            extracted = _extract_hf_whisper_text(item)
            if extracted:
                pieces.append(extracted)
        if pieces:
            return " ".join(pieces).strip()
        return ""
    if isinstance(payload, str):
        return payload.strip()
    return ""


def _hf_whisper_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_HF_WHISPER_TIMEOUT_SECONDS", "45")))
    except Exception:
        return 45.0


def _silent_wav_bytes(duration_ms: int = 240, sample_rate: int = 16_000) -> bytes:
    sample_count = max(1, int(sample_rate * duration_ms / 1000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * sample_count)
    return buffer.getvalue()


