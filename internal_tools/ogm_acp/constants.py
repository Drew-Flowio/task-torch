"""ACP v1.0 constants."""

ACP_VERSION = "1.0"

PRIORITIES = frozenset({"critical", "high", "medium", "low"})

MESSAGE_STATUSES = frozenset(
    {
        "pending",
        "sent",
        "delivered",
        "acknowledged",
        "failed",
        "dead_letter",
        "replayed",
    }
)

DEPARTMENTS = frozenset(
    {
        "research",
        "acquisition",
        "licensing",
        "ocr",
        "knowledge_engineering",
        "index_engineering",
        "validation",
        "compilation",
        "publishing",
        "cko",
        "system",
    }
)

MESSAGE_TYPES = frozenset(
    {
        "MissionCreated",
        "MissionAccepted",
        "MissionStarted",
        "MissionPaused",
        "MissionCompleted",
        "MissionFailed",
        "SourceDiscovered",
        "SourceRejected",
        "SourceApproved",
        "OCRCompleted",
        "DiagramExtracted",
        "EntityCreated",
        "KnowledgeObjectCreated",
        "KnowledgeObjectUpdated",
        "ValidationPassed",
        "ValidationFailed",
        "CoverageUpdated",
        "KnowledgeDebtCreated",
        "KnowledgeDebtResolved",
        "PackCompiled",
        "PackPublished",
        "HumanApprovalRequested",
        "HumanApprovalGranted",
        "HumanApprovalDenied",
        "AgentRegistered",
        "AgentHeartbeat",
        "MessageAcknowledged",
        "MessageFailed",
        "MessageDeadLettered",
        "SourceAcquired",
        "EvidenceLinked",
        "RepositoryObjectCreated",
        "CRSRequirementSatisfied",
        "CRSRequirementMissing",
        "CoverageMissionGenerated",
    }
)

DEFAULT_ROUTE_TABLE: dict[str, str] = {
    "SourceDiscovered": "licensing",
    "SourceApproved": "acquisition",
    "OCRCompleted": "knowledge_engineering",
    "KnowledgeObjectCreated": "validation",
    "ValidationPassed": "compilation",
    "PackCompiled": "publishing",
    "HumanApprovalRequested": "system",
}

REQUIRED_PAYLOAD_FIELDS: dict[str, tuple[str, ...]] = {
    "SourceDiscovered": ("source_candidate_id", "title"),
    "KnowledgeObjectCreated": ("object_id", "object_type", "title"),
    "HumanApprovalRequested": (
        "approval_target_type",
        "approval_target_id",
        "requested_action",
    ),
    "ValidationFailed": ("validation_profile", "blocker_count", "warning_count"),
    "MissionCreated": ("mission_id", "title"),
    "MissionFailed": ("reason",),
    "AgentRegistered": ("agent_id", "department", "role"),
    "SourceAcquired": ("source_uuid", "revision_uuid"),
    "EvidenceLinked": ("evidence_uuid", "source_uuid", "raw_revision_uuid"),
    "RepositoryObjectCreated": ("repository_object_id", "object_type", "title"),
    "CRSRequirementSatisfied": ("coverage_object_id", "reference_type"),
    "CRSRequirementMissing": ("coverage_object_id", "reference_type"),
    "CoverageMissionGenerated": ("mission_id", "coverage_object_id", "objective"),
}
