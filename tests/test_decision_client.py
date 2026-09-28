import json

from agentic_aiops.decision_client import HttpDecisionClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {
                "action": "EXECUTE",
                "decision": {
                    "candidate": "execute",
                    "confidence": 0.93,
                },
            }
        ).encode("utf-8")


def test_http_decision_client(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(
            req.data.decode("utf-8")
        )
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        "agentic_aiops.decision_client.request.urlopen",
        fake_urlopen,
    )

    client = HttpDecisionClient(
        "http://decision.local",
        timeout_seconds=2.0,
    )
    result = client.decide(
        decision_type="escalation",
        candidates=["execute", "fallback", "human_review"],
        context={"action_kind": "read"},
    )

    assert captured["url"] == "http://decision.local/decision"
    assert captured["timeout"] == 2.0
    assert result["decision"]["candidate"] == "execute"
