# Offgrid Minds Architecture Decision Records

Every major engineering decision should record:

- Decision
- Reason
- Alternatives Considered
- Consequences
- Date

---

## ADR-001: Use A Local Filesystem Raw Source Vault For Milestone 1

**Decision:** Store immutable raw source files on the local filesystem under a vault root.

**Reason:** The first milestone needs durability, inspectability, and simple recovery before distributed storage is justified.

**Alternatives Considered:** Object storage, database BLOB storage, Git LFS, content-addressed storage only.

**Consequences:** The vault is easy to inspect and Pi 5 friendly. Future implementations can replace the storage backend because records store artifact IDs, checksums, and paths separately.

**Date:** 2026-07-06

---

## ADR-002: Use SQLite For The Intake Ledger And Repository Core

**Decision:** Use SQLite for the Intake Ledger and minimal Knowledge Repository Core.

**Reason:** SQLite is durable, local, dependency-free, testable, and appropriate for a single-node vertical slice.

**Alternatives Considered:** Postgres, DuckDB, JSON files only, custom append-only logs only.

**Consequences:** The milestone can run on a laptop or Raspberry Pi 5 without services. Later storage layers can be extracted behind the current module APIs.

**Date:** 2026-07-06

---

## ADR-003: Use UUID4 For Initial Permanent IDs

**Decision:** Use UUID4 for source, revision, Knowledge Object, evidence, relationship, and audit IDs in the first implementation.

**Reason:** UUID4 is available in the Python standard library and avoids environmental assumptions.

**Alternatives Considered:** UUIDv7, ULID, deterministic IDs from checksums, database integer IDs.

**Consequences:** IDs are stable and globally unique, but not time-sortable. The architecture permits migrating the ID generator later without changing stored record semantics.

**Date:** 2026-07-06

---

## ADR-004: Defer OCR, Embeddings, Vector Search, Pack Compilation, And Agents

**Decision:** Milestone 1 implements only the Raw Source Vault, Intake Ledger, and Knowledge Repository Core.

**Reason:** The approved roadmap requires one functional vertical slice and explicitly forbids skipping ahead.

**Alternatives Considered:** Building OCR first, adding vector search early, implementing pack compilation immediately.

**Consequences:** The system proves provenance, immutability, audit, and repository object storage before advanced processing begins.

**Date:** 2026-07-06
