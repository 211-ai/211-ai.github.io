# World Aid ZKP toolchain smoke specification

## NOT APPROVED — locked input contract only

This fixture is owned by WORLDCOIN-G041 as a bounded, backend-neutral input
contract. It is not a Gate 0B selection, a toolchain receipt, a proof of
humanity, an eligibility proof, a production circuit, or production trust.
G039 alone may execute an approved native toolchain after human Gate 0B
selection binds the exact architecture, backend, version, binary/image
digest, licenses, provenance, SBOM, vulnerability disposition, flags, resource
bounds, offline location, and expiry.

## Circuit and inputs

- `Nargo.toml`, `Nargo.lock`, and `src/main.nr` are locked repository inputs.
- The public input is the field value `7`.
- The private witness is the field value `7`.
- The circuit has at most two witness fields and one equality assertion.
- No dependency, generated key, ceremony parameter, proving key, verifying
  key, or aid-policy claim is part of this smoke.

## Required G039 evidence

G039 must use the selected native architecture and checksum-pinned binary or
immutable image from a read-only offline location. With network access,
package registries, image registries, and compiler update behavior denied, it
must record:

1. two isolated repeat-build runs with byte-identical artifact hashes;
2. bounded proof output and a successful verification result for the locked
   public/private input pair;
3. compiler/backend/version and deterministic flags;
4. resource usage within the signed time, memory, and output bounds; and
5. the deny evidence, artifact digests, reviewers, exceptions, and expiry.

Any missing, conflicting, stale, wrong-architecture, tampered, mutable,
unbounded, or unpinned input fails closed. A proof or verification result for
this smoke does not authorize G012, an aid payout, a production deployment,
or a Groth16 ceremony. Developer-generated Groth16 parameters are never
production trust.

## Forbidden G041 actions

The preparation lane performs no tool import or execution, package or
container action, subprocess smoke, download, registry contact, secret lookup,
cache mutation, circuit build, proof, verification, or parameter generation.
