# World Aid runner transport v2

Status: review-only protocol foundation. It grants no execution authority and
does not change the verify-only v1 Gate-first launcher.

## Protocol identities

- Transport: `world-aid-runner-transport/v2`
- Input schema: `world-human-aid-runner-input-envelope/v2`
- Input protocol: `sealed-fd-json/v2`
- Result schema: `world-human-aid-runner-result-envelope/v2`
- Result protocol: `stdout-json/v2`

The reviewed schemas are:

- `docs/schemas/world_aid/runner-transport-v2-input.schema.json`
- `docs/schemas/world_aid/runner-transport-v2-result.schema.json`

## Sealed input

G038, G039, and G040 plans may be decoded. The caller supplies independent
goal, approval, external-boundary, and native execution-plan digests. The
envelope and decoded frozen plan must match all four values exactly.

The input must be one canonical JSON object of at most 8 MiB in an anonymous
Linux memfd. Before any identity, seal, size, or content check, the codec pins
the inherited descriptor with `F_DUPFD_CLOEXEC`. It validates and reads only
that pinned identity and closes the duplicate on every path. The memfd must
carry `F_SEAL_SEAL`, `F_SEAL_SHRINK`, `F_SEAL_GROW`, and `F_SEAL_WRITE`.

The JSON decoder rejects duplicate or unknown keys, non-canonical bytes,
floating-point and non-finite numbers, integers outside signed 64-bit form,
excessive depth, excessive nodes, forbidden Unicode, and oversized input.
G038 network namespaces use exactly `net:[digits]`. G040 Python versions use
exactly three numeric components in the transport contract.

## Result boundary

Only G039 and G040 may produce v2 success results. Their native receipts
already carry execution-plan and boundary-attestation digests, and the codec
also compares all plan-derived receipt fields with the decoded sealed plan.
The `native_receipt_sha256` is over the native runner's actual canonical
receipt bytes: UTF-8/non-ASCII-preserving JSON for G039 and ASCII-escaped JSON
for G040.

The existing aggregate-receipt v1 envelope uses a different, ASCII-escaped
canonical digest for its embedded `native_receipt` object. The transport
therefore carries both distinct mappings:

- `native_receipt_sha256` hashes the exact native runner file bytes.
- `aggregate_receipt_object_sha256` hashes
  `verify_world_aid_gate_first_receipt.canonical_json_bytes(native_receipt)`.

An aggregate publisher must verify both and map only
`aggregate_receipt_object_sha256` to the existing aggregate receipt's embedded
object digest. It must never substitute the native-file digest.

G038 cannot produce or decode a v2 result. Its frozen receipt schema omits the
native execution-plan and boundary-attestation digests. Reported tool, cache,
or namespace fields do not repair that replay gap. G038 remains closed until a
new native receipt schema binds both digests and receives independent review.

`CanonicalResultWriter` accepts only a fresh, empty, write-only FIFO/anonymous
pipe. It atomically pins the pipe with `F_DUPFD_CLOEXEC`, consumes the caller's
descriptor, writes one canonical result, and closes its duplicate on success
or failure. Regular files, readable pipes, and prepopulated pipes are rejected.
Failures have no valid result object.

## Threat boundary

Descriptor pinning prevents later numeric-FD replacement from changing which
input or output object the codec uses. It is not a substitute for process
isolation. Hostile code in the same process can retain another duplicate of an
output pipe, interfere with scheduling, or invoke unrelated capabilities. A
future operator launcher must run the adapter in a minimal isolated process,
close all unreviewed descriptors, enforce the external deny-all sandbox, drain
the result pipe with independent bounds, and treat any extra byte or abnormal
exit as failure.

This module has no CLI and does not invoke G038, G039, or G040.
