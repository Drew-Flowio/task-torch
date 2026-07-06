# OGM Agent Communication Protocol (ACP)

Reusable Python package implementing **ACP v1.0** for Offgrid Minds agents.

Full specification: [`docs/specs/ogm-agent-communication-protocol-v1.md`](../../docs/specs/ogm-agent-communication-protocol-v1.md)

## Purpose

ACP is the standardized communication layer for Offgrid Minds agents. Agents exchange structured JSON messages instead of direct function calls whenever practical.

This package provides:

- Message envelope construction and validation
- Canonical message type constants
- Append-only JSONL log store with replay
- In-process message bus
- Agent registry for discovery
- Mission-aware router
- Retry and dead-letter handling

## Quick start

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from internal_tools.ogm_acp import (
    ACPBus,
    ACPLogStore,
    AgentRegistry,
    MissionRouter,
    create_message,
)

with TemporaryDirectory() as tmp:
    store = ACPLogStore(Path(tmp) / "acp.jsonl")
    registry = AgentRegistry()
    router = MissionRouter(registry)
    bus = ACPBus(store, registry=registry, router=router)

    received = []
    router.subscribe_department("licensing", lambda msg: received.append(msg))

    registry.register(
        agent_id="agent:research:001",
        department="research",
        role="research",
    )

    message = create_message(
        message_type="SourceDiscovered",
        agent_id="agent:research:001",
        department="research",
        mission_id="mission:outdoor-pack:trees-001",
        payload={
            "source_candidate_id": "artifact:source-candidate:001",
            "title": "USDA Field Guide to Trees",
        },
        references={"correlation_id": "corr:001"},
    )

    bus.publish(message)
    print(len(received), store.count())
```

Run from the repository root so `internal_tools` resolves on `PYTHONPATH`.

## Message envelope

Every message includes:

- `version`, `message_id`, `timestamp`, `message_type`
- `agent_id`, `department`, `mission_id`
- `priority`, `status`, `payload`, `references`, `errors`, `retry_count`

Optional routing fields: `to_department`, `to_agent_id`, `requires_ack`, `ttl_seconds`, `trace_id`.

## Logging and replay

All messages are appended to an immutable JSONL log:

```python
history = store.replay(mission_id="mission:outdoor-pack:trees-001")
bus.replay(mission_id="mission:outdoor-pack:trees-001", redispatch=True)
```

## Agent discovery

```python
registry.registration_message(
    agent_id="agent:licensing:001",
    department="licensing",
    role="licensing",
)
registry.heartbeat("agent:licensing:001", status="idle")
```

## Routing

Default routes:

| Message type | Department |
|---|---|
| `SourceDiscovered` | `licensing` |
| `SourceApproved` | `acquisition` |
| `OCRCompleted` | `knowledge_engineering` |
| `KnowledgeObjectCreated` | `validation` |
| `ValidationPassed` | `compilation` |
| `PackCompiled` | `publishing` |
| `HumanApprovalRequested` | `system` |

Override or extend routes through `MissionRouter(route_table={...})`.

## Tests

```bash
cd "/Users/andrewcoghill/Desktop/Task Torch"
python3 -m unittest discover -s internal_tools/ogm_acp/tests -v
```

## Design notes

- Stdlib only (no external dependencies)
- Transport-agnostic: v1 uses in-process delivery and JSONL persistence
- Designed for five agents today and hundreds in future distributed deployments
- Does not implement research agents or Foundry workers — communication layer only
