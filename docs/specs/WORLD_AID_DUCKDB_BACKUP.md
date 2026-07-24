# World Aid DuckDB backup and restore contract

**Status: proposed and NOT APPROVED.** This document is a contract for Gate
0B-selection and G040. It is not evidence that a backup has run.

G040 proves only a **raw opaque backup** of the synthetic DuckDB smoke
database. The one local writer checkpoints the database, copies it to a
separate approved local path, records a SHA-256 over the raw bytes, restores
those raw bytes to a new local path, and checks database/state-machine
integrity. The payload inserted before backup is opaque synthetic bytes.
G040 does not create an application envelope, manage a key, or search the
files for a plaintext marker.

G033 separately owns authenticated envelope encryption, plaintext-marker
absence, encrypted/authenticated production backup, key rotation, retention,
and deletion. A successful G040 raw backup/restore receipt is not evidence for
any of those G033 controls. DuckDB file storage is never described as
application encryption: **DuckDB file storage is never described as application encryption.**

The runtime smoke owned by G040 must prove, with opaque synthetic values only:

1. transaction commit and rollback, compare-and-swap, uniqueness, and atomic
   outbox behavior;
2. refusal of a second writer and of direct worker file access;
3. clean checkpoint, crash-boundary restart, reopen, and teardown;
4. raw opaque backup, restore to a new local path, byte checksum/read-back,
   database integrity, and corruption detection; and
5. no network, extension autoload/autoinstall, wheelhouse mutation, lockfile
   mutation, or approval mutation.

The G040 smoke manifest records the bound selection-record ID and digest,
wheel/lock digests, source and restored synthetic database identities, raw
backup digest, creation/expiry timestamps, cleanup result, and redacted
outcome. It never records secrets, raw World bindings, documents, nullifiers,
eligibility reasons, or key material. Retention, deletion, key rotation,
plaintext-marker absence, application envelopes, and production encrypted
backup implementation belong to G033 and are not claimed here.

The exact retention period, encrypted-volume identifier, backup tool and
restore operator remain human selections. Exceptions require an ID, rationale,
owner, compensating control, and expiry in the signed Gate 0B-selection
record.
