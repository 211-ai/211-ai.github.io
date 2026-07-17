# Unit Tests

Pure unit tests that run without network access, databases, or external services. Each test module should mirror the production module it covers.

## Test coverage

| Module | Test file | Status | Tests |
| --- | --- | --- | --- |
| `scraper/config.py` | `test_scraper_config.py` | ✅ | 15 |
| `scraper/acquisition/` | `test_scraper_acquisition.py` | ✅ (skip on missing deps) | 6 |
| `scraper/parsing/` + `parsing/processor.py` | `test_scraper_parsing.py` | ✅ (skip on missing deps) | 16 |
| `scraper/enrichment/` | `test_scraper_enrichment.py` | ✅ (skip on missing deps) | 8 |
| `scraper/export/` | `test_scraper_export.py` | ✅ (skip on missing deps) | 6 |
| `scraper/orchestration/` | `test_scraper_orchestration.py` | ✅ (skip on missing deps) | 7 |
| `scraper/utils.py` | `test_scraper_utils.py` | ✅ | 26 |
| `wallet_interface/helpers/_ai_routing.py` | `test_wallet_ai_routing_helpers.py` | ✅ | 19 |
| `wallet_interface/helpers/_auth.py` | `test_wallet_auth_helpers.py` | ✅ | 20 |
| `wallet_interface/helpers/_auth.py` (crypto) | `test_wallet_auth_crypto.py` | ✅ | 33 |
| `wallet_interface/helpers/_app.py` | `test_wallet_app_helpers.py` | ✅ | 17 |
| `wallet_interface/helpers/` | `test_wallet_helpers.py` | ✅ (CID helpers skip on missing deps) | 14 |
| `wallet_interface/helpers/_records.py` | `test_wallet_records_helpers.py` | ✅ | 83 |
| `wallet_interface/hmis/models.py` + `errors.py` + adapters + service | `test_hmis_models.py` | ✅ | 44 |
| `wallet_interface/hmis/mapper.py` + `consent.py` | `test_hmis_mapping_consent.py` | ✅ | 29 |
| `wallet_interface/helpers/_storage.py` | `test_wallet_storage_helpers.py` | ✅ | 66 |
| `wallet_interface/helpers/_storage_filecoin.py` | `test_wallet_storage_filecoin.py` | ✅ | 22 |
| `wallet_interface/helpers/_tts_config.py` | `test_tts_config.py` | ✅ | 74 |
| `wallet_interface/helpers/_tts_gradio.py` | `test_tts_gradio.py` | ✅ | 74 |
| `wallet_interface/helpers/_tts_http.py` | `test_tts_http.py` | ✅ | 33 |
| `wallet_interface/helpers/_tts_normalization.py` | `test_tts_normalization.py` | ✅ | 67 |
| `wallet_interface/helpers/_tts_normalization.py` (extended) | `test_tts_normalization_extended.py` | ✅ | 51 |
| `wallet_interface/helpers/_tts_pipeline.py` | `test_tts_pipeline.py` | ✅ | 11 |
| `wallet_interface/helpers/_tts_client.py` | `test_tts_client.py` | ✅ | 27 |
| `wallet_interface/helpers/_tts.py` (routing) | `test_tts_routing.py` | ✅ | 16 |
| `wallet_interface/helpers/_auth.py` (notify) | `test_wallet_auth_notify.py` | ✅ | 17 |
| `wallet_interface/helpers/_auth.py` (UCAN) | `test_wallet_auth_ucan.py` | ✅ | 18 |
| `wallet_interface/ops.py` (helpers) | `test_wallet_ops_helpers.py` | ✅ | 27 |
| `wallet_interface/ops.py` (validation) | `test_wallet_ops_validation.py` | ✅ | 21 |
| `wallet_interface/service_matching.py` | `test_service_matching.py` | ✅ | 30 |
| `wallet_interface/schemas/` | `test_wallet_schemas.py` | ✅ (Pydantic tests skip when not installed) | 22 |
| `wallet_interface/schemas/app_schemas.py` | `test_portal_schemas.py` | ✅ | 15 |
| `wallet_interface/helpers/_auth.py` (magic UCAN) | `test_wallet_auth_magic_ucan.py` | ✅ | 44 |
| `wallet_interface/schemas/proof_schemas.py` + `record_schemas.py` + `export_schemas.py` | `test_wallet_proof_record_export_schemas.py` | ✅ | 31 |

## Run unit tests

```bash
python -m pytest tests/unit/ -q
```

