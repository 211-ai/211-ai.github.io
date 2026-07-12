# Unit Tests

Pure unit tests that run without network access, databases, or external services. Each test module should mirror the production module it covers.

## Target layout

| Module | Test file |
| --- | --- |
| `scraper/config.py` | `test_scraper_config.py` |
| `scraper/parsing/processor.py` | `test_scraper_processor.py` |
| `wallet_interface/app_service.py` | `test_wallet_service.py` |
| `wallet_interface/proof_backends.py` | `test_proof_backends.py` |
| `wallet_interface/world_id.py` | `test_world_id.py` |

## Current state

Unit tests are being migrated here incrementally. Existing tests live in `../` during the transition. Run only unit tests with:

```bash
python -m pytest tests/unit/ -q
```
