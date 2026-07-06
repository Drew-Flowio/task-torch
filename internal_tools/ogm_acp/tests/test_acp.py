import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_acp import (
    ACPBus,
    ACPLogStore,
    ACPValidationError,
    AgentRegistry,
    MissionRouter,
    RetryPolicy,
    create_message,
    should_retry,
)
from internal_tools.ogm_acp.errors import ACPError


class EnvelopeTests(unittest.TestCase):
    def test_create_and_round_trip_json(self):
        message = create_message(
            message_type="SourceDiscovered",
            agent_id="agent:research:001",
            department="research",
            mission_id="mission:test:001",
            payload={
                "source_candidate_id": "artifact:001",
                "title": "Guide",
            },
            references={"correlation_id": "corr:001"},
            priority="high",
        )
        restored = type(message).from_json(message.to_json())
        self.assertEqual(restored.message_id, message.message_id)
        self.assertEqual(restored.message_type, "SourceDiscovered")
        self.assertEqual(restored.payload["title"], "Guide")

    def test_missing_payload_field_raises(self):
        with self.assertRaises(ACPValidationError):
            create_message(
                message_type="SourceDiscovered",
                agent_id="agent:research:001",
                department="research",
                mission_id="mission:test:001",
                payload={"title": "Missing candidate id"},
            )

    def test_unknown_message_type_raises(self):
        with self.assertRaises(ACPValidationError):
            create_message(
                message_type="NotARealType",
                agent_id="agent:research:001",
                department="research",
                mission_id="mission:test:001",
            )


class LogStoreTests(unittest.TestCase):
    def test_append_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ACPLogStore(Path(tmp) / "acp.jsonl")
            message = create_message(
                message_type="MissionCreated",
                agent_id="agent:cko:001",
                department="cko",
                mission_id="mission:test:001",
                payload={"mission_id": "mission:test:001", "title": "Test mission"},
            )
            store.append(message)
            replayed = store.replay(mission_id="mission:test:001")
            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].message_type, "MissionCreated")

    def test_get_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ACPLogStore(Path(tmp) / "acp.jsonl")
            message = create_message(
                message_type="MissionStarted",
                agent_id="agent:cko:001",
                department="cko",
                mission_id="mission:test:001",
                payload={"mission_id": "mission:test:001", "title": "Test mission"},
            )
            store.append(message)
            found = store.get_by_id(message.message_id)
            self.assertIsNotNone(found)
            self.assertEqual(found.message_id, message.message_id)


class RegistryTests(unittest.TestCase):
    def test_register_and_list(self):
        registry = AgentRegistry()
        registry.register(
            agent_id="agent:licensing:001",
            department="licensing",
            role="licensing",
            capabilities=["review_source"],
        )
        agents = registry.list_agents(department="licensing")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].agent_id, "agent:licensing:001")

    def test_registration_message(self):
        registry = AgentRegistry()
        message = registry.registration_message(
            agent_id="agent:research:001",
            department="research",
            role="research",
        )
        self.assertEqual(message.message_type, "AgentRegistered")
        self.assertEqual(message.payload["role"], "research")


class RouterTests(unittest.TestCase):
    def test_default_route_to_licensing(self):
        router = MissionRouter()
        message = create_message(
            message_type="SourceDiscovered",
            agent_id="agent:research:001",
            department="research",
            mission_id="mission:test:001",
            payload={
                "source_candidate_id": "artifact:001",
                "title": "Guide",
            },
        )
        department, agent_id = router.resolve_destination(message)
        self.assertEqual(department, "licensing")
        self.assertIsNone(agent_id)


class BusTests(unittest.TestCase):
    def test_publish_logs_and_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ACPLogStore(Path(tmp) / "acp.jsonl")
            router = MissionRouter()
            received = []
            router.subscribe_department("licensing", received.append)
            bus = ACPBus(store, router=router)

            message = create_message(
                message_type="SourceDiscovered",
                agent_id="agent:research:001",
                department="research",
                mission_id="mission:test:001",
                payload={
                    "source_candidate_id": "artifact:001",
                    "title": "Guide",
                },
            )
            delivered = bus.publish(message)
            self.assertEqual(delivered.status, "delivered")
            self.assertEqual(len(received), 1)
            self.assertGreaterEqual(store.count(), 2)

    def test_acknowledge_emits_system_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ACPLogStore(Path(tmp) / "acp.jsonl")
            bus = ACPBus(store)
            message = create_message(
                message_type="SourceApproved",
                agent_id="agent:licensing:001",
                department="licensing",
                mission_id="mission:test:001",
                payload={"source_id": "src:001"},
            )
            published = bus.publish(message)
            bus.acknowledge(published)
            types = [item.message_type for item in store.replay(mission_id="mission:test:001")]
            self.assertIn("MessageAcknowledged", types)

    def test_retry_then_dead_letter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ACPLogStore(Path(tmp) / "acp.jsonl")
            router = MissionRouter()

            def fail_handler(_message):
                raise ACPError("transport_timeout", "timeout", retryable=True)

            router.subscribe_department("licensing", fail_handler)
            bus = ACPBus(store, router=router, retry_policy=RetryPolicy(max_retries=2))

            message = create_message(
                message_type="SourceDiscovered",
                agent_id="agent:research:001",
                department="research",
                mission_id="mission:test:001",
                payload={
                    "source_candidate_id": "artifact:001",
                    "title": "Guide",
                },
            )
            result = bus.publish(message)
            self.assertEqual(result.status, "dead_letter")
            self.assertGreaterEqual(result.retry_count, 2)


class RetryPolicyTests(unittest.TestCase):
    def test_non_retryable_error(self):
        message = create_message(
            message_type="SourceRejected",
            agent_id="agent:licensing:001",
            department="licensing",
            mission_id="mission:test:001",
            payload={"source_id": "src:001"},
            errors=[{"code": "policy_violation", "message": "denied", "retryable": False}],
            status="failed",
        )
        self.assertFalse(should_retry(message))

    def test_retryable_error(self):
        message = create_message(
            message_type="SourceDiscovered",
            agent_id="agent:research:001",
            department="research",
            mission_id="mission:test:001",
            payload={
                "source_candidate_id": "artifact:001",
                "title": "Guide",
            },
            errors=[{"code": "transport_timeout", "message": "timeout", "retryable": True}],
            status="failed",
            retry_count=1,
        )
        self.assertTrue(should_retry(message))


if __name__ == "__main__":
    unittest.main()
