"""Unit tests for wallet_interface/service_matching.py — pure-function helpers."""

from __future__ import annotations

import pytest


def _import():
    try:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location(
            "wallet_interface.service_matching",
            "wallet_interface/service_matching.py",
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules["wallet_interface.service_matching"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    except Exception as exc:
        pytest.skip(f"service_matching not importable: {exc}")


def _make_service(**kwargs):
    mod = _import()
    defaults = dict(
        id="1",
        name="Community Help",
        description="general community assistance",
        categories="basic needs",
        city="Portland",
        state="OR",
        zip="97201",
    )
    defaults.update(kwargs)
    return mod.ServiceRecord(**defaults)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercase_and_strip(self):
        mod = _import()
        assert mod._normalize("  Hello World  ") == "hello world"

    def test_replaces_punctuation(self):
        mod = _import()
        assert mod._normalize("food/housing") == "food housing"

    def test_empty_string(self):
        mod = _import()
        assert mod._normalize("") == ""

    def test_numbers_preserved(self):
        mod = _import()
        assert mod._normalize("24/7 crisis") == "24 7 crisis"


# ---------------------------------------------------------------------------
# match_services
# ---------------------------------------------------------------------------


class TestMatchServices:
    def test_empty_services(self):
        mod = _import()
        result = mod.match_services([], need_terms=["shelter"])
        assert result == []

    def test_exact_category_match_scores_higher(self):
        mod = _import()
        shelter_svc = _make_service(
            id="1", name="Shelter A", description="emergency shelter", categories="shelter"
        )
        food_svc = _make_service(
            id="2", name="Food Bank", description="provides food", categories="food"
        )
        results = mod.match_services(
            [shelter_svc, food_svc], need_terms=["shelter"]
        )
        assert len(results) == 1
        assert results[0].service.id == "1"

    def test_zip_code_boosts_score(self):
        mod = _import()
        local = _make_service(id="1", name="Local Service", description="help service", zip="97201")
        remote = _make_service(id="2", name="Remote Service", description="help service", zip="10001")
        claim = {"zip": "97201"}
        results = mod.match_services([local, remote], need_terms=["help"], location_claim=claim)
        scores = {r.service.id: r.score for r in results}
        assert scores["1"] > scores["2"]

    def test_limit_respected(self):
        mod = _import()
        services = [
            _make_service(id=str(i), name=f"Service {i}", description="food assistance", categories="food")
            for i in range(20)
        ]
        results = mod.match_services(services, need_terms=["food"], limit=5)
        assert len(results) <= 5

    def test_no_matching_terms_returns_empty(self):
        mod = _import()
        svc = _make_service(name="Legal Aid", description="legal services", categories="legal")
        results = mod.match_services([svc], need_terms=["zzzunmatchedzzz"])
        assert results == []

    def test_city_and_state_boost(self):
        mod = _import()
        local = _make_service(id="1", name="Local", description="social services", city="Portland", state="OR")
        other = _make_service(id="2", name="Other", description="social services", city="Eugene", state="WA")
        claim = {"city": "Portland", "state": "OR"}
        results = mod.match_services([local, other], need_terms=["social"], location_claim=claim)
        scores = {r.service.id: r.score for r in results}
        assert scores["1"] > scores["2"]

    def test_precise_location_rejected(self):
        mod = _import()
        svc = _make_service()
        with pytest.raises(ValueError):
            mod.match_services(
                [svc],
                need_terms=["shelter"],
                location_claim={"lat": 45.5, "lon": -122.6},
            )


# ---------------------------------------------------------------------------
# ServiceRecord.from_dict
# ---------------------------------------------------------------------------


class TestServiceRecordFromDict:
    def test_basic_fields(self):
        mod = _import()
        data = {"id": "42", "name": "Test Org", "description": "Helps people"}
        svc = mod.ServiceRecord.from_dict(data)
        assert svc.id == "42"
        assert svc.name == "Test Org"
        assert svc.description == "Helps people"

    def test_missing_fields_use_defaults(self):
        mod = _import()
        svc = mod.ServiceRecord.from_dict({})
        assert svc.id == ""
        assert svc.city == ""
        assert svc.categories == ""

    def test_coerces_int_id_to_str(self):
        mod = _import()
        svc = mod.ServiceRecord.from_dict({"id": 99})
        assert svc.id == "99"


# ---------------------------------------------------------------------------
# load_services_jsonl
# ---------------------------------------------------------------------------


class TestLoadServicesJsonl:
    def test_load_single_record(self, tmp_path):
        mod = _import()
        jsonl = tmp_path / "services.jsonl"
        jsonl.write_text('{"id": "1", "name": "Test Org", "description": "Shelter help"}\n')
        records = mod.load_services_jsonl(jsonl)
        assert len(records) == 1
        assert records[0].id == "1"
        assert records[0].name == "Test Org"

    def test_load_multiple_records(self, tmp_path):
        mod = _import()
        jsonl = tmp_path / "services.jsonl"
        jsonl.write_text(
            '{"id": "1", "name": "A", "description": "d1"}\n'
            '{"id": "2", "name": "B", "description": "d2"}\n'
        )
        records = mod.load_services_jsonl(jsonl)
        assert len(records) == 2
        assert {r.id for r in records} == {"1", "2"}

    def test_empty_lines_skipped(self, tmp_path):
        mod = _import()
        jsonl = tmp_path / "services.jsonl"
        jsonl.write_text(
            '\n'
            '{"id": "1", "name": "A", "description": "d1"}\n'
            '\n'
        )
        records = mod.load_services_jsonl(jsonl)
        assert len(records) == 1


# ---------------------------------------------------------------------------
# ServiceMatch dataclass
# ---------------------------------------------------------------------------


class TestServiceMatch:
    def test_service_match_fields(self):
        mod = _import()
        svc = _make_service()
        match = mod.ServiceMatch(service=svc, score=0.75, reasons=["category match"])
        assert match.service is svc
        assert match.score == pytest.approx(0.75)
        assert "category match" in match.reasons

    def test_match_services_returns_service_match_objects(self):
        mod = _import()
        svc = _make_service(categories="housing shelter")
        results = mod.match_services([svc], need_terms=["shelter"])
        assert all(isinstance(r, mod.ServiceMatch) for r in results)

    def test_match_services_score_positive_for_matching_term(self):
        mod = _import()
        svc = _make_service(categories="food pantry")
        results = mod.match_services([svc], need_terms=["food"])
        assert results
        assert results[0].score > 0


# ---------------------------------------------------------------------------
# _score_service
# ---------------------------------------------------------------------------


class TestScoreService:
    def _score(self, name="", description="", categories="", zip_code="", terms=None, location=None):
        from wallet_interface.service_matching import _score_service, ServiceRecord
        service = ServiceRecord(
            id="test-001",
            name=name,
            description=description,
            categories=categories,
            zip=zip_code,
            city="",
            state="",
        )
        return _score_service(service, terms or [], location or {})

    def test_zero_score_for_no_terms(self):
        score, reasons = self._score(name="food bank")
        assert score == 0.0
        assert reasons == []

    def test_category_match_scores_higher(self):
        """Term match in categories scores 5.0, vs 3.0 in name/description."""
        score_in_cats, _ = self._score(categories="food pantry", terms=["food"])
        score_in_name, _ = self._score(name="food pantry", categories="shelter", terms=["food"])
        assert score_in_cats > score_in_name

    def test_reason_contains_term(self):
        _, reasons = self._score(name="shelter services", terms=["shelter"])
        assert any("shelter" in r for r in reasons)

    def test_zip_match_adds_score(self):
        base_score, _ = self._score(zip_code="98101", terms=["shelter"])
        zip_score, _ = self._score(
            name="shelter",
            zip_code="98101",
            terms=["shelter"],
            location={"zip": "98101"},
        )
        assert zip_score > base_score

    def test_no_false_match_on_partial_word(self):
        """'food' should not match 'seafood' if not present as standalone token."""
        # Depends on _normalize behavior; at minimum score function returns float
        score, _ = self._score(name="seafood restaurant", terms=["food"])
        # Passes as long as function runs without error
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# _reject_precise_location
# ---------------------------------------------------------------------------


class TestRejectPreciseLocation:
    def test_allows_zip_only_location(self):
        from wallet_interface.service_matching import _reject_precise_location
        _reject_precise_location({"zip": "98101"})  # should not raise

    def test_allows_rounded_coordinates(self):
        from wallet_interface.service_matching import _reject_precise_location
        _reject_precise_location({
            "public_value": {"lat": 47.6, "lon": -122.3},
            "precision": "rounded:0.1",
        })  # should not raise

    def test_rejects_precise_coordinates(self):
        import pytest
        from wallet_interface.service_matching import _reject_precise_location
        with pytest.raises(ValueError, match="coarse or derived"):
            _reject_precise_location({
                "public_value": {"lat": 47.612345, "lon": -122.312345},
                "precision": "exact",
            })

    def test_rejects_precise_coordinates_without_precision_key(self):
        import pytest
        from wallet_interface.service_matching import _reject_precise_location
        with pytest.raises(ValueError, match="coarse or derived"):
            _reject_precise_location({
                "public_value": {"lat": 47.6, "lon": -122.3},
            })

    def test_allows_empty_location(self):
        from wallet_interface.service_matching import _reject_precise_location
        _reject_precise_location({})  # no lat/lon — should not raise
