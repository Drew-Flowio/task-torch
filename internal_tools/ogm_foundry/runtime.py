"""Shared Foundry backend service wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from internal_tools.ogm_acp import ACPLogStore
from internal_tools.ogm_foundry.config import FoundryConfig
from internal_tools.ogm_milestone_001.candidate_queue import CandidateIntakeQueue
from internal_tools.ogm_milestone_001.coverage import CoverageStore
from internal_tools.ogm_milestone_001.crs_evaluation import CRSEvaluator
from internal_tools.ogm_milestone_001.curator import Curator001
from internal_tools.ogm_milestone_001.intake_ledger import IntakeLedger
from internal_tools.ogm_milestone_001.knowledge_repository import KnowledgeRepository
from internal_tools.ogm_milestone_001.raw_source_vault import RawSourceVault
from internal_tools.ogm_milestone_001.records import OperationalRecords


@dataclass
class FoundryServices:
    config: FoundryConfig
    records: OperationalRecords
    queue: CandidateIntakeQueue
    coverage: CoverageStore
    ledger: IntakeLedger
    vault: RawSourceVault
    repository: KnowledgeRepository
    curator: Curator001
    crs_evaluator: CRSEvaluator
    acp_log: ACPLogStore


def ensure_workspace(config: FoundryConfig) -> None:
    if not config.intake_db.is_file() or not config.repository_db.is_file():
        raise RuntimeError(
            "Foundry workspace not initialized. Run:\n"
            "  python3 -m internal_tools.ogm_foundry.bootstrap_workspace"
        )
    config.data_root.mkdir(parents=True, exist_ok=True)
    config.vault_root.mkdir(parents=True, exist_ok=True)


def load_services(config: FoundryConfig | None = None) -> FoundryServices:
    config = config or FoundryConfig.from_env()
    ensure_workspace(config)

    records = OperationalRecords(config.intake_db)
    queue = CandidateIntakeQueue(config.intake_db, records=records)
    coverage = CoverageStore(config.repository_db)
    ledger = IntakeLedger(config.intake_db)
    vault = RawSourceVault(config.vault_root, ledger)
    acp_log = ACPLogStore(config.data_root / "acp.jsonl")
    repository = KnowledgeRepository(config.repository_db, acp_log_store=acp_log)
    crs_evaluator = CRSEvaluator(
        coverage,
        ledger=ledger,
        repository=repository,
        acp_log_store=acp_log,
    )
    curator = Curator001(records=records, coverage_store=coverage, crs_evaluator=crs_evaluator)
    return FoundryServices(
        config=config,
        records=records,
        queue=queue,
        coverage=coverage,
        ledger=ledger,
        vault=vault,
        repository=repository,
        curator=curator,
        crs_evaluator=crs_evaluator,
        acp_log=acp_log,
    )
