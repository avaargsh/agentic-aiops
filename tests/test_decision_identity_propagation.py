from agentic_aiops.action_orchestrator import ActionOrchestrator, ProposedAction


class Client:
    def decide(self, **kwargs):
        return {
            "decision_id": "decision-sha256:" + "a" * 64,
            "decision": {"candidate": "execute", "confidence": 0.93},
        }


def test_decision_identity_is_preserved_in_action_and_ledger():
    result = ActionOrchestrator(decision_client=Client()).decide(
        ProposedAction("read", "deployment/checkout", "read-only", True, ("e-1",)),
        evidence_digest="sha256:" + "b" * 64,
    )
    assert result.decision_id == "decision-sha256:" + "a" * 64
    assert result.ledger.attributes["decision_id"] == result.decision_id
    assert result.ledger.attributes["evidence_digest"] == "sha256:" + "b" * 64
