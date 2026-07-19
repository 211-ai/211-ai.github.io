"""Extended unit tests for _tts_normalization.py functions not yet covered."""

from __future__ import annotations

from wallet_interface.helpers._tts_normalization import (
    _digits_to_words,
    _domain_to_spoken_site,
    _normalize_address_directions_and_highways,
    _normalize_address_prosody,
    _normalize_hours_and_separators,
    _normalize_indextts_spoken_text,
    _normalize_percentages_and_currency,
    _normalize_phone_list_prosody,
    _normalize_record_list_sentence,
    _normalize_sentence_prosody,
    _normalize_suffix_token,
    _normalize_urls_for_speech,
    _prefer_primary_voice_contact,
    _shorten_long_eligibility_for_voice,
    _strip_scraped_page_chrome,
    _title_case_program_name,
)


class TestDigitsToWords:
    def test_single_digit(self):
        assert _digits_to_words("5") == "five"

    def test_two_digits(self):
        assert _digits_to_words("42") == "four two"

    def test_leading_zeros(self):
        assert _digits_to_words("07") == "zero seven"

    def test_empty_string(self):
        # empty input returns empty
        assert _digits_to_words("") == ""


class TestNormalizeSuffixToken:
    def test_blvd_expanded(self):
        assert _normalize_suffix_token("Blvd") == "Boulevard"

    def test_ave_expanded(self):
        assert _normalize_suffix_token("Ave") == "Avenue"

    def test_st_expanded(self):
        assert _normalize_suffix_token("St") == "Street"

    def test_unknown_token_unchanged(self):
        assert _normalize_suffix_token("Xyz") == "Xyz"

    def test_case_insensitive(self):
        assert _normalize_suffix_token("blvd") == "Boulevard"


class TestNormalizeAddressDirectionsAndHighways:
    def test_ne_direction_expanded(self):
        result = _normalize_address_directions_and_highways("123 NE Oak Ave")
        assert "North East" in result

    def test_sw_direction_expanded(self):
        result = _normalize_address_directions_and_highways("100 SW Broadway")
        assert "South West" in result

    def test_no_direction_unchanged(self):
        text = "123 Main Street"
        assert _normalize_address_directions_and_highways(text) == text

    def test_suffix_expanded(self):
        # Suffixes are expanded when a direction prefix is present
        result = _normalize_address_directions_and_highways("123 NE Oak Ave")
        assert "Avenue" in result

    def test_empty_string(self):
        assert _normalize_address_directions_and_highways("") == ""


class TestDomainToSpokenSite:
    def test_google_spoken(self):
        assert _domain_to_spoken_site("https://www.google.com") == "the google website"

    def test_bare_domain(self):
        result = _domain_to_spoken_site("https://example.org")
        assert "example" in result

    def test_removes_www(self):
        result = _domain_to_spoken_site("https://www.example.com")
        assert "www" not in result

    def test_empty_string(self):
        result = _domain_to_spoken_site("")
        assert isinstance(result, str)


class TestNormalizeUrlsForSpeech:
    def test_url_replaced_with_site_name(self):
        result = _normalize_urls_for_speech("Visit https://example.com for help")
        assert "example" in result
        assert "https" not in result

    def test_no_url_unchanged(self):
        text = "No links here"
        assert _normalize_urls_for_speech(text) == text

    def test_multiple_urls(self):
        result = _normalize_urls_for_speech(
            "See https://a.org and https://b.org"
        )
        assert "https" not in result


class TestNormalizePercentagesAndCurrency:
    def test_percent_expanded(self):
        result = _normalize_percentages_and_currency("50% off")
        assert "fifty percent" in result.lower()
        assert "%" not in result

    def test_dollar_amount_expanded(self):
        result = _normalize_percentages_and_currency("costs $100")
        assert "hundred" in result.lower()
        assert "$" not in result

    def test_no_match_unchanged(self):
        text = "no special values here"
        assert _normalize_percentages_and_currency(text) == text


class TestNormalizeHoursAndSeparators:
    def test_am_pm_separator_replaced(self):
        result = _normalize_hours_and_separators("9am-5pm")
        assert " to " in result

    def test_lowercase_am_kept(self):
        result = _normalize_hours_and_separators("9am-5pm")
        assert "AM" in result or "am" in result.lower()

    def test_colon_time_preserved(self):
        result = _normalize_hours_and_separators("9:00 AM - 5:00 PM")
        assert "9:00" in result

    def test_no_hours_unchanged(self):
        text = "No hours listed"
        assert _normalize_hours_and_separators(text) == text


class TestNormalizeRecordListSentence:
    def test_record_lists_address_rewritten(self):
        result = _normalize_record_list_sentence(
            "The record lists 123 Oak St. Phone: 503-555-1212"
        )
        assert "address is" in result.lower()

    def test_no_record_list_unchanged(self):
        text = "No special phrases here"
        assert _normalize_record_list_sentence(text) == text

    def test_unavailable_suppressed(self):
        result = _normalize_record_list_sentence(
            "The record lists not available."
        )
        assert "not available" not in result


class TestTitleCaseProgramName:
    def test_all_caps_converted(self):
        result = _title_case_program_name("EMERGENCY FOOD ASSISTANCE")
        assert result == "Emergency Food Assistance"

    def test_already_mixed_case_normalized(self):
        result = _title_case_program_name("already Proper Case")
        assert result[0].isupper()

    def test_empty_string(self):
        assert _title_case_program_name("") == ""


class TestStripScrapedPageChrome:
    def test_scraper_chrome_stripped(self):
        # Strips UI navigation phrases injected by scrapers
        result = _strip_scraped_page_chrome(
            "Get Directions Visit Website More Details Useful info here"
        )
        assert "Get Directions" not in result
        assert "Visit Website" not in result
        assert "Useful info here" in result

    def test_no_chrome_unchanged(self):
        text = "Plain text without navigation"
        assert _strip_scraped_page_chrome(text) == text

    def test_empty_string(self):
        assert _strip_scraped_page_chrome("") == ""


class TestNormalizeSentenceProsody:
    def test_sentences_pass_through(self):
        text = "This is a sentence. Another one follows."
        result = _normalize_sentence_prosody(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string(self):
        assert _normalize_sentence_prosody("") == ""


class TestNormalizeAddressProsody:
    def test_address_string_returned(self):
        result = _normalize_address_prosody("123 NE Oak Ave, Portland, OR 97201")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string(self):
        assert _normalize_address_prosody("") == ""


class TestNormalizePhoneListProsody:
    def test_phone_number_pass_through(self):
        result = _normalize_phone_list_prosody("Call 503-555-1212 for help")
        assert isinstance(result, str)
        assert "503" in result or "five" in result.lower()

    def test_no_phones_unchanged(self):
        text = "No phones here"
        assert _normalize_phone_list_prosody(text) == text


class TestPreferPrimaryVoiceContact:
    def test_returns_string(self):
        result = _prefer_primary_voice_contact(
            "Primary: 503-555-1212 Secondary: 503-555-9876"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string(self):
        assert _prefer_primary_voice_contact("") == ""


class TestShortenLongEligibilityForVoice:
    def test_short_text_unchanged(self):
        text = "Must be a resident"
        result = _shorten_long_eligibility_for_voice(text)
        assert result == text

    def test_returns_string(self):
        long_text = " ".join(["word"] * 200)
        result = _shorten_long_eligibility_for_voice(long_text)
        assert isinstance(result, str)


class TestNormalizeIndexttsSpokenText:
    def test_pipeline_runs_without_error(self):
        text = (
            "The record lists 123 NE Oak Ave. "
            "Phone: 503-555-1212. "
            "Open Mon-Fri 9am-5pm. "
            "Eligibility: 50% below poverty."
        )
        result = _normalize_indextts_spoken_text(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_input_returns_string(self):
        result = _normalize_indextts_spoken_text("")
        assert isinstance(result, str)

    def test_percent_expanded_in_pipeline(self):
        result = _normalize_indextts_spoken_text("Requires 80% completion")
        assert "%" not in result

    def test_url_replaced_in_pipeline(self):
        result = _normalize_indextts_spoken_text("See https://example.org")
        assert "https" not in result
