"""Unit tests for wallet_interface/helpers/_records.py pure helpers.

All tests in this module run without any optional dependencies
(no ipfs_datasets_py, no fastapi, no network access required).
"""
from __future__ import annotations

import unittest

from wallet_interface.helpers._records import (
    _build_privacy_search_text,
    _build_privacy_vector_terms,
    _classify_document_profile,
    _default_labels_for_mime_type,
    _derived_artifact_id,
    _derived_output,
    _display_mime_type,
    _fallback_document_profile_output,
    _parse_first_json_object,
    _read_number,
    _read_string,
    _read_string_list,
    _record_metadata_value,
    _redacted_file_name,
    _safe_organizer_signal,
    _safe_short_text,
    _summarize_document_profile,
)


class TestDerivedOutput(unittest.TestCase):
    def test_extracts_mapping_output(self):
        result = {"output": {"key": "value"}}
        self.assertEqual(_derived_output(result), {"key": "value"})

    def test_returns_empty_when_output_missing(self):
        self.assertEqual(_derived_output({}), {})

    def test_returns_empty_when_output_not_mapping(self):
        self.assertEqual(_derived_output({"output": "string"}), {})
        self.assertEqual(_derived_output({"output": 42}), {})

    def test_returns_copy_of_output(self):
        inner = {"a": 1}
        result = _derived_output({"output": inner})
        result["b"] = 2
        self.assertNotIn("b", inner)


class TestDerivedArtifactId(unittest.TestCase):
    def test_reads_artifact_id_from_mapping(self):
        self.assertEqual(_derived_artifact_id({"artifact": {"artifact_id": "abc"}}), "abc")

    def test_falls_back_to_id(self):
        self.assertEqual(_derived_artifact_id({"artifact": {"id": "xyz"}}), "xyz")

    def test_prefers_artifact_id_over_id(self):
        self.assertEqual(_derived_artifact_id({"artifact": {"artifact_id": "primary", "id": "fallback"}}), "primary")

    def test_reads_attribute_artifact_id(self):
        class MockArtifact:
            artifact_id = "attr-id"

        self.assertEqual(_derived_artifact_id({"artifact": MockArtifact()}), "attr-id")

    def test_returns_empty_when_no_artifact(self):
        self.assertEqual(_derived_artifact_id({}), "")

    def test_returns_empty_when_artifact_none(self):
        self.assertEqual(_derived_artifact_id({"artifact": None}), "")


class TestRecordMetadataValue(unittest.TestCase):
    def test_reads_string_value(self):
        record = {"metadata": {"owner": "alice"}}
        self.assertEqual(_record_metadata_value(record, "owner"), "alice")

    def test_returns_empty_when_key_missing(self):
        record = {"metadata": {"owner": "alice"}}
        self.assertEqual(_record_metadata_value(record, "missing_key"), "")

    def test_returns_empty_when_no_metadata(self):
        self.assertEqual(_record_metadata_value({}, "owner"), "")

    def test_returns_empty_when_metadata_not_mapping(self):
        record = {"metadata": "not-a-dict"}
        self.assertEqual(_record_metadata_value(record, "owner"), "")


class TestSafeShortText(unittest.TestCase):
    def test_truncates_to_limit(self):
        text = "a" * 300
        result = _safe_short_text(text, limit=240)
        self.assertEqual(len(result), 240)

    def test_redacts_email(self):
        result = _safe_short_text("contact user@example.com please")
        self.assertIn("[email]", result)
        self.assertNotIn("user@example.com", result)

    def test_redacts_phone(self):
        result = _safe_short_text("call 503-555-1234 now")
        self.assertIn("[phone]", result)
        self.assertNotIn("503-555-1234", result)

    def test_redacts_long_numbers(self):
        result = _safe_short_text("id 12345678 here")
        self.assertIn("[number]", result)

    def test_strips_whitespace(self):
        self.assertEqual(_safe_short_text("  hello  "), "hello")

    def test_handles_none(self):
        self.assertEqual(_safe_short_text(None), "")

    def test_plain_text_unchanged(self):
        result = _safe_short_text("No PII here")
        self.assertEqual(result, "No PII here")


class TestRedactedFileName(unittest.TestCase):
    def test_preserves_extension(self):
        self.assertEqual(_redacted_file_name("document.pdf"), "document.pdf")

    def test_lowercases_extension(self):
        self.assertEqual(_redacted_file_name("FILE.PDF"), "document.pdf")

    def test_replaces_stem(self):
        self.assertEqual(_redacted_file_name("alice_tax_return.pdf"), "document.pdf")

    def test_no_extension(self):
        self.assertEqual(_redacted_file_name("noextension"), "document")

    def test_empty_string(self):
        self.assertEqual(_redacted_file_name(""), "document")


class TestParseFirstJsonObject(unittest.TestCase):
    def test_parses_simple_object(self):
        result = _parse_first_json_object('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_extracts_from_prose(self):
        result = _parse_first_json_object('Here is the data: {"a": 1} done.')
        self.assertEqual(result, {"a": 1})

    def test_returns_none_for_no_json(self):
        self.assertIsNone(_parse_first_json_object("no json here"))

    def test_returns_none_for_array(self):
        self.assertIsNone(_parse_first_json_object("[1, 2, 3]"))

    def test_returns_none_for_invalid_json(self):
        self.assertIsNone(_parse_first_json_object("{bad json"))

    def test_returns_none_for_empty(self):
        self.assertIsNone(_parse_first_json_object(""))


class TestReadStringList(unittest.TestCase):
    def test_reads_list_of_strings(self):
        result = _read_string_list(["a", "b", "c"])
        self.assertEqual(result, ["a", "b", "c"])

    def test_filters_empty_items(self):
        result = _read_string_list(["a", "", "  ", "b"])
        self.assertNotIn("", result)
        self.assertIn("a", result)
        self.assertIn("b", result)

    def test_respects_limit(self):
        result = _read_string_list(["a"] * 20, limit=5)
        self.assertEqual(len(result), 5)

    def test_returns_empty_for_non_list(self):
        self.assertEqual(_read_string_list("not-a-list"), [])
        self.assertEqual(_read_string_list(None), [])


class TestReadNumber(unittest.TestCase):
    def test_reads_integer(self):
        self.assertEqual(_read_number({"count": 5}, "count"), 5)

    def test_reads_float(self):
        self.assertAlmostEqual(_read_number({"score": 0.5}, "score"), 0.5)

    def test_returns_none_for_missing_key(self):
        self.assertIsNone(_read_number({"a": 1}, "missing"))

    def test_returns_none_for_string_value(self):
        self.assertIsNone(_read_number({"count": "5"}, "count"))

    def test_returns_none_for_none_record(self):
        self.assertIsNone(_read_number(None, "count"))


class TestReadString(unittest.TestCase):
    def test_reads_string(self):
        self.assertEqual(_read_string({"name": "alice"}, "name"), "alice")

    def test_strips_whitespace(self):
        self.assertEqual(_read_string({"name": "  bob  "}, "name"), "bob")

    def test_returns_empty_for_missing_key(self):
        self.assertEqual(_read_string({}, "name"), "")

    def test_returns_empty_for_non_string_value(self):
        self.assertEqual(_read_string({"count": 5}, "count"), "")

    def test_returns_empty_for_none_record(self):
        self.assertEqual(_read_string(None, "name"), "")


class TestDefaultLabelsForMimeType(unittest.TestCase):
    def test_pdf(self):
        self.assertIn("pdf", _default_labels_for_mime_type("application/pdf"))

    def test_image(self):
        labels = _default_labels_for_mime_type("image/png")
        self.assertIn("image", labels)

    def test_text(self):
        labels = _default_labels_for_mime_type("text/plain")
        self.assertIn("text", labels)

    def test_json(self):
        labels = _default_labels_for_mime_type("application/json")
        self.assertIn("json", labels)

    def test_audio(self):
        labels = _default_labels_for_mime_type("audio/mp3")
        self.assertIn("audio", labels)

    def test_video(self):
        labels = _default_labels_for_mime_type("video/mp4")
        self.assertIn("video", labels)

    def test_unknown_fallback(self):
        labels = _default_labels_for_mime_type("application/octet-stream")
        self.assertIn("wallet file", labels)


class TestDisplayMimeType(unittest.TestCase):
    def test_pdf(self):
        self.assertEqual(_display_mime_type("application/pdf"), "PDF document")

    def test_image(self):
        self.assertIn("image", _display_mime_type("image/png").lower())

    def test_json(self):
        self.assertIn("JSON", _display_mime_type("application/json"))

    def test_empty(self):
        self.assertEqual(_display_mime_type(""), "Unknown file")

    def test_encrypted(self):
        result = _display_mime_type("application/octet-stream")
        self.assertIn("Encrypted", result)


class TestFallbackDocumentProfileOutput(unittest.TestCase):
    def test_returns_dict_with_required_keys(self):
        result = _fallback_document_profile_output(file_name="test.pdf", mime_type="application/pdf")
        self.assertIn("output_policy", result)
        self.assertIn("profile", result)
        self.assertIn("summary", result)
        self.assertIn("upload_state", result)

    def test_summary_mentions_mime_type(self):
        result = _fallback_document_profile_output(file_name="test.pdf", mime_type="application/pdf")
        self.assertIn("PDF", result["summary"])

    def test_upload_state_has_redacted_filename(self):
        result = _fallback_document_profile_output(file_name="alice_id.pdf", mime_type="application/pdf")
        self.assertEqual(result["upload_state"]["fileName"], "document.pdf")


class TestClassifyDocumentProfile(unittest.TestCase):
    def test_uses_organizer_summary_when_present(self):
        public_inputs = {"organizer_summary": "Tax return document"}
        self.assertEqual(_classify_document_profile(public_inputs), "Tax return document")

    def test_falls_back_to_labels(self):
        public_inputs = {"organizer_summary": "", "organizer_labels": ["pdf", "document"]}
        result = _classify_document_profile(public_inputs)
        self.assertIn("pdf", result)

    def test_falls_back_to_mime_type_display(self):
        public_inputs = {"organizer_summary": "", "organizer_labels": [], "mime_type": "application/pdf"}
        self.assertEqual(_classify_document_profile(public_inputs), "PDF document")


class TestSummarizeDocumentProfile(unittest.TestCase):
    def test_includes_mime_type(self):
        result = _summarize_document_profile({"mime_type": "application/pdf"})
        self.assertIn("application/pdf", result)

    def test_includes_node_count_when_present(self):
        result = _summarize_document_profile({"mime_type": "text/plain", "node_count": 42})
        self.assertIn("42", result)

    def test_falls_back_for_missing_fields(self):
        result = _summarize_document_profile({})
        self.assertIn("·", result)


class TestSafeOrganizerSignal(unittest.TestCase):
    def test_extracts_summary(self):
        result = _safe_organizer_signal({"summary": "Brief summary"})
        self.assertEqual(result.get("summary"), "Brief summary")

    def test_drops_empty_fields(self):
        result = _safe_organizer_signal({"summary": "", "text": "", "output_policy": ""})
        self.assertEqual(result, {})

    def test_includes_profile_fields(self):
        result = _safe_organizer_signal({"summary": "s", "profile": {"chunk_count": 5, "profile_type": "rag"}})
        self.assertIn("profile", result)
        self.assertEqual(result["profile"]["chunk_count"], 5)


class TestBuildPrivacySearchText(unittest.TestCase):
    def test_includes_summary(self):
        public_inputs = {
            "organizer_summary": "Tax document",
            "organizer_labels": [],
            "output_policies": [],
        }
        result = _build_privacy_search_text([], public_inputs)
        self.assertIn("Tax document", result)

    def test_includes_labels(self):
        public_inputs = {
            "organizer_summary": "",
            "organizer_labels": ["pdf", "document"],
            "output_policies": [],
            "mime_type": "application/pdf",
        }
        result = _build_privacy_search_text([], public_inputs)
        self.assertIn("pdf", result)


class TestBuildPrivacyVectorTerms(unittest.TestCase):
    def test_includes_labels(self):
        public_inputs = {
            "organizer_labels": ["pdf", "document"],
            "mime_type": "application/pdf",
        }
        terms = _build_privacy_vector_terms([], public_inputs)
        self.assertIn("pdf", terms)
        self.assertIn("document", terms)

    def test_deduplicates(self):
        public_inputs = {
            "organizer_labels": ["pdf", "pdf"],
            "mime_type": "",
        }
        terms = _build_privacy_vector_terms([], public_inputs)
        self.assertEqual(terms.count("pdf"), 1)

    def test_respects_limit(self):
        public_inputs = {
            "organizer_labels": [f"label{i}" for i in range(30)],
        }
        terms = _build_privacy_vector_terms([], public_inputs)
        self.assertLessEqual(len(terms), 24)


if __name__ == "__main__":
    unittest.main()
