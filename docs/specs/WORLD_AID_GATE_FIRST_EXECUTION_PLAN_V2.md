# World Aid Gate-first execution-plan construction v2

Status: validation-only repository foundation; not installed, approved, or
runtime-authorizing.

## Problem addressed

An immutable sealed descriptor proves that plan bytes did not change after
sealing. It does not prove that a caller was allowed to choose those bytes.
The G038, G039, and G040 native plans contain tool and input paths, commands,
environment values, resource bounds, output paths, and expiration values.
Those values must not come from a supervisor task, CLI argument, environment
variable, or other agent-controlled input.

`scripts/build_world_aid_gate_first_execution_plans.py` defines a bounded v2
candidate-validation contract. It accepts one canonical profile only when the
profile's exact digest is supplied separately as
`expected_profile_sha256`. It materializes only the three exact native plan
byte strings embedded in that profile. Each plan digest is cross-bound to:

- the exact selection approval bytes and the direct in-memory result of the
  existing nine-signature Gate verifier;
- the exact external operator-policy bytes;
- the exact independently administered deployment-conformance attestation;
- the exact runner path and digest bound by the signed approval;
- the external network-boundary-attestation digest used by the native plan;
  and
- the exact plan builder, plan-set schema, v2 transport codec, transport input
  schema, transport result schema, transport protocol specification, and
  strict receipt-verifier digests.

The signed approval's reviewed-artifact digests for the launcher protocol,
launcher, Gate verifier, and all three runners are also compared with the
actual repository files before the transport is imported. The independently
administered deployment attestation must cross-bind those exact protocol,
launcher, and Gate-verifier digests, the reviewed root commit, the reviewed
objective-heap digest, the policy digest, a syntactically valid administrator
identity, and an issuance time no later than the signed approval.

The current v1 policy is required to remain `mode=verify-only`, with
`run_selection_enabled=false` and no injected runners for this candidate
contract. The v1 policy parser can represent enabled runner entries, but the
current launcher exposes no execution CLI. The profile separately advertises
the future `world-aid-runner-transport/v2`,
`sealed-fd-json/v2`, and `stdout-json/v2` contracts; those declarations do not
alter or enable launcher v1.

The validator rejects an unexpected profile digest, duplicate JSON keys,
non-finite numbers, noncanonical profile bytes, unknown fields, oversized or
deeply nested JSON, authority drift, reordered goals, runner drift,
native-plan digest drift, and expiration drift. When candidate plan objects
are supplied for comparison, any changed tool path, command, environment,
input, resource limit, or output path is rejected because its canonical bytes
differ from the externally digest-bound profile.

After the profile digest, Gate authority, complete dependency closure, and
signed repository artifacts pass, the reference validator lazily imports the
bound v2 transport. Every returned payload must then pass
`world_aid_runner_transport_v2._decode_plan`, round-trip through the native
runner's plan serializer without drift, and produce the same native execution
plan digest. This prevents the plan-set validator from accepting a payload
that its eventual transport or native constructor would reject.

G038 plan input is validation-only even within v2. The transport can decode
its plan, but it categorically excludes G038 success results because the
frozen native receipt lacks plan and boundary-attestation digests. A
three-goal execution wave therefore remains impossible until a separately
reviewed G038 receipt revision closes that binding gap. The presence of a
validated G038 candidate plan does not make it result-capable.

## Authority boundary

The `gate_verifier_summary` argument is trusted only when it is the direct
Python return value of `verify_world_aid_gate_0b.verify_approval` in the same
sealed launcher operation. Loading a summary from JSON, stdin, a task bundle,
or an environment variable does not prove signatures and is outside this
contract.

There is an important one-way authority boundary: the current signed selection
approval v2, operator policy v1, and deployment attestation v1 do not contain
the digest of this new plan profile. They therefore cannot authenticate it.
`expected_profile_sha256` must arrive through a separately authenticated,
independently administered channel. Supplying a digest calculated from the
same caller-controlled profile being validated proves nothing and is
forbidden. Until a new governance/deployment contract binds that digest, the
result remains an unauthorizing candidate plan set.

Likewise, the authoritative launcher must snapshot the operator policy,
deployment attestation, plan profile, builder, all contract dependencies,
runners, and all native plan inputs through its external root-owned
no-symlink boundary. Repository paths and ordinary `Path.read_bytes()` calls
in the validation-only reference are not a production installation boundary.

The lazy ordinary Python import used here is only a constructor-parity check
for repository review. It is vulnerable to import-cache substitution and
read-then-import time-of-check/time-of-use races and is therefore
unacceptable for production execution. A production launcher must load only
sealed, independently installed modules from the already snapshotted and
digest-verified dependency closure, in an isolated process, before granting
the process any execution capability.

The output type stores native plan bytes rather than mutable parsed mappings.
It has `runtime_authorized=false` and exposes no run method. The module has no
CLI, writes no file, and starts no process. Its post-validation lazy import is
strictly unauthorizing.

## Deliberately disabled template

`docs/governance/templates/gate-first-execution-plan-set.template.json` is
intentionally nonconformant:

- `status` is `pending`;
- `candidate_validation_enabled` is false;
- authority and contract digests are placeholders; and
- the required three-plan array is empty.

Agents must not fill, sign, or install it on behalf of human operators.

## Remaining deployment work

This contract does not change the v1 launcher, which remains verify-only. A
future reviewed protocol revision still needs to:

1. install and bind the builder, plan schema, transport codec, transport
   schemas, transport specification, receipt verifier, and native runners
   outside repository authority as one sealed dependency closure;
2. add a signed or independently administered authority record that binds the
   exact completed profile digest;
3. securely snapshot the completed canonical profile and all referenced
   artifacts;
4. pass only the externally digest-bound plan bytes over the reviewed v2
   sealed-FD transport;
5. enforce AppArmor, network namespace, mount, cgroup, process-tree, timeout,
   and output boundaries before importing runner code;
6. validate the strict stdout result and publish the aggregate receipt
   atomically; and
7. receive fresh human and independent-operator review before enabling any
   run-selection command.

Until that work and external evidence exist, G038-G040 execution remains
blocked.
