# Integration Tests

Tests that exercise end-to-end integration between platform components. These require live external services or heavier local setup.

## Contents

| Test file | Dependencies |
| --- | --- |
| `test_chainlink_cre_consensus.py` | Chainlink CRE endpoint |
| `test_llm_consensus_p2p.py` | libp2p peer network |

## Running integration tests

Integration tests are **not** in the default CI suite. Run them manually:

```bash
python -m pytest tests/integration/ -q --timeout=300
```

## Adding new integration tests

- Gating pattern: skip if the required env variable or service is not available
- Use `pytest.mark.integration` to tag tests
- Do **not** add integration tests to the `python-unit-tests` or `python-contract-tests` CI jobs
