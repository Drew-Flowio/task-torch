# OGM Milestone 1 / 2 / 3 / 4 / 5 / 6

Functional vertical-slice foundation for Offgrid Minds implementation.

This package intentionally implements:

- Raw Source Vault
- Intake Ledger
- Knowledge Repository Core
- Intake-to-Repository bridge (Milestone 2)
- Coverage Matrix and CRS evaluation (Milestone 3)
- First-class operational records (missions, curator recommendations, human approvals)
- Curator-001 manual source recommendation workflow (Milestone 4)
- Controlled candidate intake queue (Milestone 5)
- Candidate review workflow and approved intake orchestration (Milestone 6)
- ACP event integration via `ogm_acp`

It does not implement OCR, embeddings, vector search, pack compilation, autonomous research agents, or broad web crawling.

## Directory Structure

```text
internal_tools/ogm_milestone_001/
  acp_events.py
  audit.py
  bridge.py
  candidate_queue.py
  coverage.py
  crs_evaluation.py
  curator.py
  intake_ledger.py
  knowledge_repository.py
  orchestration.py
  raw_source_vault.py
  records.py
  review.py
  schema.py
  utils.py
  tests/
    test_milestone_001.py
    test_milestone_002.py
    test_milestone_003.py
    test_milestone_004.py
    test_milestone_005.py
    test_milestone_006.py
```

## Database Schema

The Intake Ledger uses SQLite tables:

- `sources` (includes Milestone 2 structured intake link columns)
- `source_revisions`
- `audit_events`
- `missions` (Milestone 3)
- `curator_recommendations` (Milestone 3)
- `human_approvals` (Milestone 3)
- `candidate_sources` (Milestone 5)
- `candidate_review_events` (Milestone 6)

The Knowledge Repository Core uses SQLite tables:

- `knowledge_objects`
- `object_revisions`
- `evidence`
- `object_evidence`
- `relationships`
- `audit_events`
- `coverage_objects`
- `canonical_reference_requirements`
- `source_coverage_links`
- `evidence_coverage_links`
- `crs_satisfactions` (Milestone 3)
- `mission_suggestions` (Milestone 3)

## Minimal API

```python
from pathlib import Path

from internal_tools.ogm_acp import ACPLogStore
from internal_tools.ogm_milestone_001 import (
    CandidateIntakeQueue,
    CRSEvaluator,
    CoverageStore,
    Curator001,
    IntakeLedger,
    KnowledgeRepository,
    OperationalRecords,
    RawSourceVault,
    approved_candidate_to_repository_evidence,
    bridge_intake_to_repository,
)

root = Path("/tmp/ogm-milestone-003")
records = OperationalRecords(root / "intake.db")
queue = CandidateIntakeQueue(root / "intake.db", records=records)
records.create_mission(
    mission_id="mission:vertical-slice-001",
    title="Improve tree coverage",
    target_pack_id="ogm.pack.north-american-outdoor",
    metadata={"coverage_object_ids": ["cov:demo:001"]},
)

ledger = IntakeLedger(root / "intake.db")
vault = RawSourceVault(root / "vault", ledger)
repo = KnowledgeRepository(root / "repository.db", acp_log_store=ACPLogStore(root / "acp.jsonl"))
coverage = CoverageStore(root / "repository.db")
acp_log = ACPLogStore(root / "acp.jsonl")

coverage.create_coverage_object(
    coverage_object_id="cov:demo:001",
    domain="outdoor",
    category="species",
    title="Demo coverage object",
)
coverage.add_canonical_reference_requirement(
    coverage_object_id="cov:demo:001",
    reference_type="government_publication",
)

source = vault.store_approved_source(
    root / "sample.txt",
    source="human-approved upload",
    license="internal_test",
    mission="mission:vertical-slice-001",
    mission_id="mission:vertical-slice-001",
    curator="curator-001",
    approval_status="approved",
    coverage_object_ids=["cov:demo:001"],
    canonical_reference_type="government_publication",
)

bridged = bridge_intake_to_repository(
    ledger=ledger,
    repository=repo,
    source_uuid=source["uuid"],
    revision_uuid=source["revision"]["revision_uuid"],
    coverage_store=coverage,
    vault=vault,
    acp_log_store=acp_log,
)

evaluator = CRSEvaluator(coverage, ledger=ledger, repository=repo, acp_log_store=acp_log)
evaluation = evaluator.evaluate_and_record("cov:demo:001")
suggestions = evaluator.generate_mission_suggestions(
    "cov:demo:001",
    mission_id="mission:vertical-slice-001",
)

curator = Curator001(records=records, coverage_store=coverage, crs_evaluator=evaluator)
candidate = queue.submit_candidate(
    title="Demo Tree Reference",
    publisher="Example Government Forestry Office",
    url="https://example.gov/tree-reference",
    source_type="government",
    submitted_by="human:submitter:001",
    mission_id="mission:vertical-slice-001",
    coverage_object_id="cov:demo:001",
    proposed_canonical_reference_type="government_publication",
    notes="Manual candidate for Curator-001 review.",
    license_status="public_domain_or_government_work",
    authority_score=0.9,
    authority_reason="Government forestry publisher.",
)
queue.assign_reviewer(
    candidate["candidate_id"],
    assigned_reviewer="human:reviewer:001",
    review_priority="high",
)
queue.attach_license_evidence(
    candidate["candidate_id"],
    license_status="public_domain_or_government_work",
    license_source_url="https://example.gov/license",
    license_text_excerpt="Government work.",
    license_checked_by="human:reviewer:001",
)
queued_recommendations = curator.recommend_from_queue(
    "mission:vertical-slice-001",
    candidate_queue=queue,
    candidate_ids=[candidate["candidate_id"]],
)

recommendations = curator.recommend_sources(
    "mission:vertical-slice-001",
    candidates=[
        {
            "title": "Demo Tree Reference",
            "publisher": "Example Government Forestry Office",
            "url": "https://example.gov/tree-reference",
            "source_type": "government",
            "authority_score": 0.9,
            "license_status": "public_domain_or_government_work",
            "coverage_contribution": "Satisfies government publication CRS.",
            "suggested_canonical_reference_type": "government_publication",
            "suggested_coverage_object_id": "cov:demo:001",
            "reason_recommended": "Publisher matches trusted source policy.",
            "risks_limitations": ["Manual candidate requires human review."],
        }
    ],
)

# After human approval, an approved local-file candidate can be vaulted and bridged:
# queue.update_candidate_review(candidate_id, status="approved_for_intake")
# approved_candidate_to_repository_evidence(
#     candidate_queue=queue,
#     candidate_id=candidate_id,
#     ledger=ledger,
#     vault=vault,
#     repository=repo,
#     coverage_store=coverage,
#     strict_license_review=True,
# )
```

## Testing

```bash
cd "/Users/andrewcoghill/Desktop/Task Torch"
python3 -m unittest discover -s internal_tools/ogm_milestone_001/tests -v
python3 -m unittest discover -s internal_tools/ogm_acp/tests -v
```

## Assumptions

- Milestone 1/2/3 is local and single-node.
- Only human-approved sources can enter the Raw Source Vault.
- UUID4 is acceptable for the first implementation.
- SQLite is sufficient until implementation pressure proves otherwise.
- Raw source storage is filesystem-backed for inspectability.
- CRS satisfaction is matched by `canonical_reference_type` on linked sources or evidence provenance.
- Mission suggestions are records only; no autonomous agents are spawned.
- Curator-001 only evaluates manually supplied candidate sources.
- Curator-001 supports the North American Outdoor Expert Pack tree scope.
- Curator recommendations require a `human_approvals` record before source intake.
- Candidate duplicate detection is intentionally simple: normalized URLs, file checksums, and title/publisher similarity.
- URL-only candidates require a local file before `prepare_for_vault_intake` can return a Raw Source Vault payload.
- Candidate review events are append-only and preserve insertion order.
- `approved_candidate_to_repository_evidence` reuses the existing vault and bridge; it does not extract/OCR content.
- Strict license mode requires license review evidence before vault intake.

## Future Improvements

- Add reviewer workflow queues, status dashboards, and review SLA reporting.
- Add authority-level validation beyond reference type matching.
- Wire ACP events into the full `ogm_acp` bus with handlers.
- Add OCR and normalized source stages only after the vault and repository spine are validated.
