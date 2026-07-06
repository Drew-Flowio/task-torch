# OGM Metadata Standard v1.0

**Status:** draft v1.0 specification  
**Audience:** pack authors, build pipeline engineers, validators, runtime engineers, and marketplace reviewers  
**Primary runtime target:** offline pack discovery and retrieval on Raspberry Pi 5  

---

## 1. Purpose

Metadata is the control plane for Offgrid Minds knowledge. It lets the
runtime discover packs, select the right knowledge, enforce licenses,
preserve attribution, filter by domain, localize content, and explain where
answers came from.

Metadata MUST be human-readable enough for audit and machine-readable enough
for deterministic validation.

---

## 2. Metadata Principles

- Metadata MUST be explicit, not inferred at runtime from filenames.
- Metadata MUST preserve source attribution and licensing.
- Metadata MUST support offline verification.
- Metadata MUST use stable identifiers.
- Metadata MUST be sufficient for retrieval filtering without opening large
  object bodies.
- Metadata SHOULD be conservative when source quality or licensing is unclear.

---

## 3. Naming Conventions

### IDs

ID prefixes:

| Prefix | Meaning |
|---|---|
| `ogm.pack.` | Expert Pack ID |
| `ogm.publisher.` | Publisher ID |
| `ko:` | Knowledge Object ID |
| `ent:` | Entity ID |
| `src:` | Source ID |
| `media:` | Media ID |
| `vol:` | Knowledge Volume ID |
| `cit:` | Runtime citation ID |
| `ev:` | Runtime evidence ID |

Rules:

- IDs MUST be stable.
- IDs MUST be ASCII.
- IDs MUST NOT contain spaces.
- IDs SHOULD use lowercase kebab-case after the prefix.
- IDs MUST NOT include local storage paths.

### Titles

Titles SHOULD be human-readable and locale-aware. Titles are display labels,
not identity.

### Filenames

Filenames MUST be ASCII and SHOULD use lowercase kebab-case. Required
control-plane files MUST use the filenames defined by the Expert Pack
Specification.

---

## 4. Pack Metadata

`manifest.yaml` MUST include:

```yaml
pack:
  id: "ogm.pack.small-engine-repair"
  version: "1.0.0"
  content_revision: "2026-07-06.r1"
  title: "Small Engine Repair"
  summary: "Repair and maintenance procedures for small gasoline engines."
  publisher_id: "ogm.publisher.example"
  primary_locale: "en-US"
  created_at: "2026-07-06T17:00:00Z"
  updated_at: "2026-07-06T17:00:00Z"
  domains: ["repair", "small_engine"]
  audience: ["consumer", "technician"]
  trust_tier: "reviewed"
```

Rules:

- `summary` MUST describe scope, not marketing claims.
- `domains` MUST align with `metadata/taxonomy.yaml`.
- `trust_tier` MUST reflect validation status, not author reputation alone.
- Publisher identity MUST be separate from pack identity.

---

## 5. Taxonomy

Taxonomy provides stable retrieval facets.

`metadata/taxonomy.yaml` example:

```yaml
taxonomy_version: "1.0"
domains:
  - id: "repair"
    label: "Repair"
    parent: null
  - id: "small_engine"
    label: "Small Engine"
    parent: "repair"
  - id: "fuel_system"
    label: "Fuel System"
    parent: "small_engine"

object_types:
  - id: "procedure"
    label: "Procedure"
    base_type: "procedure"
  - id: "spark_plug"
    label: "Spark Plug"
    base_type: "part"

safety_classes:
  - id: "fire"
    label: "Fire"
  - id: "electrical"
    label: "Electrical"
```

Rules:

- Taxonomy IDs MUST be stable within a major pack version.
- Parent references MUST resolve.
- Taxonomy labels MAY be localized.
- Runtime filters MUST use taxonomy IDs, not display labels.
- Domain-specific object types MUST declare a base type.

---

## 6. Source Catalog Metadata

Every source used to build a pack MUST be listed in
`metadata/source-catalog.yaml`.

Required fields:

```yaml
sources:
  - source_id: "src:briggs-service-manual-1234"
    title: "Service Manual for Model 1234 Engines"
    source_type: "manual"
    issuing_organization: "Example Manufacturer"
    authors: []
    publication_date: "2019-03-01"
    revision: "2019 edition"
    language: "en-US"
    locator_scheme: ["page", "section", "figure"]
    license_id: "lic:source-001"
    redistribution_allowed: false
    source_quality: 0.98
    trust_tier: "authoritative"
    included_in_pack: false
    checksum: null
```

Source types:

- `manual`
- `book`
- `paper`
- `field_guide`
- `catalog`
- `image_set`
- `video`
- `web_archive`
- `expert_note`
- `dataset`
- `standard`
- `regulation`
- `user_provided`

Trust tiers:

- `authoritative`
- `reviewed`
- `community`
- `user_provided`
- `machine_extracted`
- `unknown`

Rules:

- `unknown` trust sources MUST NOT be used for high-risk procedural answers
  without corroboration.
- Source records MUST remain even when the source file is not redistributable.
- Source records MUST include locator schemes.
- Source quality MUST be numeric between `0.0` and `1.0`.

---

## 7. Licensing Metadata

Licensing is required for offline ownership and marketplace distribution.

`LICENSES/source-licenses.yaml` example:

```yaml
licenses:
  - license_id: "lic:source-001"
    name: "Manufacturer service manual license"
    spdx_id: null
    rights:
      local_use: true
      redistribution: false
      commercial_distribution: false
      derivative_indexing: true
      excerpt_display: "limited"
    attribution_required: true
    attribution_text: "Example Manufacturer, Service Manual, 2019 edition."
    restrictions:
      - "Full manual PDF may not be redistributed."
```

Rules:

- Every source MUST reference a license record.
- Runtime answer generation MUST obey excerpt and display restrictions.
- Pack validators MUST fail packs with missing license references.
- Marketplace packs MUST disclose license constraints before install.
- User-owned private packs MAY include sources the user is allowed to store
  locally, but distribution rights remain separate.

---

## 8. Versioning Metadata

Pack version fields:

- `schema_version`: pack format.
- `pack.version`: user-visible semantic version.
- `pack.content_revision`: build-specific corpus revision.
- `taxonomy_version`: taxonomy contract.
- `build_info.pipeline_version`: build software version.

`metadata/revision-history.yaml` example:

```yaml
revisions:
  - pack_version: "1.0.0"
    content_revision: "2026-07-06.r1"
    date: "2026-07-06"
    changes:
      - "Initial compiled pack."
    source_changes:
      added: 11840
      removed: 0
      updated: 0
    object_changes:
      added: 1842300
      superseded: 0
      withdrawn: 0
```

Rules:

- Revision history MUST be append-only.
- Removed sources MUST remain in history.
- Withdrawn objects MUST be recorded with reason codes.
- Delta updates MUST reference both version and checksum of the base pack.

---

## 9. Localization Metadata

`metadata/locales.yaml` example:

```yaml
locales:
  primary: "en-US"
  available:
    - locale: "en-US"
      coverage: 1.0
      translation_method: "source"
    - locale: "es-MX"
      coverage: 0.62
      translation_method: "machine-reviewed"
      safety_reviewed: true
```

Rules:

- Locale tags MUST use BCP 47.
- Primary locale MUST match the dominant source language or declared authoring
  language.
- Safety-critical translations SHOULD be human-reviewed.
- Retrieval MAY fall back to primary locale, but answers MUST disclose when
  source evidence is not in the user's preferred language if it matters.

---

## 10. Build Metadata

`metadata/build-info.yaml` MUST record how the pack was produced.

Required fields:

```yaml
build:
  build_id: "build:2026-07-06:abc123"
  pipeline_version: "1.0.0"
  built_at: "2026-07-06T17:00:00Z"
  builder: "ogm-pack-builder"
  reproducible: true

processing:
  ocr_engines:
    - name: "example-ocr"
      version: "1.2.3"
  embedding_models:
    - name: "example-embedding-model"
      digest: "sha256:..."
      dimensions: 768
  tokenization:
    keyword_normalizer: "ogm-keyword-normalizer-v1"
    stopword_locale: "en-US"
  compression:
    object_stream: "zstd-jsonl"
    vector_index: "quantized-vectors"
```

Rules:

- Build metadata MUST be sufficient to audit major processing choices.
- Embedding model identity MUST be precise enough to detect incompatible
  semantic indexes.
- OCR and extraction engines SHOULD include versions and configuration
  digests.

---

## 11. Safety Metadata

Safety metadata supports conservative answer behavior.

Safety classes:

- `electrical`
- `fire`
- `gas`
- `chemical`
- `structural`
- `medical`
- `automotive_hv`
- `weapon`
- `legal`
- `financial`
- `environmental`

Hazard metadata example:

```yaml
safety:
  hazard_class: "fire"
  severity: "danger"
  applies_when:
    - "fuel system opened"
    - "engine hot"
  safest_action: "Work outside away from ignition sources and let engine cool."
```

Rules:

- Safety metadata MUST be attached to warnings.
- Safety metadata SHOULD be attached to procedures when any step is hazardous.
- Ranking MUST promote relevant warnings.
- High-risk safety metadata SHOULD require expert review before marketplace
  publication.

---

## 12. Device Compatibility Metadata

Packs MUST declare runtime expectations.

```yaml
device_compatibility:
  min_runtime: "1.0.0"
  recommended_storage_classes: ["usb_ssd", "nvme", "local_nas"]
  pi5:
    supported: true
    semantic_search_profile: "paged"
    max_recommended_parallel_packs: 3
  mobile:
    supported: "future"
  desktop:
    supported: true
```

Rules:

- Device compatibility MUST NOT hard-code storage paths.
- Packs MAY be too large for comfortable use on slow microSD while still
  being valid.
- Runtime warnings SHOULD explain performance limitations without blocking
  user ownership.

---

## 13. Metadata Validation

Validation levels:

- **M0:** file exists and parses.
- **M1:** required fields and field types are valid.
- **M2:** references resolve across metadata files.
- **M3:** metadata matches object, source, license, and index content.
- **M4:** marketplace-grade review and policy validation.

v1 packs MUST pass M3 for normal installation. Marketplace packs SHOULD pass
M4.

Validators MUST fail on:

- missing required metadata
- duplicate IDs
- invalid version strings
- invalid locale tags
- missing license references
- unresolved taxonomy parents
- source records without locator schemes
- capability declarations inconsistent with files

---

## 14. Forward Compatibility

Metadata files MUST tolerate unknown fields. New metadata sections SHOULD be
added under explicit names rather than changing existing field meaning.

Breaking metadata changes require a new major schema version. Non-breaking
changes MAY add optional fields, taxonomy nodes, locales, device profiles, or
validation annotations.
