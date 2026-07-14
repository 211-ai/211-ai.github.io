# Unit Tests

Pure unit tests that run without network access, databases, or external services. Each test module should mirror the production module it covers.

## Test coverage

| Module | Test file | Status | Tests |
| --- | --- | --- | --- |
| `scraper/config.py` | `test_scraper_config.py` | ✅ | 15 |
| `scraper/acquisition/` | `test_scraper_acquisition.py` | ✅ (skip on missing deps) | 6 |
| `scraper/parsing/` | `test_scraper_parsing.py` | ✅ (skip on missing deps) | 6 |
| `scraper/enrichment/` | `test_scraper_enrichment.py` | ✅ (skip on missing deps) | 4 |
| `scraper/export/` | `test_scraper_export.py` | ✅ (skip on missing deps) | 4 |
| `scraper/orchestration/` | `test_scraper_orchestration.py` | ✅ (skip on missing deps) | 2 |
| `scraper/utils.py` | `test_scraper_utils.py` | ✅ | 17 |
| `wallet_interface/helpers/_auth.py` | `test_wallet_auth_helpers.py` | ✅ | 20 |
| `wallet_interface/helpers/` | `test_wallet_helpers.py` | ✅ (CID helpers skip on missing deps) | 14 |
| `wallet_interface/helpers/_tts_normalization.py` | `test_tts_normalization.py` | ✅ | 48 |
| `wallet_interface/ops.py` | `test_wallet_ops_helpers.py` | ✅ | 27 |
| `wallet_interface/service_matching.py` | `test_service_matching.py` | ✅ | 20 |

## Run unit tests

```bash
python -m pytest tests/unit/ -q
```

