# OGM Knowledge Object Specification v1.0

**Status:** draft v1.0 specification  
**Audience:** engineers building object extraction, pack validation, retrieval, and answer attribution systems  
**Primary runtime target:** offline retrieval on Raspberry Pi 5 with large external Knowledge Volumes  

---

## 1. Purpose

Offgrid Minds systems do not reason directly over files. They reason over
Knowledge Objects: normalized, versioned, source-attributed units of
knowledge that can be retrieved independently and assembled into an evidence
pack for the LLM.

Knowledge Objects are the durable semantic layer between raw information and
runtime reasoning.

### Non-goals

- This specification does not define every domain-specific object subtype.
- This specification does not require a single physical storage backend.
- This specification does not make generated summaries authoritative.
- This specification does not replace source citations.

---

## 2. Design Principles

Every Knowledge Object MUST be:

- **Identifiable:** stable ID, type, pack origin, and revision.
- **Attributable:** traceable to one or more source locators.
- **Retrievable:** indexed by metadata, keywords, entities, relationships,
  and optionally vectors.
- **Composable:** usable with related objects, warnings, media, tables, and
  procedures.
- **Versioned:** able to be superseded, corrected, deprecated, or withdrawn.
- **Confidence-scored:** explicit about evidence quality and extraction
  certainty.
- **Portable:** encoded in a machine-readable form that does not assume a
  specific database engine.

---

## 3. Object Identity

Every object MUST have a stable ID.

Recommended ID form:

```text
ko:<pack_id>:<object_type>:<stable_key>
```

Example:

```text
ko:ogm.pack.small-engine-repair:procedure:clean-carburetor-main-jet
```

Rules:

- IDs MUST be unique within the pack.
- IDs SHOULD be deterministic when generated from stable source structure.
- IDs MUST NOT include storage paths.
- IDs MUST remain stable across patch versions unless the object is
  intentionally replaced.
- If an object is replaced, the replacement MUST reference the prior object
  through `supersedes`.

---

## 4. Base Object Schema

All Knowledge Objects MUST conform to the base schema.

```json
{
  "object_id": "ko:ogm.pack.small-engine-repair:procedure:clean-carburetor-main-jet",
  "schema_version": "1.0",
  "pack_id": "ogm.pack.small-engine-repair",
  "object_type": "procedure",
  "title": "Clean a carburetor main jet",
  "summary": "Procedure for removing debris from a small-engine carburetor main jet.",
  "body": {
    "format": "ogm.richtext.v1",
    "value": "..."
  },
  "entities": [
    "ent:small-engine:assembly:carburetor",
    "ent:small-engine:part:main-jet"
  ],
  "relationships": [
    {
      "type": "requires_tool",
      "target_id": "ko:ogm.pack.small-engine-repair:tool:flathead-screwdriver",
      "confidence": 0.98
    }
  ],
  "sources": [
    {
      "source_id": "src:briggs-service-manual-1234",
      "locator": {
        "type": "page",
        "page": 42,
        "section": "Fuel System"
      },
      "claim_scope": "procedure",
      "confidence": 0.96
    }
  ],
  "media": [
    {
      "media_id": "media:carb-main-jet-diagram-001",
      "role": "diagram",
      "locator": "media/diagrams/shard-00000/main-jet.svg"
    }
  ],
  "warnings": [
    "ko:ogm.pack.small-engine-repair:warning:fuel-vapor-fire-risk"
  ],
  "metadata": {
    "domain": ["repair", "small_engine", "fuel_system"],
    "locale": "en-US",
    "difficulty": "intermediate",
    "estimated_time_minutes": 20
  },
  "confidence": {
    "overall": 0.94,
    "source_quality": 0.98,
    "extraction_quality": 0.91,
    "validation_quality": 0.93
  },
  "version": {
    "object_revision": "2026-07-06.r1",
    "status": "active",
    "created_at": "2026-07-06T17:00:00Z",
    "updated_at": "2026-07-06T17:00:00Z",
    "supersedes": [],
    "superseded_by": []
  }
}
```

### Required fields

- `object_id`
- `schema_version`
- `pack_id`
- `object_type`
- `title`
- `summary`
- `sources`
- `metadata`
- `confidence`
- `version`

### Optional fields

- `body`
- `entities`
- `relationships`
- `media`
- `warnings`
- `references`
- `measurements`
- `locale_variants`
- `domain_payload`

If the object has no source attribution, it MUST be marked as invalid for
answer grounding unless it is an internal system object such as a taxonomy
node.

---

## 5. Object Types

v1 defines core object types. Packs MAY add domain-specific subtypes if they
declare them in `metadata/taxonomy.yaml`.

### Core object types

| Type | Purpose |
|---|---|
| `procedure` | Ordered steps for accomplishing a task. |
| `step` | Atomic action inside a procedure. |
| `warning` | Safety, legal, damage, or reliability warning. |
| `part` | Replaceable component or physical part. |
| `tool` | Tool, instrument, fixture, or consumable. |
| `material` | Material, chemical, fluid, ingredient, or supply. |
| `specification` | Measurement, tolerance, rating, capacity, torque, or limit. |
| `diagram` | Labeled visual explanation or schematic. |
| `image` | Photograph or raster image with source metadata. |
| `table` | Structured tabular reference data. |
| `manual_reference` | Pointer to a manual section or source passage. |
| `troubleshooting_case` | Symptom, possible causes, tests, and remedies. |
| `entity_profile` | Canonical descriptive record for an entity. |
| `definition` | Term, concept, or glossary definition. |
| `relationship_assertion` | Explicit claim connecting two objects or entities. |
| `compatibility_record` | Compatibility between parts, models, versions, or products. |

### Domain object examples

Packs MAY define domain object types such as:

- `species`
- `coin`
- `comic`
- `vehicle`
- `chemical`
- `circuit`
- `connector`
- `engine`
- `appliance`
- `medical_condition`
- `plant_disease`
- `legal_form`

Domain object types MUST inherit the base object schema.

---

## 6. Object Type Requirements

### Procedure

A `procedure` MUST include:

- ordered steps or references to `step` objects
- required tools or materials when known
- warnings before hazardous steps
- applicability constraints
- expected outcome
- source attribution for the procedure and critical steps

Example:

```json
{
  "object_type": "procedure",
  "title": "Replace a mower spark plug",
  "domain_payload": {
    "applicability": ["small gasoline engines"],
    "estimated_time_minutes": 10,
    "preconditions": ["engine off", "engine cool"],
    "steps": [
      {
        "order": 1,
        "instruction": "Disconnect the spark plug wire.",
        "warnings": ["ko:...:warning:accidental-start"]
      },
      {
        "order": 2,
        "instruction": "Remove the plug with the correct socket."
      }
    ],
    "success_criteria": ["new plug is seated", "engine starts normally"]
  }
}
```

### Warning

A `warning` MUST include:

- hazard class
- severity
- conditions where it applies
- safest immediate action
- source locator

Severity levels:

- `info`
- `caution`
- `warning`
- `danger`
- `critical`

### Specification

A `specification` MUST include:

- measured property
- value
- unit
- tolerance or range when available
- applicability
- source locator

Example:

```json
{
  "object_type": "specification",
  "title": "Spark plug gap",
  "domain_payload": {
    "property": "spark_plug_gap",
    "value": 0.030,
    "unit": "inch",
    "tolerance": "+/- 0.002",
    "applies_to": ["ent:small-engine:model:example-engine-abc"]
  }
}
```

### Diagram

A `diagram` MUST include:

- media reference
- caption
- labels if available
- source locator
- related entities or parts

Diagram labels SHOULD be extracted into structured regions when possible.

### Troubleshooting Case

A `troubleshooting_case` SHOULD include:

- symptom
- likely causes
- tests
- remedies
- required tools
- warnings
- confidence per cause

---

## 7. Body Formats

The `body` field MAY use one of the following v1 formats:

- `ogm.richtext.v1`
- `text/plain`
- `text/markdown`
- `application/json`
- `application/ogm-procedure+json`
- `application/ogm-table+json`

Rules:

- `summary` MUST remain short and suitable for ranking display.
- `body` MAY be absent when the object is purely structured.
- Long passages SHOULD be chunked into source-aligned records rather than
  stored as one oversized body.
- Body text MUST NOT replace source attribution.

---

## 8. Relationships

Relationships connect Knowledge Objects and entities. Relationship edges MUST
be typed and SHOULD be directional.

Common relationship types:

- `is_a`
- `part_of`
- `has_part`
- `requires_tool`
- `requires_material`
- `has_warning`
- `has_specification`
- `has_diagram`
- `has_image`
- `references_source`
- `supersedes`
- `compatible_with`
- `incompatible_with`
- `causes`
- `symptom_of`
- `fixes`
- `tests_for`
- `located_in`
- `same_as`
- `related_to`

Relationship record:

```json
{
  "type": "requires_tool",
  "target_id": "ko:ogm.pack.small-engine-repair:tool:spark-plug-socket",
  "direction": "outbound",
  "confidence": 0.97,
  "source_id": "src:manual-001",
  "locator": {
    "type": "page",
    "page": 17
  }
}
```

Rules:

- Relationship endpoints MUST resolve to an object ID, entity ID, or declared
  external reference.
- Safety relationships MUST NOT be inferred silently; generated warnings
  must be marked as inferred and separately validated.
- Cross-pack relationships MUST include the target pack ID and a fallback
  label in case the target pack is not installed.

---

## 9. Source Attribution

Every answerable object MUST include source attribution.

Source attribution MUST identify:

- source ID
- locator type
- locator value
- claim scope
- extraction method
- confidence

Locator examples:

```json
{ "type": "page", "page": 42, "section": "Fuel System" }
{ "type": "figure", "figure": "3-12", "page": 91 }
{ "type": "bounding_box", "page": 12, "x": 0.12, "y": 0.30, "w": 0.41, "h": 0.18 }
{ "type": "timestamp", "start_s": 90.2, "end_s": 108.4 }
{ "type": "uri", "uri": "urn:isbn:9780000000000:chapter:4" }
```

Rules:

- A source locator MUST be stable across rebuilds when the source is stable.
- Multiple sources MAY support one object.
- Conflicting sources MUST be represented through confidence, notes, and
  relationship assertions rather than hidden during build.
- Generated summaries MUST point back to the source passages they summarize.

---

## 10. Confidence

Confidence is not a substitute for citation. It helps ranking and answer
calibration.

Required confidence dimensions:

- `overall`
- `source_quality`
- `extraction_quality`
- `validation_quality`

Optional dimensions:

- `ocr_quality`
- `media_quality`
- `entity_linking_quality`
- `semantic_chunk_quality`
- `expert_review_quality`

Scale:

- `0.0` means unusable or untrusted.
- `0.5` means uncertain but potentially useful.
- `1.0` means highly reliable within the limits of the source.

Rules:

- Confidence values MUST be numeric between `0.0` and `1.0`.
- Validators MUST reject values outside the range.
- Objects below pack-defined minimum confidence MAY remain in the pack but
  MUST be excluded from answer grounding unless the runtime explicitly asks
  for low-confidence candidates.

---

## 11. Version Status

Object status values:

- `active`
- `draft`
- `deprecated`
- `superseded`
- `withdrawn`
- `conflicted`

Rules:

- `draft` objects MUST NOT be used for normal answer grounding.
- `deprecated` objects MAY be used only when no better active object exists
  and the answer explains the limitation.
- `superseded` objects MUST point to replacements when known.
- `withdrawn` objects MUST remain visible for audit but MUST NOT be used in
  answers.
- `conflicted` objects MAY be used only with explicit uncertainty.

---

## 12. Localization

Objects MAY include localized fields.

```json
{
  "locale_variants": {
    "es-MX": {
      "title": "Cambiar una bujia de cortadora",
      "summary": "Procedimiento para reemplazar una bujia..."
    }
  }
}
```

Rules:

- The canonical object ID MUST remain locale-independent.
- Localized text MUST preserve the same source attribution.
- Locale variants MUST declare translation method: human, machine, or
  machine-reviewed.
- Safety warnings SHOULD require human review before marketplace publication.

---

## 13. Media References

Objects reference media by ID and locator, not by embedding raw bytes inside
the object record.

Media reference:

```json
{
  "media_id": "media:brake-pad-wear-photo-001",
  "role": "image",
  "locator": "media/images/shard-00002/photo-001.webp",
  "thumbnail": "media/thumbnails/photo-001.webp",
  "source_id": "src:field-guide-001",
  "caption": "Worn brake pad below recommended thickness.",
  "regions": [
    {
      "label": "wear indicator",
      "x": 0.32,
      "y": 0.44,
      "w": 0.14,
      "h": 0.08
    }
  ]
}
```

Rules:

- Media references MUST include source attribution.
- Full-resolution media SHOULD be loaded only after text, caption, and
  locator retrieval indicate relevance.
- Derived thumbnails MUST link to their source media record.

---

## 14. Validation Requirements

Object validators MUST check:

- required fields
- ID uniqueness
- valid object type
- source locator presence
- confidence range
- version status
- relationship endpoint existence
- warning severity validity
- unit normalization for specifications
- media reference existence
- cross-pack reference syntax

Recommended validation levels:

- **Level 0:** structural schema only.
- **Level 1:** schema plus internal references.
- **Level 2:** source locator and index consistency.
- **Level 3:** expert review or high-confidence automated validation.

Only Level 2 or higher objects SHOULD be used for normal answer grounding.

---

## 15. Retrieval Contract

A Knowledge Object is retrievable evidence only if:

- it is compatible with the active runtime
- its status is answerable
- it has source attribution
- its confidence meets the query policy
- its license permits local use
- its metadata matches the query scope

The retrieval engine MAY return non-answerable objects as context for audit,
debugging, or explanation, but the LLM MUST be told that they are not
grounding evidence.

---

## 16. Forward Compatibility

Object schemas MUST support unknown fields. Builders and validators MUST NOT
discard unknown fields unless explicitly configured to produce a normalized
minimal export.

Future object types SHOULD:

- inherit the base object schema
- define a `domain_payload`
- avoid changing base field meaning
- declare required relationship and source rules
- include examples and validation tests

The base object model is intended to remain stable across v1 minor releases.
