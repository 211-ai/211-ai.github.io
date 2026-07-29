# Datasets Manipulator and Swissknife Symbolic Contract Analysis Task Board

This is the executable projection of
[`DATASETS_CONTRACT_ANALYSIS_OBJECTIVES.md`](DATASETS_CONTRACT_ANALYSIS_OBJECTIVES.md).
It is maintained by `ipfs_accelerate_py.agent_supervisor`; implementation
agents must not hand-edit generated task status or identity fields.

Program invariants:

- Integration branch: `codex/datasets-contract-analysis`.
- Static discovery, graph construction, proof, cache identity, finding
  admission, deduplication, and task projection are deterministic.
- LLMs receive bounded repair packets only after symbolic task admission.
- `unknown`, `unsupported`, `stale`, partial, and errored analysis fail closed.
- ZK evidence attests a reviewed deterministic computation; it does not prove
  unmodeled Python behavior.
- Every tracked recursive-tree object receives a CID and disposition, but only
  supported semantics may receive a `proved` verdict.
- The dataset manipulator may not report mock success or use process-randomized
  identity.
- Network, credentials, dependency installation, publication, and production
  changes are disabled unless an individual task explicitly authorizes them.
- Task completion requires current-tree deterministic validation evidence.

The objective daemon appends canonical `DSCON-*` task blocks below.
