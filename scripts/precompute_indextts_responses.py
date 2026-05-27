#!/usr/bin/env python3
"""Precompute Abby IndexTTS audio for conversation DAG voice responses."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
import re
import subprocess
import time
import uuid
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib import parse as urllib_parse
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(IPFS_DATASETS_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(IPFS_DATASETS_ROOT))
DEFAULT_DAG = REPO_ROOT / "docs/211_conversation_dag.json"
DEFAULT_RESULTS = REPO_ROOT / "docs/211_chatbot_simulation_results.json"
DEFAULT_REFERENCE = REPO_ROOT / "tmp_assets/abby-reference.wav"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "wallet_interface/ui/public/assets/audio/precomputed/211-dag-indextts"
DEFAULT_MANIFEST = REPO_ROOT / "docs/211_indextts_precompute_manifest.json"
DEFAULT_PUBLIC_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"


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


def audio_url_for(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    return f"/assets/audio/precomputed/211-dag-indextts/{path.name}"


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path, *, bitrate: str = "64k", force: bool = False) -> None:
    if mp3_path.exists() and not force and mp3_path.stat().st_mtime >= wav_path.stat().st_mtime:
        return
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
        str(mp3_path),
    ]
    subprocess.run(command, check=True)


def maybe_delete_wav(wav_path: Path, mp3_path: Path, *, delete_wav: bool) -> bool:
    if not delete_wav:
        return False
    if not mp3_path.exists() or mp3_path.stat().st_size <= 0:
        return False
    wav_path.unlink(missing_ok=True)
    return True


def load_secret_env() -> None:
    """Best-effort load HF token/billing env from ~/.ipfs_datasets/secrets.json."""
    try:
        from ipfs_datasets_py.utils.secrets import resolve_secret  # type: ignore
    except Exception:
        resolve_secret = None  # type: ignore[assignment]
    if resolve_secret:
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
    return os.getenv("WALLET_INDEXTTS_SPACE_URL", "https://indexteam-indextts-2-demo.hf.space").strip().rstrip("/")


def indextts_timeout() -> float:
    try:
        return max(30.0, float(os.getenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "900")))
    except ValueError:
        return 900.0


def indextts_headers(*, accept: str = "application/json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "211-ai-indextts-precompute/1.0",
    }
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("IPFS_DATASETS_PY_HF_API_TOKEN")
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


def http_json(method: str, url: str, payload: Any | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = indextts_headers()
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=indextts_timeout()) as response:
        return json.loads(response.read().decode("utf-8"))


def upload_reference(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    boundary = f"----211AiIndexTtsPrecompute{uuid.uuid4().hex}"
    safe_name = path.name or "abby-reference.wav"
    mime_type = mimetypes.guess_type(str(path))[0] or "audio/wav"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="files"; filename="{safe_name}"\r\n'.encode("utf-8"),
            f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
            data,
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    headers = indextts_headers()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request = urllib_request.Request(
        f"{indextts_base_url()}/gradio_api/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=indextts_timeout()) as response:
        parsed = json.loads(response.read().decode("utf-8"))
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
    return dict(http_json("GET", f"{indextts_base_url()}/config"))


def indextts_fn_index(config: Mapping[str, Any]) -> int:
    api_name = os.getenv("WALLET_INDEXTTS_API_NAME", "/gen_single")
    api_candidates = {api_name, api_name.lstrip("/"), f"/{api_name.lstrip('/')}"}
    dependencies = config.get("dependencies")
    if not isinstance(dependencies, list):
        raise RuntimeError("IndexTTS config did not include dependencies")
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            continue
        if str(dependency.get("api_name") or "") in api_candidates:
            value = dependency.get("id")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            continue
        name = str(dependency.get("api_name") or dependency.get("id") or "").lower()
        if any(marker in name for marker in ("tts", "synth", "generate", "infer", "predict")):
            value = dependency.get("id")
            if isinstance(value, int):
                return value
    raise RuntimeError(f"IndexTTS api_name {api_name!r} was not found")


def indextts_batch_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", "/gen_batch").strip()


def indextts_batch_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_BATCH_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    api_name = indextts_batch_api_name()
    api_candidates = {api_name, api_name.lstrip("/"), f"/{api_name.lstrip('/')}"}
    dependencies = config.get("dependencies")
    if not isinstance(dependencies, list):
        raise RuntimeError("IndexTTS config did not include dependencies")
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            continue
        if str(dependency.get("api_name") or "") in api_candidates:
            value = dependency.get("id")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
    raise RuntimeError(f"IndexTTS batch api_name {api_name!r} was not found")


def request_data(text: str, reference_audio: Mapping[str, Any], voice_description: str) -> list[Any]:
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
        voice_description,
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


def batch_request_data(texts: Sequence[str], reference_audio: Mapping[str, Any], voice_description: str) -> list[Any]:
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
        voice_description,
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


def wait_for_result(session_hash: str) -> dict[str, Any]:
    deadline = time.time() + indextts_timeout()
    url = f"{indextts_base_url()}/gradio_api/queue/data?session_hash={urllib_parse.quote(session_hash)}"
    while time.time() < deadline:
        request = urllib_request.Request(url, headers=indextts_headers())
        with urllib_request.urlopen(request, timeout=min(30.0, indextts_timeout())) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload_text = line.removeprefix("data:").strip()
                if not payload_text:
                    continue
                event = json.loads(payload_text)
                if not isinstance(event, Mapping):
                    continue
                message = str(event.get("msg") or "")
                if message == "process_completed":
                    if event.get("success") is False:
                        raise RuntimeError(f"IndexTTS queue failed: {event.get('output') or event}")
                    output = event.get("output")
                    return dict(output) if isinstance(output, Mapping) else dict(event)
                if message in {"process_failed", "queue_full"}:
                    raise RuntimeError(f"IndexTTS queue failed: {event}")
        time.sleep(0.5)
    raise TimeoutError("IndexTTS queue timed out")


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
        url = str(ref.get("url") or "")
        path = str(ref.get("path") or ref.get("name") or "")
        mime_type = str(ref.get("mime_type") or ref.get("mimeType") or "")
    else:
        url = str(ref or "")
        path = url
        mime_type = ""
    if url.startswith("http://") or url.startswith("https://"):
        file_url = url
    else:
        encoded_path = urllib_parse.quote(path, safe="/:")
        file_url = f"{indextts_base_url()}/gradio_api/file={encoded_path}"
    request = urllib_request.Request(file_url, headers=indextts_headers(accept="audio/*, application/octet-stream"))
    with urllib_request.urlopen(request, timeout=indextts_timeout()) as response:
        return response.read(), mime_type or response.headers.get_content_type() or "audio/wav"


def synthesize(text: str, config: Mapping[str, Any], fn_index: int, reference_audio: Mapping[str, Any], voice_description: str) -> dict[str, Any]:
    start = time.perf_counter()
    session_hash = uuid.uuid4().hex
    http_json(
        "POST",
        f"{indextts_base_url()}/gradio_api/queue/join",
        {"data": request_data(text, reference_audio, voice_description), "fn_index": fn_index, "session_hash": session_hash},
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


def synthesize_batch(
    texts: Sequence[str],
    config: Mapping[str, Any],
    single_fn_index: int,
    reference_audio: Mapping[str, Any],
    voice_description: str,
) -> list[dict[str, Any]]:
    text_list = [str(text) for text in texts]
    if not text_list:
        return []
    batch_enabled = os.getenv("WALLET_INDEXTTS_BATCH_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
    require_batch = os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "").strip().lower() in {"1", "true", "yes"}
    if batch_enabled:
        start = time.perf_counter()
        try:
            session_hash = uuid.uuid4().hex
            http_json(
                "POST",
                f"{indextts_base_url()}/gradio_api/queue/join",
                {
                    "data": batch_request_data(text_list, reference_audio, voice_description),
                    "fn_index": indextts_batch_fn_index(config),
                    "session_hash": session_hash,
                },
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
        except Exception:
            if require_batch:
                raise
    return [
        {
            **synthesize(text, config, single_fn_index, reference_audio, voice_description),
            "batchMode": "sequential-fallback" if batch_enabled else "sequential",
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


def load_audio_responses(dag_path: Path, results_path: Path, *, include_assistant: bool = True, include_voice: bool = True) -> list[dict[str, Any]]:
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
    responses: list[dict[str, Any]] = []
    for item in by_text.values():
        responses.append(
            {
                **item,
                "originalTexts": list(item["originalTexts"]),
                "routes": sorted(item["routes"]),
                "serviceTags": sorted(item["serviceTags"]),
                "locationTags": sorted(item["locationTags"]),
                "sourceTypes": sorted(item["sourceTypes"]),
            }
        )
    responses.sort(key=lambda item: item["id"])
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dag", type=Path, default=DEFAULT_DAG)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--public-manifest", type=Path, default=DEFAULT_PUBLIC_MANIFEST)
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
        default=int(os.getenv("WALLET_INDEXTTS_REMOTE_BATCH_SIZE", "1") or "1"),
        help="Send this many uncached responses to the IndexTTS batch endpoint at once when available.",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started_at = time.time()
    include_assistant = not args.voice_responses_only
    include_voice = not args.assistant_responses_only
    responses = load_audio_responses(
        args.dag,
        args.results,
        include_assistant=include_assistant,
        include_voice=include_voice,
    )
    if args.offset:
        responses = responses[max(0, args.offset) :]
    if args.limit is not None:
        responses = responses[: max(0, args.limit)]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []
    if args.dry_run:
        for item in responses:
            manifest_entries.append({**item, "status": "planned", "audioPath": "", "mp3Path": ""})
    else:
        load_secret_env()
        if not args.reference_audio.exists():
            raise FileNotFoundError(args.reference_audio)
        print(f"IndexTTS auth: {describe_indextts_auth()}")
        config = indextts_config()
        fn_index = indextts_fn_index(config)
        reference = upload_reference(args.reference_audio)
        remote_batch_size = max(1, int(args.remote_batch_size or 1))
        pending: list[tuple[int, dict[str, Any], Path, Path]] = []

        def flush_pending() -> None:
            if not pending:
                return
            batch = list(pending)
            pending.clear()
            texts = [item["text"] for _, item, _, _ in batch]
            try:
                print(f"synthesizing remote batch of {len(batch)} response(s)")
                results = synthesize_batch(texts, config, fn_index, reference, args.voice_description)
                if len(results) != len(batch):
                    raise RuntimeError(f"IndexTTS batch returned {len(results)} result(s) for {len(batch)} response(s)")
                for (index, item, audio_path, mp3_path), result in zip(batch, results):
                    audio_path.write_bytes(result["audio"])
                    if args.write_mp3:
                        convert_wav_to_mp3(audio_path, mp3_path, bitrate=args.mp3_bitrate, force=True)
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
                    manifest_entries.append(entry)
                    print(f"[{index}/{len(responses)}] generated {mp3_path.name if mp3_path.exists() else audio_path.name}")
                    write_progress(args.progress_json, manifest_entries, len(responses), started_at)
            except Exception as exc:
                for index, item, _audio_path, _mp3_path in batch:
                    print(f"[{index}/{len(responses)}] failed {item['id']}: {exc}")
                    manifest_entries.append(
                        {
                            **item,
                            "status": "failed",
                            "audioPath": "",
                            "mp3Path": "",
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                if args.stop_on_error:
                    raise

        for index, item in enumerate(responses, start=1):
            if args.max_runtime_seconds is not None and time.time() - started_at >= args.max_runtime_seconds:
                print(f"[{index}/{len(responses)}] stopping before new work: max runtime reached")
                break
            audio_path = args.output_dir / f"{item['id']}.wav"
            mp3_path = args.output_dir / f"{item['id']}.mp3"
            if not audio_path.exists() and mp3_path.exists() and not args.force:
                manifest_entries.append(
                    {
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
                )
                print(f"[{index}/{len(responses)}] cached {mp3_path.name}")
                write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                continue
            if audio_path.exists() and not args.force:
                if args.write_mp3:
                    convert_wav_to_mp3(audio_path, mp3_path, bitrate=args.mp3_bitrate, force=False)
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
                manifest_entries.append(entry)
                print(f"[{index}/{len(responses)}] cached {audio_path.name}")
                write_progress(args.progress_json, manifest_entries, len(responses), started_at)
                continue
            print(f"[{index}/{len(responses)}] queued {item['id']}: {item['text']}")
            pending.append((index, item, audio_path, mp3_path))
            if len(pending) >= remote_batch_size:
                try:
                    flush_pending()
                except Exception:
                    break
        if pending:
            try:
                flush_pending()
            except Exception:
                pass

    payload = {
        "schemaVersion": 1,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": "IndexTeam/IndexTTS-2-Demo",
        "spaceUrl": indextts_base_url(),
        "referenceAudio": str(args.reference_audio),
        "voiceDescription": args.voice_description,
        "responseCount": len(manifest_entries),
        "sources": {
            "dag": str(args.dag),
            "results": str(args.results),
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
            "batchApiName": indextts_batch_api_name(),
            "enabled": os.getenv("WALLET_INDEXTTS_BATCH_ENABLED", "1").strip().lower() not in {"0", "false", "no"},
            "requiresBatch": os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "").strip().lower() in {"1", "true", "yes"},
        },
        "responses": manifest_entries,
    }
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


if __name__ == "__main__":
    main()
