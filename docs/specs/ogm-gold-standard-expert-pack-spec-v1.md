# OGM Gold Standard Expert Pack Specification v1.0

**Status:** draft Phase 6 specification  
**Audience:** Offgrid Minds founders, Knowledge Foundry operators, CKO supervisors, pack architects, validators, runtime engineers, and human expert reviewers  
**Relationship to Phase 1:** specializes the generic Expert Pack, Knowledge Object, Entity, Metadata, Retrieval, Build Pipeline, and Marketplace specifications into a flagship product standard  
**Relationship to Phase 2:** defines the product the Agent Control Center should track from mission creation through human approval  
**Relationship to Phase 3:** defines what the Knowledge Foundry must manufacture, validate, and prove  
**Relationship to Phase 4:** defines the quality target the CKO must measure through coverage, Knowledge Debt, and provenance  
**Relationship to Phase 5:** defines high-value ACP events and review checkpoints produced while building a flagship pack  
**Flagship target:** North American Outdoor Expert Pack  
**Primary runtime target:** Raspberry Pi 5, 8 GB RAM, offline, removable Knowledge Volumes  

---

## 1. Purpose

The OGM Gold Standard Expert Pack Specification defines what a finished
Offgrid Minds Expert Pack should look like when quality matters more than
quantity.

The flagship example is the **North American Outdoor Expert Pack**: a portable
professional reference system for outdoor field use, designed specifically for
small offline language models.

This pack is not:

- a software package
- a folder of PDFs
- a vector database
- a prompt collection
- an unreviewed scrape of outdoor content

It is a structured, source-attributed, professionally reviewed field reference
library that can be retrieved in small pieces by an offline model.

---

## 2. Product Standard

A Gold Standard Expert Pack MUST feel like the reference library a serious
professional would carry into the field if storage were cheap, RAM were scarce,
and trust were non-negotiable.

It should serve:

- park rangers
- survival instructors
- wildlife biologists
- anglers
- hunters
- wilderness medics
- search and rescue instructors
- botanists
- mycologists
- geologists
- foresters
- experienced outdoorspeople
- responsible beginners under stress

The pack MUST optimize for:

- trust
- usefulness
- organization
- source quality
- reviewability
- emergency clarity
- offline operation
- fast retrieval under memory limits

It MUST NOT optimize for raw object count, novelty, or broad unverified
coverage.

---

## 3. Flagship Pack Identity

Recommended identity:

```yaml
pack:
  id: "ogm.pack.north-american-outdoor"
  title: "North American Outdoor Expert Pack"
  version: "1.0.0"
  schema_version: "1.0"
  content_revision: "2026-07-06.r1"
  publisher_id: "ogm.publisher.offgrid-minds"
  primary_locale: "en-US"
  operating_region: "north-america"
  runtime_profile: "pi5-8gb-offline"
```

The flagship pack MUST include a public-facing quality statement:

> This pack is a source-attributed professional reference system. It is not a
> substitute for emergency services, licensed medical care, lawful training, or
> official local regulations. When uncertainty affects safety, the runtime must
> say so.

---

## 4. Complete Folder and Module Structure

The pack SHOULD use the generic Expert Pack structure from Phase 1, specialized
with a field library layout.

```text
ogm.pack.north-american-outdoor/
  manifest.yaml
  pack_readme.md
  safety_notice.md
  review_summary.md
  coverage_report.yaml
  quality_scorecard.yaml
  licensing_report.yaml
  provenance_ledger.jsonl
  audit/
    human_reviews.jsonl
    source_decisions.jsonl
    validation_runs.jsonl
    build_lineage.jsonl
  control/
    modules.yaml
    object_types.yaml
    route_hints.yaml
    retrieval_profiles.yaml
    emergency_overrides.yaml
  objects/
    modules/
      safety/
      emergency_medicine/
      search_and_rescue/
      navigation/
      weather/
      water/
      fire/
      shelter/
      food/
      plants/
      fungi/
      wildlife/
      fish_and_aquatic/
      hunting_and_trapping/
      geology/
      forestry/
      knots_and_ropework/
      tools_and_equipment/
      equipment_repair/
      regulations/
      regional_field_guides/
  entities/
    species/
    hazards/
    places/
    equipment/
    agencies/
    regulations/
    symptoms/
    procedures/
  relationships/
    graph_edges.jsonl
    contraindications.jsonl
    lookalikes.jsonl
    region_applicability.jsonl
    procedure_dependencies.jsonl
  indexes/
    metadata/
    keyword/
    entity/
    graph/
    vector/
    media/
    map/
    emergency/
    quick_reference/
  media/
    images/
      species/
      equipment/
      terrain/
      medical/
      weather/
    diagrams/
      procedures/
      anatomy/
      knots/
      repairs/
      weather/
      geology/
    maps/
      base/
      overlays/
      regions/
      grids/
    cards/
      quick_reference/
      emergency/
      checklists/
  sources/
    source_catalog.yaml
    source_manifests/
    source_extracts/
    public_domain_originals/
    licensed_originals/
  manuals/
    government/
    university/
    professional/
    technical/
  validation/
    object_validation.jsonl
    source_validation.jsonl
    emergency_validation.jsonl
    regional_validation.jsonl
    retrieval_validation.jsonl
```

Rules:

- Modules MUST be discoverable without loading object bodies.
- Source originals MAY be omitted when licensing requires it, but source
  manifests and approved extracts MUST remain.
- Media MUST be addressed by stable media IDs, not filesystem paths.
- Maps MUST be separated from general images because map retrieval has unique
  spatial and scale constraints.
- Emergency quick references MUST be separately indexed for first retrieval.

---

## 5. Domain Module Structure

The flagship pack MUST be organized into professional field modules.

### 5.1 Safety and Risk

Purpose: global hazard handling and conservative advice.

Includes:

- risk assessment
- stop conditions
- legal and ethical constraints
- weather exposure risk
- animal encounter risk
- firearm and hunting safety boundaries
- water crossing risk
- avalanche and ice risk
- wildfire risk
- toxic exposure
- emergency escalation triggers

### 5.2 Emergency Medicine

Purpose: wilderness first aid reference, not medical replacement.

Includes:

- primary survey
- bleeding control
- fractures and splinting
- burns
- hypothermia
- heat illness
- dehydration
- anaphylaxis
- snakebite
- tick-borne illness awareness
- altitude illness
- drowning and near-drowning
- evacuation decision support
- medical contraindications

### 5.3 Search and Rescue

Purpose: practical SAR-compatible field guidance.

Includes:

- lost-person behavior
- signaling
- shelter-in-place
- group accountability
- search pattern concepts
- incident reporting data
- emergency communication
- map-grid references
- probability-of-area concepts

### 5.4 Navigation and Field Orientation

Includes:

- map reading
- compass use
- GPS coordinate formats
- UTM/MGRS/latitude-longitude basics
- route planning
- terrain association
- declination
- dead reckoning
- emergency navigation

### 5.5 Weather and NOAA References

Includes:

- NOAA weather terminology
- warning/watch/advisory interpretation
- cloud and storm indicators
- lightning safety
- wind chill and heat index
- marine weather basics
- mountain weather
- fire weather
- flood risk

### 5.6 Water

Includes:

- water sourcing
- filtration
- disinfection
- contamination indicators
- cold-water hazards
- river crossing
- ice safety
- coastal/tidal considerations

### 5.7 Fire, Shelter, and Exposure

Includes:

- fire safety
- fire lays
- emergency shelter
- clothing systems
- insulation
- exposure management
- stove and fuel safety
- wildfire restrictions

### 5.8 Food, Plants, and Fungi

Includes:

- edible plant identification
- poisonous plant identification
- fungus identification warnings
- lookalikes
- seasonality
- plant parts
- habitat
- preparation safety
- absolute no-eat rules

### 5.9 Wildlife

Includes:

- mammal identification
- reptile and amphibian identification
- bird basics
- insect and arthropod hazards
- bear, cougar, moose, bison, alligator, and snake encounters
- tracks and scat
- disease vectors

### 5.10 Fish and Aquatic Life

Includes:

- fish identification
- habitat
- seasonal behavior
- invasive species
- safe handling
- consumption advisories references
- fishing regulation pointers

### 5.11 Hunting, Trapping, and Harvest Ethics

Includes:

- field safety
- species identification
- seasonal and legal caveats
- ethical shot placement references
- field dressing overview
- game care
- state regulation links and disclaimers

The pack MUST avoid presenting regulation-sensitive instructions as universally
valid.

### 5.12 Geology and Terrain

Includes:

- rocks and minerals
- terrain hazards
- landslide risk
- karst and caves
- coastal geology
- desert hazards
- glacial terrain
- USGS references

### 5.13 Forestry and Land Management

Includes:

- forest types
- tree identification
- disease and pests
- fire ecology
- Leave No Trace
- public land management basics
- agency roles

### 5.14 Tools, Equipment, and Repair

Includes:

- knives
- axes and saws
- stoves
- water filters
- tents
- packs
- boots
- GPS units
- radios
- headlamps
- fishing reels
- firearm care safety boundaries
- field repair guides
- maintenance checklists

---

## 6. Knowledge Object Hierarchy

The flagship pack MUST use domain-specific Knowledge Object subtypes in
addition to the base Phase 1 object model.

### 6.1 Top-level object classes

```text
ReferenceObject
  SafetyRule
  EmergencyProtocol
  Procedure
  DecisionTree
  IdentificationKey
  SpeciesProfile
  HazardProfile
  RegulationReference
  MapReference
  GPSReference
  WeatherReference
  TechnicalManual
  EquipmentRepairGuide
  Checklist
  QuickReferenceCard
  DiagramReference
  ImageReference
  GovernmentPublication
  UniversityReference
  ProfessionalFieldGuideReference
  SourceSummary
```

### 6.2 Required hierarchy for species

```text
SpeciesProfile
  Taxonomy
  CommonNames
  Range
  Habitat
  Seasonality
  IdentificationFeatures
  Lookalikes
  Hazards
  HumanUse
  LegalStatus
  ConservationStatus
  Images
  Diagrams
  SourceCitations
  ReviewStatus
```

Species objects MUST include authoritative taxonomy and region applicability.
Plant, fungus, wildlife, and fish profiles MUST be reviewable by domain experts.

### 6.3 Required hierarchy for procedures

```text
Procedure
  Purpose
  Preconditions
  RequiredEquipment
  Contraindications
  Steps
  Warnings
  FailureModes
  StopConditions
  RelatedDiagrams
  RelatedDecisionTrees
  Citations
  HumanReview
```

Emergency procedures MUST include explicit stop conditions and escalation
triggers.

### 6.4 Required hierarchy for decision trees

```text
DecisionTree
  Scope
  EntryCriteria
  Questions
  Branches
  Outcomes
  ConfidenceLimits
  EmergencyEscalation
  SourceCitations
  ReviewStatus
```

Decision trees MUST prefer conservative outcomes when uncertainty is high.

### 6.5 Required hierarchy for identification keys

```text
IdentificationKey
  TaxonOrDomain
  RegionApplicability
  ObservableTraits
  TraitDefinitions
  Branches
  Lookalikes
  Disqualifiers
  RequiredImages
  ConfidenceLimits
  ExpertReview
```

Identification keys MUST separate beginner-observable traits from expert-only
traits.

---

## 7. Relationship Model

The pack MUST include an explicit relationship graph.

Required relationship types:

- `cites`
- `derived_from`
- `reviewed_by`
- `applies_to_region`
- `applies_to_season`
- `has_hazard`
- `has_contraindication`
- `requires_equipment`
- `requires_skill`
- `next_step`
- `alternative_step`
- `lookalike_of`
- `confusable_with`
- `safe_substitute_for`
- `not_safe_substitute_for`
- `regulated_by`
- `supersedes`
- `has_diagram`
- `has_image`
- `has_map`
- `has_quick_reference`
- `belongs_to_module`

High-risk relationships MUST be independently reviewed.

Examples:

```yaml
- from: "ko:ogm.pack.north-american-outdoor:species:amanita-bisporigera"
  relation: "confusable_with"
  to: "ko:ogm.pack.north-american-outdoor:species:agaricus-campestris"
  risk: "fatal_misidentification"
  review_required: true

- from: "ko:ogm.pack.north-american-outdoor:procedure:treat-hypothermia"
  relation: "has_quick_reference"
  to: "ko:ogm.pack.north-american-outdoor:quick-card:hypothermia"
```

---

## 8. Metadata Standard for Gold Packs

Every object MUST include baseline metadata from the OGM Metadata Standard plus
field-specific metadata.

Required field metadata:

```yaml
field_context:
  domain: "emergency_medicine"
  subdomain: "cold_exposure"
  region_applicability:
    countries: ["US", "CA"]
    states_provinces: []
    ecoregions: []
  season_applicability: ["winter", "shoulder_season"]
  environment_applicability: ["mountain", "forest", "subalpine"]
  user_skill_level: "trained_layperson"
  risk_level: "critical"
  time_sensitivity: "immediate"
  equipment_dependency: ["insulation", "shelter", "warm_fluids_if_safe"]
  legal_sensitivity: "none"
  review_required: true
```

Gold Pack metadata MUST support filtering without opening large object bodies.

---

## 9. Image Storage

Images are first-class evidence, not decoration.

Image assets MUST include:

- stable `media_id`
- source attribution
- license
- subject entity IDs
- capture context when known
- region
- season
- life stage
- view angle
- diagnostic feature annotations
- quality rating
- reviewer notes

Image categories:

- species overview
- diagnostic close-up
- lookalike comparison
- tracks/scat/sign
- habitat
- hazard
- equipment
- medical
- terrain
- weather

Image derivatives SHOULD include:

- thumbnail
- field-card resolution
- full reference resolution
- annotation overlay

The runtime MUST retrieve thumbnails before full images unless the task
requires diagnostic inspection.

---

## 10. Diagram Storage

Diagrams MUST be stored separately from images and linked to the procedures or
objects they explain.

Diagram types:

- anatomy
- knots
- splints
- shelters
- trap/rigging safety concepts
- weather systems
- map/compass examples
- equipment exploded views
- repair sequences
- geological cross-sections
- decision flow charts

Diagram metadata MUST include:

```yaml
diagram:
  media_id: "media:diagram:hypothermia-treatment-flow-v1"
  diagram_type: "flow_chart"
  linked_objects:
    - "ko:ogm.pack.north-american-outdoor:procedure:treat-hypothermia"
  required_for_answer: true
  retrieval_trigger:
    - "procedure_step_complexity"
    - "visual_sequence"
```

The runtime SHOULD retrieve diagrams when text alone is likely to cause
misexecution.

---

## 11. Maps and GPS References

The pack MUST support map-aware retrieval without requiring all map tiles in
RAM.

Map assets:

- regional overview maps
- ecoregion maps
- species range maps
- hazard maps
- public land jurisdiction references
- NOAA/USGS reference overlays when licensed
- grid examples
- coordinate-format guides

Map metadata MUST include:

```yaml
map:
  media_id: "media:map:na-ecoregions-level3"
  map_type: "ecoregion"
  bounding_box:
    west: -170.0
    south: 5.0
    east: -50.0
    north: 83.0
  scale_hint: "regional"
  coordinate_system: "EPSG:4326"
  source_id: "src:epa-ecoregions"
  tile_profile: "offline-low-memory"
```

GPS references MUST include:

- coordinate format explanations
- conversion procedures
- datum warnings
- UTM zone references
- MGRS basics
- location reporting templates
- SAR-compatible report formats

The runtime MUST retrieve maps when a query includes location, route, terrain,
species range, regulation region, wildfire/flood context, or public land
jurisdiction.

---

## 12. Species Database

The species database is a professional reference subsystem.

Required groups:

- trees
- shrubs
- herbaceous plants
- poisonous plants
- edible plants
- fungi
- mammals
- reptiles
- amphibians
- birds of field relevance
- freshwater fish
- saltwater fish of field relevance
- insects and arthropods
- medically significant species
- invasive species

Each SpeciesProfile MUST include:

- accepted scientific name
- common names
- taxonomy source
- authoritative identifiers where available
- range
- habitat
- seasonality
- diagnostic features
- lookalikes
- confidence limitations
- risk notes
- conservation/legal notes
- source citations
- image set
- review status

Species with food, venom, toxicity, disease, legal, or conservation relevance
MUST require human expert review.

---

## 13. Decision Trees

Decision trees MUST be used for high-consequence branching tasks.

Required decision tree families:

- emergency severity triage
- evacuation decision
- hypothermia/heat illness differentiation
- water treatment selection
- storm/lightning response
- lost-person immediate action
- plant/fungus no-eat screening
- wildlife encounter response
- route continuation vs retreat
- equipment failure workaround
- fishing/hunting regulation lookup path

Decision trees MUST expose:

- entry criteria
- required observations
- stop conditions
- confidence level
- source basis
- human reviewer

When a decision tree applies, retrieval MUST fetch it before broad explanatory
objects.

---

## 14. Identification Keys

Identification keys MUST support field observation, not laboratory certainty.

Key types:

- dichotomous keys
- multi-access trait keys
- visual comparison keys
- hazard-first exclusion keys
- region-specific keys

Keys MUST include:

- trait definitions
- required observation quality
- photo examples
- common mistakes
- lookalike warnings
- confidence thresholds
- expert-review notes

For edible plants and fungi, keys MUST default to refusal or uncertainty when
diagnostic traits are missing.

---

## 15. Procedures and Emergency Protocols

Procedures MUST be operationally clear and source-attributed.

Procedure categories:

- emergency medicine
- shelter construction
- fire management
- water treatment
- navigation
- signaling
- weather response
- animal encounter response
- equipment repair
- food handling
- field dressing
- fishing gear maintenance
- camp hygiene

Emergency protocols MUST include:

- immediate actions
- danger signs
- stop conditions
- evacuation triggers
- what not to do
- required equipment
- when to seek professional help
- citation trail
- quick reference card link

No emergency protocol may be approved without human review.

---

## 16. Technical Manuals and Equipment Repair Guides

Technical manuals are structured references for field-maintainable equipment.

Required equipment domains:

- water filters
- stoves
- tents and poles
- packs and buckles
- boots and laces
- knives and sharpening
- axes and saws
- GPS devices
- radios
- headlamps
- fishing reels
- waders and patching
- firearm maintenance safety references, where lawful and carefully bounded

Repair guides MUST include:

- symptoms
- likely causes
- tools/materials
- field-safe procedure
- failure modes
- manufacturer manual references
- safety warnings
- replacement-part references when available

The runtime SHOULD retrieve manuals when the user asks about a named product,
part, fault, maintenance task, exploded diagram, or repair sequence.

---

## 17. Illustrated References

Illustrated references MUST be treated as Knowledge Objects with attached
media, not loose images.

Required illustrated reference types:

- knots and hitches
- splints and bandages
- animal tracks
- leaf arrangements
- mushroom morphology
- fish anatomy
- map symbols
- cloud types
- shelter forms
- fire lays
- tool parts
- reel components

Illustrated references MUST include low-resolution quick versions and higher
resolution diagnostic versions.

---

## 18. Source Classes

Gold Standard packs MUST prefer authoritative sources.

### 18.1 Government publications

Expected source families:

- National Park Service
- U.S. Forest Service
- Bureau of Land Management
- U.S. Fish and Wildlife Service
- state/provincial wildlife agencies
- state/provincial fish and game agencies
- public health agencies
- emergency management agencies
- Canadian federal and provincial agencies

### 18.2 University references

Expected source families:

- extension services
- herbarium references
- forestry schools
- wildlife departments
- medical/wilderness medicine training references when legally usable
- mycology and botany teaching materials

### 18.3 Professional field guides

Professional field guides MAY be used when licensing allows, but they MUST NOT
be treated as automatically authoritative. Human review MUST confirm quality.

### 18.4 State and provincial regulations

Regulations MUST be stored as reference pointers and summarized conservatively.

Rules:

- regulations are region-specific
- regulations expire or change
- runtime answers MUST include currency date
- runtime MUST advise checking official sources when legality matters
- pack publication MUST include regulation freshness metadata

### 18.5 NOAA, USGS, and weather references

NOAA and USGS content SHOULD be first-class source families for:

- weather terminology
- hazards
- marine conditions
- hydrology
- topography
- geology
- earthquakes
- landslides
- volcanoes
- maps
- coordinate systems

---

## 19. Checklists, Flow Charts, and Quick Reference Cards

The pack MUST include a quick-use layer for stressful field situations.

Required checklists:

- pre-trip planning
- 10 essentials
- weather go/no-go
- first aid kit
- water treatment
- camp setup
- fire safety
- bear country
- tick prevention
- fishing/hunting legal check
- navigation before departure
- equipment repair kit
- emergency communication

Required flow charts:

- medical triage
- lost-person immediate action
- severe weather response
- water safety
- route retreat decision
- plant/fungus edibility refusal path
- equipment failure diagnosis

Required quick reference cards:

- hypothermia
- heat illness
- bleeding control
- lightning
- bear encounter
- snakebite
- water disinfection
- SOS/signaling
- GPS location report
- map/compass basics
- fire restrictions reminder

Quick references MUST be tiny, printable, and indexed for first retrieval.

---

## 20. Visual Identification Systems

A Gold Pack MUST include visual identification systems for field domains where
text alone is insufficient.

Required capabilities:

- side-by-side lookalike comparison
- diagnostic feature highlighting
- seasonal variation images
- juvenile/adult/life-stage variation
- range and habitat filtering
- confidence-limited results
- required-observation prompts

The runtime MUST avoid definitive species claims when retrieved evidence lacks
required diagnostic observations.

---

## 21. Confidence Scoring

Gold Pack confidence scoring MUST combine evidence quality, extraction quality,
review quality, and applicability.

Recommended fields:

```yaml
confidence:
  evidence_quality: 0.95
  source_authority: 0.97
  extraction_confidence: 0.92
  human_review_confidence: 1.0
  regional_applicability: 0.88
  temporal_currency: 0.90
  media_support: 0.85
  overall: 0.92
  confidence_class: "high"
```

Confidence classes:

- `verified`
- `high`
- `moderate`
- `low`
- `insufficient`

Emergency, edible, toxic, legal, and medical content MUST require higher
confidence thresholds than general educational content.

---

## 22. Knowledge Provenance

Every answerable object MUST preserve provenance.

Required provenance:

- source ID
- source title
- source organization or author
- source class
- license
- retrieval date
- publication date when known
- approved date
- source locator
- extraction method
- transformation lineage
- human reviewer
- validation run ID

Provenance MUST be available offline.

The runtime MUST be able to answer:

- where did this claim come from?
- who reviewed it?
- what source version was used?
- what is the confidence?
- what changed since the last pack version?

---

## 23. Human Review Workflow

The Gold Standard requires human review gates beyond automated validation.

Required review queues:

- source approval
- licensing approval
- species safety review
- medical review
- legal/regulation review
- emergency protocol review
- map/regional applicability review
- final pack publication review

Review record:

```yaml
review:
  review_id: "review:2026-07-06:medical:001"
  reviewer_role: "wilderness_medicine_reviewer"
  reviewer_identity_policy: "verified_internal"
  object_ids:
    - "ko:ogm.pack.north-american-outdoor:protocol:hypothermia"
  decision: "approved_with_notes"
  notes: "Clarified evacuation trigger language."
  reviewed_at: "2026-07-06T18:00:00Z"
```

Agents may propose. Humans approve official content.

---

## 24. Offline Retrieval Strategy for Small Models

The runtime MUST retrieve the smallest sufficient set of trusted evidence.

### 24.1 Retrieval priority order

For each user query, the runtime SHOULD retrieve in this order:

1. Safety and emergency overrides
2. Query intent and domain classification
3. Region, season, environment, and legal context
4. Quick reference card or decision tree when applicable
5. Core Knowledge Objects
6. Relationship graph expansions
7. Images or diagrams required for execution or identification
8. Maps and GPS references when spatial context matters
9. Manuals or long technical references when the query names equipment,
   regulation, source, or procedure detail
10. Source excerpts and provenance for citation

### 24.2 What to retrieve first

Retrieve first:

- emergency protocol if the query indicates injury, exposure, lost person,
  dangerous animal, drowning, lightning, wildfire, firearm incident, poisoning,
  or severe weather
- legal/regulation warning if the query involves harvest, hunting, fishing,
  trapping, fire restrictions, public land use, protected species, or collection
- no-eat/no-touch hazard gate for plants, fungi, unknown berries, unknown
  mushrooms, venomous animals, or contaminated water
- quick reference card if one exists for the task

### 24.3 What to retrieve second

Retrieve second:

- the primary procedure, protocol, species profile, or regulation reference
- the best related decision tree
- contraindications and stop conditions
- lookalikes or confusable hazards
- relevant checklist

### 24.4 When to open a manual

Open a manual when:

- the user names a specific product, tool, model, component, or fault
- an exploded diagram is needed
- torque/specification/part order matters
- the question asks for maintenance or repair
- the procedure depends on manufacturer-specific instructions

Manuals SHOULD be opened as targeted sections, not full documents.

### 24.5 When to retrieve diagrams

Retrieve diagrams when:

- the procedure has spatial steps
- misassembly or misapplication could cause harm
- knots, splints, bandages, shelters, repairs, anatomy, or weather systems are
  involved
- the object marks `required_for_answer: true`

### 24.6 When to retrieve maps

Retrieve maps when:

- the query includes location
- species range matters
- weather/geology/terrain context matters
- public land jurisdiction or regulations matter
- route planning or evacuation is involved
- GPS, UTM, MGRS, datum, or grid references appear

The runtime MUST use low-memory map tile access and avoid loading broad map
regions unnecessarily.

### 24.7 When to retrieve decision trees

Retrieve decision trees when:

- the user is deciding what to do next
- symptoms or conditions are ambiguous
- safety depends on branching observations
- the query includes identification uncertainty
- law/regulation applicability depends on jurisdiction or species

### 24.8 When to retrieve identification keys

Retrieve identification keys when:

- the user asks "what is this?"
- the user provides traits, image descriptions, habitat, or season
- the object domain includes lookalikes or hazards
- a species result has confidence below verified/high

The runtime MUST ask for missing diagnostic observations rather than guessing.

---

## 25. Pi 5 Memory Strategy

The pack MUST reduce memory usage without reducing knowledge.

Runtime rules:

- Keep manifest, module catalog, route hints, emergency index, and metadata
  filters memory-resident.
- Keep object bodies, large media, manuals, and maps on the Knowledge Volume
  until needed.
- Prefer deterministic indexes before vector search.
- Use bounded graph expansion.
- Use thumbnails before full images.
- Use map tile windows instead of full map loads.
- Cache only the current task context and high-value emergency cards.
- Evict large media aggressively.
- Keep citation ledger compact.

Recommended hot set:

```yaml
pi5_hot_set:
  manifest: resident
  module_catalog: resident
  emergency_index: resident
  metadata_filters: resident
  entity_alias_index: compact_resident
  keyword_index_blocks: mmap_or_paged
  vector_index: paged_or_optional
  object_bodies: on_demand
  manuals: on_demand
  maps: tiled_on_demand
  images: thumbnail_first
```

---

## 26. Validation Requirements

A Gold Standard pack MUST pass stricter validation than a standard pack.

Required validation classes:

- schema validation
- source provenance validation
- license validation
- citation coverage validation
- relationship graph validation
- emergency protocol review validation
- species lookalike validation
- regulation freshness validation
- map bounds validation
- media attribution validation
- retrieval scenario validation
- Pi 5 memory profile validation
- human review completeness validation

Failure in emergency, medical, edible/toxic, legal, or source provenance
validation MUST block publication.

---

## 27. Minimum Flagship Acceptance Criteria

The North American Outdoor Expert Pack v1.0 SHOULD NOT be considered
flagship-ready until it includes:

- complete module catalog
- reviewed source catalog
- emergency quick reference layer
- high-confidence medical and safety protocols
- species database with reviewed high-risk species
- visual identification system for priority hazards and common field species
- maps and GPS references for region-aware retrieval
- NOAA and USGS reference integration where applicable
- state/provincial regulation freshness strategy
- complete provenance ledger
- human review audit trail
- retrieval validation scenarios
- Pi 5 offline performance profile

The pack may ship with scoped coverage, but it MUST be honest about coverage
limits and Knowledge Debt.

---

## 28. Recommended Changes to Previous Architecture Phases

These recommendations extend the approved architecture. They do not replace it.

### 28.1 Phase 1 Knowledge Architecture

Recommended improvements:

- Add a `gold_standard_profile` section to the Expert Pack manifest.
- Add explicit `quick_reference`, `decision_tree`, `identification_key`,
  `map_reference`, and `manual_section` object subtypes.
- Add first-class media derivative metadata for thumbnail, field-card, and full
  diagnostic resolution.
- Add map-specific index requirements separate from generic media indexes.
- Add risk-tiered confidence thresholds to the Knowledge Object spec.
- Add a required `human_review_required` flag for medical, legal, edible,
  toxic, emergency, and high-risk equipment content.

### 28.2 Phase 2 Agent Control Center

Recommended improvements:

- Add Gold Standard coverage dashboards by module, region, source class, and
  risk level.
- Add human review workbenches for emergency, medical, legal, and species
  safety queues.
- Add a publication readiness screen that shows blocker categories, not only
  aggregate status.
- Add pack-quality comparison views so future packs can be measured against
  the flagship standard.
- Add review identity and role tracking for auditability.

### 28.3 Phase 3 Knowledge Foundry

Recommended improvements:

- Add a Visual Evidence Department responsible for image, diagram, annotation,
  and media derivative quality.
- Add a Geospatial Department responsible for map assets, coordinate systems,
  ranges, overlays, and regional applicability.
- Add a Regulation Freshness Department or workflow for state/provincial legal
  content.
- Add emergency-content escalation gates that require expert human review.
- Add retrieval scenario generation as a required validation output.
- Add field-card generation as a standard compilation output.

### 28.4 Phase 4 Chief Knowledge Officer

Recommended improvements:

- Add a Gold Standard Score that tracks trust, utility, coverage, provenance,
  review completeness, and runtime usability.
- Add Knowledge Debt classes for missing diagrams, missing maps, missing
  decision trees, missing human review, stale regulations, and insufficient
  visual evidence.
- Add explicit CKO refusal policies for unsafe low-confidence domains.
- Add flagship benchmark missions that every future pack must pass.
- Add dashboards for "field readiness" rather than only content completeness.

### 28.5 Phase 5 Agent Communication Protocol

Recommended improvements:

- Add ACP message types for `HumanReviewQueued`, `HumanReviewCompleted`,
  `GoldScoreUpdated`, `RetrievalScenarioPassed`,
  `RetrievalScenarioFailed`, `MediaDerivativeCreated`,
  `MapAssetCreated`, `RegulationFreshnessChecked`,
  `QuickReferenceCardCreated`, and `DecisionTreeCreated`.
- Add standard payload schemas for review decisions, map assets, media
  derivatives, and Gold Standard score updates.
- Add priority escalation rules for emergency-content validation failures.
- Add routing defaults for visual evidence, geospatial, and regulation
  workflows if those Foundry departments are added.

---

## 29. Company-Level Quality Standard

The Gold Standard should become the permanent quality bar for Offgrid Minds.

Every future Expert Pack SHOULD answer:

- What would a serious professional actually carry?
- What information must be trusted under stress?
- What must be visual?
- What must be regional?
- What must be reviewed by a human?
- What must the offline model retrieve first?
- Where should the model refuse or ask for more evidence?
- What is the pack's honest coverage limit?

A Gold Standard Expert Pack is finished only when it is useful, trustworthy,
organized, reviewable, and executable by a small offline model under real field
constraints.
