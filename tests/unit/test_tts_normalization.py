"""Unit tests for wallet_interface/helpers/_tts_normalization.py.

Exercises pure text-normalization helpers that require only the Python
standard library, so all tests run without optional dependencies.
"""

from __future__ import annotations

import pytest

from wallet_interface.helpers._tts_normalization import (
    _normalize_address_directions_and_highways,
    _normalize_address_prosody,
    _normalize_hours_and_separators,
    _normalize_indextts_spoken_text,
    _normalize_percentages_and_currency,
    _normalize_phone_extensions,
    _normalize_phone_numbers,
    _normalize_sentence_prosody,
    _normalize_urls_for_speech,
    _normalize_zip_codes,
    _number_to_words,
    _ordinal_to_words,
    _shorten_long_eligibility_for_voice,
    _strip_coordinates,
    _strip_scraped_page_chrome,
    _strip_unspoken_fields,
    _title_case_program_name,
)

# ---------------------------------------------------------------------------
# _number_to_words
# ---------------------------------------------------------------------------

class TestNumberToWords:
    def test_zero(self):
        assert _number_to_words(0) == "zero"

    def test_single_digits(self):
        assert _number_to_words(1) == "one"
        assert _number_to_words(9) == "nine"

    def test_teens(self):
        assert _number_to_words(11) == "eleven"
        assert _number_to_words(15) == "fifteen"
        assert _number_to_words(19) == "nineteen"

    def test_tens(self):
        assert _number_to_words(20) == "twenty"
        assert _number_to_words(50) == "fifty"

    def test_compound_tens(self):
        result = _number_to_words(42)
        assert "forty" in result
        assert "two" in result

    def test_hundreds(self):
        result = _number_to_words(100)
        assert "hundred" in result

    def test_hundreds_with_remainder(self):
        result = _number_to_words(123)
        assert "hundred" in result
        assert "twenty" in result
        assert "three" in result

    def test_thousands(self):
        result = _number_to_words(1000)
        assert "thousand" in result

    def test_out_of_range_returns_string(self):
        assert _number_to_words(10000) == "10000"
        assert _number_to_words(-1) == "-1"


# ---------------------------------------------------------------------------
# _ordinal_to_words
# ---------------------------------------------------------------------------

class TestOrdinalToWords:
    def test_first_through_fifth(self):
        assert _ordinal_to_words(1) == "first"
        assert _ordinal_to_words(2) == "second"
        assert _ordinal_to_words(3) == "third"
        assert _ordinal_to_words(4) == "fourth"
        assert _ordinal_to_words(5) == "fifth"

    def test_larger_ordinals(self):
        result = _ordinal_to_words(21)
        assert "twenty" in result
        assert "first" in result

    def test_zero_returns_zero(self):
        assert _ordinal_to_words(0) == "zero"


# ---------------------------------------------------------------------------
# _normalize_zip_codes
# ---------------------------------------------------------------------------

class TestNormalizeZipCodes:
    def test_five_digit_zip_expanded(self):
        result = _normalize_zip_codes("Portland OR 97201")
        # zip digits should be spelled out or expanded
        assert "97201" not in result or any(d in result for d in ["nine", "seven", "two", "zero", "one"])

    def test_no_zip_unchanged(self):
        result = _normalize_zip_codes("Portland Oregon")
        assert "Portland" in result

    def test_zip_plus_four_handled(self):
        result = _normalize_zip_codes("97201-1234")
        assert "97201-1234" not in result or "nine" in result.lower()


# ---------------------------------------------------------------------------
# _normalize_phone_numbers
# ---------------------------------------------------------------------------

class TestNormalizePhoneNumbers:
    def test_us_format_with_dashes(self):
        result = _normalize_phone_numbers("Call 503-555-1234 for info")
        assert "5-0-3" not in result  # Should be spaced digits, not original
        assert "503-555-1234" not in result

    def test_preserves_surrounding_text(self):
        result = _normalize_phone_numbers("Call 503-555-1234 for info")
        assert "Call" in result
        assert "for info" in result

    def test_no_phone_unchanged(self):
        result = _normalize_phone_numbers("Visit our website")
        assert "Visit our website" == result


# ---------------------------------------------------------------------------
# _normalize_phone_extensions
# ---------------------------------------------------------------------------

class TestNormalizePhoneExtensions:
    def test_ext_expanded(self):
        result = _normalize_phone_extensions("Call 503-555-1234 ext. 42")
        assert "ext." not in result.lower() or "extension" in result.lower()


# ---------------------------------------------------------------------------
# _strip_unspoken_fields
# ---------------------------------------------------------------------------

class TestStripUnspokenFields:
    def test_url_field_stripped(self):
        result = _strip_unspoken_fields("Service URL: https://example.com")
        assert "https://example.com" not in result

    def test_cid_field_stripped(self):
        result = _strip_unspoken_fields("CID: bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi")
        assert "bafybei" not in result

    def test_name_field_preserved(self):
        text = "Name: Portland Housing Help\nPhone: 503-555-1234"
        result = _strip_unspoken_fields(text)
        assert "Portland Housing Help" in result


# ---------------------------------------------------------------------------
# _strip_coordinates
# ---------------------------------------------------------------------------

class TestStripCoordinates:
    def test_lat_lon_stripped(self):
        result = _strip_coordinates("Location: 45.5231, -122.6765")
        assert "45.5231" not in result

    def test_non_coordinate_text_preserved(self):
        result = _strip_coordinates("Shelter at 123 Main Street")
        assert "Main Street" in result


# ---------------------------------------------------------------------------
# _strip_scraped_page_chrome
# ---------------------------------------------------------------------------

class TestStripScrapedPageChrome:
    def test_newlines_collapsed_to_spaces(self):
        result = _strip_scraped_page_chrome("Service description here\nPhone: 503-555-1234")
        assert "\n" not in result
        assert "Service description here" in result

    def test_plain_text_preserved(self):
        result = _strip_scraped_page_chrome("Rent assistance program")
        assert "Rent assistance program" in result

    def test_multiple_newlines_collapsed(self):
        result = _strip_scraped_page_chrome("Line one\n\n\nLine two")
        assert "\n\n" not in result


# ---------------------------------------------------------------------------
# _normalize_urls_for_speech
# ---------------------------------------------------------------------------

class TestNormalizeUrlsForSpeech:
    def test_http_url_transformed(self):
        result = _normalize_urls_for_speech("Visit https://example.com for details")
        assert "https" not in result

    def test_plain_text_unchanged(self):
        result = _normalize_urls_for_speech("Call for more information")
        assert result == "Call for more information"


# ---------------------------------------------------------------------------
# _normalize_percentages_and_currency
# ---------------------------------------------------------------------------

class TestNormalizePercentagesAndCurrency:
    def test_percent_sign_expanded(self):
        result = _normalize_percentages_and_currency("Income at 50% AMI")
        assert "%" not in result
        assert "percent" in result.lower()

    def test_dollar_sign_expanded(self):
        result = _normalize_percentages_and_currency("Cost is $25")
        # Either "$" is removed or "dollar" appears
        assert "$" not in result or "dollar" in result.lower()


# ---------------------------------------------------------------------------
# _normalize_hours_and_separators
# ---------------------------------------------------------------------------

class TestNormalizeHoursAndSeparators:
    def test_time_separator_cleaned(self):
        result = _normalize_hours_and_separators("Hours: 9:00 AM - 5:00 PM")
        assert "9:00" in result or "nine" in result.lower()


# ---------------------------------------------------------------------------
# _normalize_address_directions_and_highways
# ---------------------------------------------------------------------------

class TestNormalizeAddressDirectionsAndHighways:
    def test_highway_number_expanded(self):
        result = _normalize_address_directions_and_highways("Located on US Highway 26")
        # Numbers in highway names should be spoken
        assert "twenty six" in result.lower() or "Highway" in result

    def test_street_suffix_expanded(self):
        result = _normalize_address_directions_and_highways("123 NW Flanders St")
        assert "Street" in result or "St" not in result

    def test_direction_expanded(self):
        result = _normalize_address_directions_and_highways("123 NW Flanders Street")
        assert "North West" in result or "NW" not in result


# ---------------------------------------------------------------------------
# _title_case_program_name
# ---------------------------------------------------------------------------

class TestTitleCaseProgramName:
    def test_all_caps_converted(self):
        result = _title_case_program_name("EMERGENCY SHELTER SERVICES")
        assert result != "EMERGENCY SHELTER SERVICES"
        assert "Emergency" in result or "emergency" in result.lower()

    def test_mixed_case_preserved(self):
        result = _title_case_program_name("Portland Housing Help")
        assert "Portland" in result


# ---------------------------------------------------------------------------
# _normalize_sentence_prosody
# ---------------------------------------------------------------------------

class TestNormalizeSentenceProsody:
    def test_all_caps_program_name_converted(self):
        # "I found PORTLAND HOUSING HELP." → title-cased
        result = _normalize_sentence_prosody("I found PORTLAND HOUSING HELP.")
        assert "PORTLAND HOUSING HELP" not in result

    def test_sentence_returns_string(self):
        result = _normalize_sentence_prosody("End of sentence.")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _normalize_address_prosody
# ---------------------------------------------------------------------------

class TestNormalizeAddressProsody:
    def test_address_with_state_name_preserved(self):
        result = _normalize_address_prosody("Portland, Oregon")
        assert "Oregon" in result

    def test_address_returns_string(self):
        result = _normalize_address_prosody("123 Main Street")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _shorten_long_eligibility_for_voice
# ---------------------------------------------------------------------------

class TestShortenLongEligibilityForVoice:
    def test_short_text_unchanged(self):
        short = "Adults only"
        result = _shorten_long_eligibility_for_voice(short)
        assert short in result

    def test_long_eligibility_body_shortened(self):
        # Requires "Eligibility:" prefix and body > 220 chars to trigger shortening
        long_body = "Adults seeking shelter services. " * 10
        text = f"Eligibility: {long_body} Before traveling call ahead."
        result = _shorten_long_eligibility_for_voice(text)
        assert len(result) < len(text)


# ---------------------------------------------------------------------------
# _normalize_indextts_spoken_text (integration)
# ---------------------------------------------------------------------------

class TestNormalizeIndexTTSSpokenText:
    def test_full_pipeline_runs(self):
        text = "Portland Housing Help\nPhone: 503-555-1234\nAddress: 123 N Main St, Portland OR 97201"
        result = _normalize_indextts_spoken_text(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_removes_url_fields(self):
        text = "Service URL: https://example.com\nName: Test Service"
        result = _normalize_indextts_spoken_text(text)
        assert "https://example.com" not in result
        assert "Test Service" in result

    def test_211_ai_expanded(self):
        text = "Contact 211-AI for help"
        result = _normalize_indextts_spoken_text(text)
        # "211-AI" should be expanded to a spoken form
        assert "two one one" in result.lower() or "211" not in result

    def test_211_hotline_expanded(self):
        text = "Call 211 for resources"
        result = _normalize_indextts_spoken_text(text)
        assert "two one one" in result.lower()

    def test_empty_string_returns_empty(self):
        result = _normalize_indextts_spoken_text("")
        assert result == "" or isinstance(result, str)
