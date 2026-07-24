# World Human-Aid DuckDB Storage ADR

- Status: proposed; Gate 0B approval required
- Date: 2026-07-24
- Scope: World human-aid identity, eligibility, payout, and reconciliation state
- Supersedes: the PostgreSQL-specific storage direction in the initial World
  human-aid implementation plan

## Decision

Use DuckDB as the reference transactional store for the first World human-aid
deployment, behind a dedicated single-host, single-writer storage service.
Application workers must not open independent writable DuckDB connections.
They use a narrow authenticated local IPC or loopback service boundary owned by
one writer process.

This decision does not approve a DuckDB version, wheel, deployment, or security
exception. Gate 0B selection must bind the exact runtime and topology, and Gate
0B launch must bind successful offline, crash, restore, and egress-deny
receipts.

## Why the topology is part of the decision

DuckDB is an embedded database with a single external writer boundary. The
repository already accounts for that property in
`ipfs_accelerate_py.agent_supervisor.duckdb_state` by serializing access with
thread and process locks. A payout system must not rely on every web or worker
process independently coordinating writable connections.

The World human-aid boundary therefore has these invariants:

1. Exactly one supervised writer service owns the writable database connection
   and schema migration lease.
2. API, proof, signer, reconciliation, and audit workers submit typed commands
   through an authenticated local interface. They never receive a writable
   database path.
3. The writer validates compare-and-swap versions, uniqueness constraints,
   immutable idempotency payloads, and authorization references inside one
   transaction.
4. State mutation and its outbox event commit in the same transaction.
5. Writer unavailability, lock ambiguity, schema drift, or a second writer
   fails closed. There is no JSON, SQLite, in-memory, or direct-file fallback.
6. Multi-host active-active writing is out of scope. Crossing that boundary
   requires a new storage ADR, migration plan, and human gate.

## Confidentiality boundary

DuckDB file storage is not treated as the encryption boundary. Sensitive values
are authenticated-envelope-encrypted before insertion. KMS, HSM, or approved
secret-provider key references remain outside the database; raw key material
must not be serialized.

The database, WAL, temporary directory, snapshots, and backups additionally
reside on an approved encrypted volume with least-privilege filesystem access.
Tests plant synthetic secret markers and prove that plaintext markers do not
appear in the database file, WAL, temporary files, backup, logs, or receipts.

Public and operator-facing projections remain authenticated and
minimum-necessary. They must not serialize raw durable models, wallet
snapshots, documents, World proof payloads, nullifiers, eligibility reasons, or
treasury material.

## Transaction and recovery requirements

The schema and writer service must provide:

- versioned, checksum-bound forward migrations;
- uniqueness for SIWE challenges, scoped World replay keys, eligibility
  nullifiers, payout idempotency/payload pairs, submission attempts,
  transaction hashes, and chain-event identities;
- compare-and-swap state transitions and fencing tokens;
- an atomic outbox for signer, reconciliation, revocation, and audit work;
- bounded checkpointing and clean restart;
- crash recovery after interruption before and after commit;
- encrypted, authenticated, read-back-verified backups;
- restore into a new path followed by integrity and state-machine checks;
- key rotation, retention, deletion, and disaster-recovery procedures; and
- an append-only redacted operational receipt for migration, backup, restore,
  and recovery exercises.

Only synthetic or development snapshots may be migrated autonomously.
Retiring, overwriting, or importing real plaintext state remains a separate,
recoverable human operation after backup and restore approval.

## Gate 0B supply-chain requirements

The selection record must bind:

- the exact CPython ABI, platform tag, DuckDB version, wheel filename, SHA-256,
  license, provenance, SBOM, vulnerability review, and offline wheelhouse
  location;
- the exact hash-pinned World-aid Python lock;
- the database, WAL, temporary, backup, and lock paths;
- filesystem owner and mode, encrypted-volume reference, resource limits, and
  backup/restore policy;
- locked runtime settings with `enable_external_access`,
  `autoinstall_known_extensions`, `autoload_known_extensions`, and
  `allow_community_extensions` all disabled, plus an isolated empty extension
  directory unless a later separately reviewed ADR explicitly permits one;
- the single-writer service identity and authenticated local client boundary;
- the prohibition on multi-host and multi-writer deployment; and
- approved exceptions and expiration.

The launch record additionally binds receipts proving:

- installation from an empty environment with indexes and network denied;
- transaction, rollback, uniqueness, compare-and-swap, and outbox behavior;
- rejection of a second writer and of direct worker write access;
- restart, crash-boundary, checkpoint, backup, restore, and teardown behavior;
- round-trip integrity for opaque, already-encrypted synthetic payloads without
  claiming that the DuckDB file itself is encrypted;
- no unapproved extension load, wheelhouse/dependency-lock mutation, approval
  mutation, or reviewed-input mutation; and
- a deliberate egress canary was blocked and reported.

The application-layer plaintext-marker, envelope-encryption, encrypted-backup,
and key-rotation tests execute later under G033. G040 cannot claim those
controls before the production repository exists.

## Consequences

This reduces bootstrap complexity because the first deployment does not need a
PostgreSQL server or container image. It also deliberately limits horizontal
write scaling and availability. The supervisor must not describe DuckDB as a
drop-in distributed transaction service.

Before workload or availability needs exceed a single writer, maintainers must
measure queue depth, write latency, recovery time, and backup size. A move to a
client-server or distributed store requires an independently reviewed
migration that preserves replay, idempotency, encryption, outbox, and audit
invariants.
