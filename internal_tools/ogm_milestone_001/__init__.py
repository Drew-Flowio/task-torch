"""Milestone 1/2/3/4/5/6 implementation for Offgrid Minds.

This package intentionally implements:

- Raw Source Vault
- Intake Ledger
- minimal Knowledge Repository Core
- Intake-to-Repository bridge (Milestone 2)
- Coverage/CRS evaluation (Milestone 3)
- Curator-001 manual source recommendation workflow (Milestone 4)
- Controlled candidate intake queue (Milestone 5)
- Candidate review workflow and approved intake orchestration (Milestone 6)
"""

from internal_tools.ogm_milestone_001.bridge import bridge_intake_to_repository
from internal_tools.ogm_milestone_001.candidate_queue import CandidateIntakeQueue
from internal_tools.ogm_milestone_001.coverage import CoverageStore
from internal_tools.ogm_milestone_001.crs_evaluation import CRSEvaluator
from internal_tools.ogm_milestone_001.curator import Curator001
from internal_tools.ogm_milestone_001.intake_ledger import IntakeLedger
from internal_tools.ogm_milestone_001.knowledge_repository import KnowledgeRepository
from internal_tools.ogm_milestone_001.orchestration import approved_candidate_to_repository_evidence
from internal_tools.ogm_milestone_001.raw_source_vault import RawSourceVault
from internal_tools.ogm_milestone_001.records import OperationalRecords
from internal_tools.ogm_milestone_001.review import REVIEW_STATUSES, validate_transition

__all__ = [
    "IntakeLedger",
    "KnowledgeRepository",
    "RawSourceVault",
    "CandidateIntakeQueue",
    "CoverageStore",
    "CRSEvaluator",
    "Curator001",
    "OperationalRecords",
    "REVIEW_STATUSES",
    "approved_candidate_to_repository_evidence",
    "bridge_intake_to_repository",
    "validate_transition",
]
