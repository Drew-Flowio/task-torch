# OGM Entity Specification v1.0

**Status:** draft v1.0 specification  
**Audience:** engineers building entity extraction, normalization, indexes, graph relationships, and cross-pack references  
**Primary runtime target:** offline entity lookup and disambiguation on Raspberry Pi 5  

---

## 1. Purpose

Entities are canonical references to real or conceptual things: parts,
tools, species, vehicles, chemicals, authors, manuals, symptoms, circuits,
models, places, products, and named concepts.

Entities let the retrieval engine understand that "carb jet," "main jet,"
and "carburetor nozzle" may refer to the same component in a specific
domain, while "jet" alone may be ambiguous.

---

## 2. Entity Principles

- Entities MUST be stable identifiers, not display strings.
- Aliases MUST preserve context and locale.
- Entity normalization MUST be explainable.
- Entity relationships MUST be typed.
- Cross-pack references MUST tolerate missing packs.
- Ambiguity MUST be represented, not hidden.

---

## 3. Entity ID

Recommended ID form:

```text
ent:<namespace>:<type>:<stable-key>
```

Examples:

```text
ent:small-engine:part:main-jet
ent:automotive:vehicle:2016-honda-civic-1-5t
ent:botany:species:acer-rubrum
ent:electronics:connector:usb-c
```

Rules:

- Entity IDs MUST be ASCII.
- Entity IDs MUST NOT contain storage paths.
- Entity IDs MUST remain stable across patch versions.
- Entity IDs SHOULD be deterministic for well-known canonical entities.
- Pack-local entities MAY later be mapped to global entities.

---

## 4. Entity Record Schema

```json
{
  "entity_id": "ent:small-engine:part:main-jet",
  "schema_version": "1.0",
  "pack_id": "ogm.pack.small-engine-repair",
  "entity_type": "part",
  "canonical_name": "main jet",
  "summary": "Metering orifice in a carburetor that controls fuel flow at higher throttle.",
  "aliases": [
    {
      "value": "carb jet",
      "locale": "en-US",
      "kind": "common",
      "confidence": 0.86
    },
    {
      "value": "main nozzle",
      "locale": "en-US",
      "kind": "manual_term",
      "source_id": "src:manual-001",
      "confidence": 0.91
    }
  ],
  "normalization": {
    "canonical_form": "main jet",
    "case_fold": true,
    "unit_normalized": false,
    "part_number_normalized": false
  },
  "relationships": [
    {
      "type": "part_of",
      "target_id": "ent:small-engine:assembly:carburetor",
      "confidence": 0.98
    }
  ],
  "object_refs": [
    {
      "object_id": "ko:ogm.pack.small-engine-repair:procedure:clean-carburetor-main-jet",
      "role": "primary_subject"
    }
  ],
  "source_refs": [
    {
      "source_id": "src:manual-001",
      "locator": {
        "type": "page",
        "page": 42
      },
      "confidence": 0.95
    }
  ],
  "external_refs": [
    {
      "system": "manufacturer_part_catalog",
      "value": "ABC-123",
      "confidence": 0.90
    }
  ],
  "confidence": {
    "overall": 0.94,
    "extraction_quality": 0.91,
    "alias_quality": 0.88,
    "linking_quality": 0.96
  },
  "status": "active"
}
```

Required fields:

- `entity_id`
- `schema_version`
- `pack_id`
- `entity_type`
- `canonical_name`
- `aliases`
- `confidence`
- `status`

---

## 5. Entity Types

Core entity types:

- `part`
- `tool`
- `material`
- `chemical`
- `procedure`
- `symptom`
- `hazard`
- `measurement`
- `specification`
- `model`
- `product`
- `vehicle`
- `appliance`
- `species`
- `person`
- `organization`
- `place`
- `document`
- `standard`
- `concept`
- `circuit`
- `connector`
- `software`
- `legal_jurisdiction`

Packs MAY add domain-specific entity types if declared in
`metadata/taxonomy.yaml`.

Rules:

- Entity type affects ranking, disambiguation, and graph traversal.
- Domain-specific types SHOULD declare a core parent type.
- Entity type names MUST be lowercase snake_case.

---

## 6. Aliases

Aliases are first-class records, not loose synonym lists.

Alias schema:

```json
{
  "value": "carb jet",
  "normalized_value": "carb jet",
  "locale": "en-US",
  "kind": "common",
  "source_id": "src:manual-001",
  "confidence": 0.86,
  "scope": {
    "domain": ["repair", "small_engine"],
    "applies_to": ["ent:small-engine:assembly:carburetor"]
  }
}
```

Alias kinds:

- `canonical`
- `common`
- `abbreviation`
- `part_number`
- `model_number`
- `manual_term`
- `brand_term`
- `scientific_name`
- `localized`
- `misspelling`
- `legacy`

Rules:

- Aliases MUST include locale when language matters.
- Part numbers and model numbers MUST preserve original formatting and a
  normalized form.
- Misspellings MAY be included if they improve retrieval, but MUST be marked
  as misspellings.
- Aliases SHOULD include scope to avoid false matches across domains.

---

## 7. Normalization

Normalization converts observed strings into comparable forms.

Supported v1 normalization:

- Unicode normalization to NFC before ASCII-safe indexing where possible.
- Case folding.
- Whitespace normalization.
- Punctuation normalization for part and model numbers.
- Unit normalization.
- Singular/plural normalization where locale supports it.
- Abbreviation expansion.

Rules:

- Normalization MUST preserve the original observed value.
- Normalization MUST be deterministic.
- Normalization rules MUST be declared in `metadata/build-info.yaml`.
- Domain-specific normalization SHOULD be isolated and versioned.

Example:

```json
{
  "observed": "RJ-19LM",
  "normalized": "rj19lm",
  "kind": "part_number",
  "normalizer": "ogm-part-number-normalizer-v1"
}
```

---

## 8. Disambiguation

The entity system MUST represent ambiguity explicitly.

Disambiguation candidate:

```json
{
  "observed": "jet",
  "candidates": [
    {
      "entity_id": "ent:small-engine:part:main-jet",
      "label": "main jet",
      "domain": ["small_engine"],
      "score": 0.82
    },
    {
      "entity_id": "ent:aviation:vehicle:jet-aircraft",
      "label": "jet aircraft",
      "domain": ["aviation"],
      "score": 0.31
    }
  ],
  "resolution": "resolved_by_context",
  "context": ["mower", "carburetor"]
}
```

Rules:

- If disambiguation confidence is low and the decision affects safety or
  procedure selection, the runtime MUST ask a clarifying question.
- Disambiguation SHOULD use session context, active packs, taxonomy, and
  neighboring terms.
- The chosen candidate and reason SHOULD be logged in retrieval diagnostics.

---

## 9. Entity Relationships

Entity relationship types:

- `is_a`
- `same_as`
- `part_of`
- `has_part`
- `used_with`
- `compatible_with`
- `incompatible_with`
- `causes`
- `symptom_of`
- `located_in`
- `made_by`
- `model_of`
- `variant_of`
- `replaces`
- `requires`
- `hazard_for`
- `regulated_by`

Relationship record:

```json
{
  "type": "compatible_with",
  "target_id": "ent:small-engine:model:example-engine-1234",
  "confidence": 0.92,
  "source_id": "src:parts-catalog-001",
  "locator": {
    "type": "row",
    "table": "spark_plugs",
    "row_id": "17"
  },
  "status": "active"
}
```

Rules:

- Relationships MUST be typed.
- Relationships SHOULD include source attribution.
- Compatibility and incompatibility claims MUST include source attribution.
- `same_as` relationships require high confidence or expert validation.
- Inferred relationships MUST be marked as inferred.

---

## 10. Cross-Pack References

Entities may reference entities in other packs.

```json
{
  "type": "same_as",
  "target": {
    "pack_id": "ogm.pack.global-parts-registry",
    "entity_id": "ent:global:part:main-jet"
  },
  "fallback_label": "main jet",
  "confidence": 0.89
}
```

Rules:

- Cross-pack references MUST include both target pack ID and target entity ID.
- Runtime MUST tolerate missing target packs.
- Cross-pack references MUST NOT be required for local pack function.
- Cross-pack reference conflicts MUST be exposed during validation.

---

## 11. Entity-to-Object References

Entity records SHOULD list relevant object references by role.

Roles:

- `primary_subject`
- `mentioned`
- `required_tool`
- `required_material`
- `warning_subject`
- `specification_subject`
- `diagram_label`
- `compatible_item`
- `symptom`
- `cause`
- `remedy`

Rules:

- Entity-to-object refs improve retrieval but MUST be derivable from object
  relationships or index data.
- Validators SHOULD check that object references resolve.
- Object references SHOULD include role for ranking.

---

## 12. Entity Index Requirements

The entity index MUST support:

- canonical name lookup
- alias lookup
- prefix lookup for part/model numbers
- exact part/model number lookup
- locale filtering
- domain filtering
- entity type filtering
- object reference retrieval
- relationship neighborhood retrieval

Pi 5 requirements:

- Entity aliases SHOULD be stored in a compact finite-state or similarly
  memory-efficient lookup structure.
- The hot entity cache SHOULD fit within the retrieval memory budget.
- Full entity records SHOULD be loaded lazily after candidate lookup.

---

## 13. Conflict Handling

Entity conflicts occur when:

- two entities claim the same canonical identity
- aliases collide across domains
- compatibility claims disagree
- a part number maps to multiple products
- sources disagree about relationships

Conflict record:

```json
{
  "conflict_id": "conflict:entity:001",
  "kind": "alias_collision",
  "entities": [
    "ent:small-engine:part:main-jet",
    "ent:aviation:vehicle:jet-aircraft"
  ],
  "observed_value": "jet",
  "resolution": "domain_context_required",
  "severity": "medium"
}
```

Rules:

- Conflicts MUST NOT be silently resolved if safety, compatibility, or
  procedural correctness depends on them.
- Low-severity alias collisions MAY be resolved by context.
- High-severity conflicts SHOULD block marketplace publication until
  reviewed.

---

## 14. Validation Requirements

Entity validators MUST check:

- ID uniqueness
- required fields
- valid entity type
- alias structure
- normalized alias uniqueness within declared scope
- relationship endpoint existence
- confidence range
- source references
- cross-pack reference syntax
- conflict records

Validation levels:

- **E0:** parse and required fields.
- **E1:** alias normalization and local references.
- **E2:** source-backed relationships and object refs.
- **E3:** conflict analysis.
- **E4:** expert-reviewed high-risk or marketplace entities.

---

## 15. Runtime Behavior

At runtime, entity lookup SHOULD run before semantic search. Entity matches
seed retrieval by:

- selecting candidate packs
- filtering object types
- boosting exact matches
- expanding graph neighborhoods
- disambiguating procedures
- promoting relevant warnings

The runtime MUST preserve ambiguity information through evidence assembly
when the ambiguity remains unresolved.

---

## 16. Forward Compatibility

The entity model is intended to survive new domains. Future versions MAY add:

- global entity registries
- cryptographic entity attestations
- domain-specific normalizers
- learned disambiguation models
- richer ontology mapping

These additions MUST preserve the v1 guarantees: stable IDs, explicit
aliases, typed relationships, source attribution, and offline lookup.
