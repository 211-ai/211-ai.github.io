# Unit Tests

Pure unit tests that run without network access, databases, or external services. Each test module should mirror the production module it covers.

## Test coverage

| Module | Test file | Status |
| --- | --- | --- |
| `scraper/config.py` | `test_scraper_config.py` | ✅ |
| `scraper/acquisition/` | `test_scraper_acquisition.py` | ✅ (skip on missing deps) |
| `scraper/parsing/` | `test_scraper_parsing.py` | ✅ (skip on missing deps) |
| `scraper/enrichment/` | `test_scraper_enrichment.py` | ✅ (skip on missing deps) |
| `scraper/export/` | `test_scraper_export.py` | ✅ (skip on missing deps) |
| `scraper/orchestration/` | `test_scraper_orchestration.py` | ✅ (skip on missing deps) |
| `scraper/utils.py` | `test_scraper_utils.py` | ✅ |
| `wallet_interface/helpers.py` | `test_wallet_helpers.py` | ✅ |
| `wallet_interface/service_matching.py` | `test_service_matching.py` | ✅ |

## Run unit tests

```bash
python -m pytest tests/unit/ -q
```
