# OGM Expert Pack Specification v1.0

**Status:** draft v1.0 specification  
**Audience:** engineers building Offgrid Minds pack builders, validators, runtimes, and distribution tools  
**Primary runtime target:** Raspberry Pi 5, 8 GB RAM, offline, storage-expandable  

---

## 1. Purpose

An OGM Expert Pack is a compiled, portable knowledge module. It is not a
folder of PDFs, not a prompt bundle, and not a fine-tuned model. It is a
versioned artifact containing normalized Knowledge Objects, source
provenance, retrieval indexes, media references, relationships, validation
reports, and compatibility metadata.

The pack exists so a small offline model can reason over trusted evidence
without loading the full body of knowledge into RAM.

### Non-goals

- This specification does not define a specific database engine.
- This specification does not require a cloud marketplace or user account.
- This specification does not define the LLM prompt format.
- This specification does not require all raw source documents to be shipped
  inside every pack.

---

## 2. Terminology

- **Pack:** A compiled Expert Pack artifact.
- **Pack root:** The root directory inside an unpacked pack.
- **Knowledge Object:** A normalized unit of knowledge such as a Procedure,
  Part, Warning, Diagram, Specification, or Species.
- **Source:** A document, manual, image set, dataset, field note, catalog, or
  other input used to produce Knowledge Objects.
- **Locator:** A stable pointer into a source, such as page number, section
  ID, figure ID, timestamp, bounding box, or byte range.
- **Knowledge Volume:** A storage location that may contain packs, indexes,
  user memory, or cache data. The runtime MUST address packs through volume
  abstractions, never hard-coded storage paths.
- **Control plane:** Small human-readable metadata files used to inspect and
  validate the pack.
- **Data plane:** Large machine-readable indexes and object stores optimized
  for retrieval.

---

## 3. Pack Identity

Every pack MUST have a stable identity independent of filename and storage
location.

Required identity fields:

```yaml
pack_id: "ogm.pack.small-engine-repair"
pack_version: "1.0.0"
schema_version: "1.0"
content_revision: "2026-07-06.r1"
title: "Small Engine Repair"
publisher_id: "ogm.publisher.example"
primary_locale: "en-US"
```

Rules:

- `pack_id` MUST be globally unique within the OGM ecosystem.
- `pack_id` MUST use lowercase reverse-domain or OGM namespace form.
- `pack_version` MUST use semantic versioning: `MAJOR.MINOR.PATCH`.
- `schema_version` identifies this pack format, not the subject matter.
- `content_revision` identifies the source corpus build, not the software
  format.
- A runtime MUST NOT infer identity from a directory name, archive filename,
  mount path, or marketplace listing.

---

## 4. Artifact Forms

An Expert Pack MAY be distributed in either form:

1. **Unpacked directory:** A directory matching the canonical layout.
2. **Pack archive:** A compressed archive that expands to the canonical layout.

The runtime profile for Raspberry Pi 5 SHOULD prefer unpacked or
memory-mappable artifacts on SSD-class storage. Archive extraction MAY happen
at install time, but runtime retrieval MUST NOT require decompressing the
entire pack.

Recommended archive extensions:

- `.ogpack` for full pack archives.
- `.ogdelta` for delta updates.
- `.ogindex` for separately distributed rebuilt indexes.

Archive requirements:

- The archive MUST contain exactly one pack root.
- File paths inside the archive MUST be relative.
- File paths MUST NOT contain `..`, absolute paths, device paths, or symlinks
  escaping the pack root.
- The archive MUST include `manifest.yaml` at the pack root.
- Large data-plane files SHOULD be chunk-compressed independently, not
  compressed only at the archive layer.

---

## 5. Canonical Folder Structure

```text
pack-root/
  manifest.yaml
  compatibility.yaml
  checksums.sha256
  LICENSES/
    pack-license.txt
    source-licenses.yaml
  metadata/
    taxonomy.yaml
    locales.yaml
    source-catalog.yaml
    revision-history.yaml
    build-info.yaml
  objects/
    objects.jsonl.zst
    object-blocks/
      shard-00000.ogkb
      shard-00001.ogkb
  entities/
    entities.jsonl.zst
    aliases.fst
    entity-map.ogidx
  relationships/
    edges.jsonl.zst
    graph.oggraph
  sources/
    source-index.jsonl.zst
    locators.ogidx
  indexes/
    keyword/
      terms.ogidx
      postings.ogidx
    semantic/
      manifest.yaml
      vectors.ogvec
      object-map.ogidx
    metadata/
      facets.ogidx
    procedures/
      steps.ogidx
    warnings/
      hazards.ogidx
    tables/
      tables.ogidx
    media/
      images.ogidx
      diagrams.ogidx
  media/
    images/
      shard-00000/
    diagrams/
      shard-00000/
    thumbnails/
  validation/
    report.yaml
    coverage.json
    retrieval-tests.jsonl
  signatures/
    manifest.sig
    checksums.sig
```

### Required files

The following files MUST exist in every v1.0 pack:

- `manifest.yaml`
- `compatibility.yaml`
- `checksums.sha256`
- `LICENSES/pack-license.txt`
- `LICENSES/source-licenses.yaml`
- `metadata/taxonomy.yaml`
- `metadata/source-catalog.yaml`
- `metadata/revision-history.yaml`
- `metadata/build-info.yaml`
- `objects/objects.jsonl.zst`
- `entities/entities.jsonl.zst`
- `relationships/edges.jsonl.zst`
- `sources/source-index.jsonl.zst`
- `indexes/metadata/facets.ogidx`
- `indexes/keyword/terms.ogidx`
- `indexes/keyword/postings.ogidx`
- `validation/report.yaml`

### Optional files

Optional files MAY be omitted when unsupported by the source corpus:

- Semantic vector indexes.
- Image indexes.
- Diagram indexes.
- Table indexes.
- Procedure indexes.
- Warning indexes.
- Media thumbnails.
- Cryptographic signatures.
- Raw or normalized source documents.

If an optional capability is omitted, `manifest.yaml` MUST explicitly declare
the capability as unavailable. Runtime code MUST rely on the capability
manifest, not file probing.

---

## 6. Manifest

`manifest.yaml` is the authoritative control-plane record for the pack.

Required sections:

```yaml
schema_version: "1.0"
pack:
  id: "ogm.pack.small-engine-repair"
  version: "1.0.0"
  content_revision: "2026-07-06.r1"
  title: "Small Engine Repair"
  summary: "Repair and maintenance procedures for small gasoline engines."
  publisher_id: "ogm.publisher.example"
  primary_locale: "en-US"
  created_at: "2026-07-06T17:00:00Z"

capabilities:
  objects: true
  entities: true
  relationships: true
  keyword_search: true
  semantic_search: true
  images: true
  diagrams: true
  tables: true
  procedures: true
  warnings: true

counts:
  objects: 1842300
  entities: 412900
  relationships: 7900000
  sources: 11840
  images: 220000
  diagrams: 83000

runtime:
  minimum_ogm_runtime: "1.0.0"
  recommended_storage: ["ssd", "nvme", "nas"]
  pi5_profile:
    max_open_file_handles: 128
    recommended_cache_mb: 512
    semantic_index_load_policy: "paged"

integrity:
  checksum_file: "checksums.sha256"
  signature_policy: "optional-v1-required-marketplace"
```

Rules:

- The manifest MUST be parseable without loading any large data-plane file.
- Unknown manifest fields MUST be preserved by pack editing tools.
- Runtime-critical fields MUST be duplicated only when necessary; if
  duplicated, validators MUST check consistency.
- Capability flags MUST be treated as the contract between pack and runtime.

---

## 7. Compatibility

`compatibility.yaml` declares required and optional runtime features.

Example:

```yaml
format:
  schema_version: "1.0"
  min_reader_version: "1.0.0"
  forward_compatible_until: "1.x"

required_features:
  - object-jsonl-v1
  - source-locator-v1
  - keyword-index-v1
  - metadata-facets-v1

optional_features:
  - semantic-index-v1
  - diagram-index-v1
  - image-embedding-index-v1

breaking_change_policy:
  unknown_required_feature: "reject-pack"
  unknown_optional_feature: "ignore-feature"
  unknown_field: "preserve"
```

Rules:

- A runtime MUST reject a pack with an unknown required feature.
- A runtime MUST ignore unsupported optional features without rejecting the
  entire pack.
- A runtime MUST preserve unknown fields when rewriting control-plane files.
- v1 readers MUST support all v1 minor versions that do not introduce
  unknown required features.

---

## 8. Object Storage

Knowledge Objects MUST be stored as JSON Lines compressed with Zstandard
unless a future required feature declares a different object encoding.

Baseline object stream:

```text
objects/objects.jsonl.zst
```

Large packs SHOULD also provide object block shards:

```text
objects/object-blocks/shard-00000.ogkb
objects/object-blocks/shard-00001.ogkb
```

Rules:

- Object records MUST be independently addressable by `object_id`.
- Object stores MUST support loading a single object without scanning the
  full object stream.
- The JSONL stream is the canonical exchange format.
- Binary block shards MAY be the preferred runtime format.
- Object IDs MUST remain stable across patch versions unless the object is
  intentionally superseded.

---

## 9. Indexes

Indexes are data-plane files optimized for selective retrieval. No single
query should require loading all index families.

### Metadata index

The metadata index MUST support filtering by:

- object type
- source
- source revision
- locale
- domain taxonomy
- confidence range
- license class
- safety/hazard class
- revision status

### Keyword index

The keyword index MUST support exact and normalized lexical retrieval.

Requirements:

- Token normalization rules MUST be declared in `metadata/build-info.yaml`.
- Postings MUST reference object IDs or chunk IDs, not file offsets alone.
- The index SHOULD support memory-mapped or paged access.

### Entity index

The entity index MUST support:

- canonical entity lookup
- alias lookup
- type filtering
- disambiguation candidates
- cross references to Knowledge Objects

### Relationship graph

The relationship graph MUST support bounded traversal from known objects or
entities. It MUST NOT require loading the full graph into memory on Pi 5.

### Semantic index

Semantic vector indexes are optional but strongly recommended for high-value
packs. If present, `indexes/semantic/manifest.yaml` MUST declare:

- embedding model name
- embedding model version or digest
- vector dimensions
- quantization format
- distance metric
- shard size
- object or chunk mapping
- build date
- compatibility constraints

### Media indexes

Image and diagram indexes MUST store metadata separately from large media
payloads. Retrieval MUST be able to return captions, labels, bounding boxes,
and source locators before loading full-resolution images.

---

## 10. Compression

Compression MUST preserve knowledge fidelity. Compression is for storage and
retrieval efficiency, not content deletion.

Allowed v1 compression profiles:

- `zstd-jsonl`: Zstandard-compressed JSON Lines for exchange records.
- `zstd-blocked`: independently compressed blocks for random access.
- `quantized-vectors`: quantized vector index representation with declared
  precision and recall validation.
- `thumbnail-media`: derived media previews linked to original media records.

Rules:

- Source text MUST NOT be summarized destructively as a substitute for
  storing retrievable source-aligned chunks.
- OCR text MAY be cleaned, but original OCR output SHOULD be retained when
  licensing permits.
- Vector quantization MUST include validation metrics.
- Compression profiles MUST be declared in `metadata/build-info.yaml`.
- A runtime MUST be able to skip unsupported optional compressed indexes.

---

## 11. Source Documents

Packs MAY include full source documents when licensing permits, but they are
not required to. Packs MUST always include enough source metadata and locators
to attribute answers.

`metadata/source-catalog.yaml` MUST include:

- source ID
- title
- author or issuing organization
- publication date if known
- revision or edition
- license
- trust tier
- source type
- language
- locator scheme
- checksum when the source file is included

If a source cannot be redistributed, the pack MUST still include:

- a bibliographic record
- locators for cited claims
- license constraints
- provenance notes
- build-time access record

---

## 12. Versioning

Expert Packs use three version axes:

1. `schema_version`: format compatibility.
2. `pack_version`: distributor-facing semantic version.
3. `content_revision`: source corpus build identity.

Version rules:

- Patch versions MUST NOT remove Knowledge Objects without marking them
  superseded or withdrawn.
- Minor versions MAY add object types, optional indexes, sources, and fields
  that v1 readers can ignore.
- Major versions MAY introduce breaking layout or schema changes.
- Object-level revision history MUST identify superseded objects.
- Delta updates MUST declare their required base pack version and checksum.

---

## 13. Integrity and Signing

`checksums.sha256` MUST cover every file in the pack except signatures that
are computed after checksums.

Rules:

- Checksums MUST use normalized relative paths.
- Pack validators MUST detect missing files, unexpected required files, and
  checksum mismatches.
- Signatures are optional in local development v1 packs.
- Marketplace-distributed packs SHOULD require signatures in v1 and MUST
  require them before general public distribution.
- Signature verification MUST be possible offline against locally trusted
  publisher keys.

---

## 14. Installation

Installing a pack means making it discoverable to the runtime. It MUST NOT
mean copying it to a fixed storage location.

Runtime discovery flow:

1. Enumerate mounted Knowledge Volumes.
2. Locate candidate pack roots or archives.
3. Read `manifest.yaml`.
4. Check compatibility.
5. Verify checksums and signatures according to local policy.
6. Register pack identity and index paths in the local pack registry.

Rules:

- Multiple versions of the same pack MAY be installed side by side.
- A user MAY pin a pack version.
- A pack MAY live on removable media.
- Runtime registry entries MUST tolerate missing removable volumes.
- Pack installation MUST be reversible without deleting user memory.

---

## 15. Raspberry Pi 5 Runtime Profile

The Pi 5 runtime MUST assume RAM is scarce and storage is expandable.

Requirements:

- The runtime MUST load manifests before large indexes.
- The runtime MUST page or memory-map large indexes where possible.
- The runtime MUST cap per-pack cache usage.
- The runtime MUST not keep all semantic indexes resident.
- The runtime SHOULD prioritize SSD, NVMe, or network volumes for large
  multi-terabyte packs.
- The runtime MUST handle slow or missing removable volumes gracefully.

Suggested default memory budget:

```yaml
pi5_cache_budget:
  manifest_registry_mb: 16
  metadata_facets_mb: 64
  keyword_hot_pages_mb: 128
  entity_hot_pages_mb: 96
  graph_frontier_mb: 64
  semantic_search_scratch_mb: 128
  evidence_pack_mb: 64
  reserved_for_llm_and_os_mb: 6144
```

---

## 16. Validation Requirements

A valid v1 pack MUST pass:

- manifest schema validation
- compatibility validation
- required file presence validation
- checksum validation
- source catalog validation
- object schema validation
- relationship endpoint validation
- citation locator validation
- license declaration validation
- index-object consistency validation
- retrieval smoke tests

`validation/report.yaml` MUST include:

```yaml
validation:
  status: "passed"
  validator_version: "1.0.0"
  validated_at: "2026-07-06T17:00:00Z"
  object_schema_errors: 0
  dangling_relationships: 0
  missing_citations: 0
  index_consistency_errors: 0
  retrieval_tests_passed: 128
  retrieval_tests_failed: 0
```

---

## 17. Future Compatibility Rules

The v1.0 format is designed to last by separating stable contracts from
implementation choices.

Stable in v1:

- pack identity model
- manifest capability declaration
- Knowledge Object identity
- source locator requirement
- object-to-source attribution
- compatibility feature negotiation
- required validation report

Allowed to evolve:

- binary index encodings
- vector quantization methods
- graph storage engines
- media processing pipelines
- marketplace trust policies
- device-specific cache profiles

Breaking changes MUST introduce a new major schema version. New minor
features MUST be capability-declared and ignorable by older runtimes unless
listed under `required_features`.
