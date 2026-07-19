> **These tests are NOT part of the default CI suite.** They test speculative features, external integrations, and adversarial scenarios that require live network access or non-deterministic behavior. Run them on-demand or in nightly CI.

# Experimental Tests

Speculative, simulation, and adversarial tests that test research-grade features or require live service dependencies.

## Contents

| Test file | Why experimental |
| --- | --- |
| `test_211_conversation_simulation.py` | Requires live LLM service |
| `test_llm_consensus.py` | Adversarial/probabilistic scenarios |
| `test_llm_consensus_adversarial.py` | Adversarial/probabilistic scenarios |
| `test_llm_consensus_p2p.py` | Requires libp2p peer network |
| `test_llm_consensus_privacy.py` | Adversarial/probabilistic scenarios |
| `test_llm_consensus_proof_verifiers.py` | Adversarial/probabilistic scenarios |
| `test_llm_router_consensus.py` | Requires external Chainlink endpoint |
| `test_hf_space_inference.py` | Requires live HuggingFace space |
| `test_analyze_slot_friendly_query_response_pairs.py` | Batch analysis, slow |
| `test_build_slotted_response_dag.py` | Requires large data artifacts |

All files are marked with `pytestmark = pytest.mark.experimental` so they can be deselected from any broad test run with `-m "not experimental"`.

## Run experimental tests

```bash
python -m pytest tests/experimental/ -q --timeout=300
```

Do not add experimental tests to the default CI job paths; instead add them to a nightly `workflow_dispatch`-only job.
