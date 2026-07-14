# ruff: noqa: E501
"""Pure text-normalization helpers for speech/TTS output.

All functions in this module use only the Python standard library, so they
can be imported without optional dependencies such as ``ipfs_datasets_py``
or ``ipfs_accelerate_py``.
"""

from __future__ import annotations

import math
import re
from urllib import parse as urllib_parse

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

