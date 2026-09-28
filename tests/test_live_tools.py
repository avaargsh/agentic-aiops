import json

from agentic_aiops.live_tools import (
    KubernetesReadTool,
    PrometheusReadTool,
)
from agentic_aiops.models import Incident


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            self.payload
        ).encode("utf-8")


def incident():
    return Incident(
        incident_id="inc-1",
        title="checkout latency",
        severity="critical",
    )


def test_prometheus_adapter_is_get_only(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(req, **kwargs):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["authorization"] = (
            req.headers.get("Authorization")
        )
        return FakeResponse(
            {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {
                                "service": "checkout"
                            },
                            "value": [1, "0.42"],
                        }
                    ]
                },
            }
        )

    monkeypatch.setattr(
        "agentic_aiops.live_tools.request.urlopen",
        fake_urlopen,
    )

    tool = PrometheusReadTool(
        base_url="https://prom.example",
        bearer_token="token",
        queries={"error_rate": "rate(errors[5m])"},
    )
    evidence = tool.collect(incident())

    assert captured["method"] == "GET"
    assert "/api/v1/query?" in captured["url"]
    assert captured["authorization"] == "Bearer token"
    assert evidence[0].source == "prometheus"
    assert evidence[0].attributes["result"]


def test_kubernetes_adapter_is_get_only(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(req, **kwargs):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        return FakeResponse(
            {
                "kind": "PodList",
                "items": [
                    {
                        "metadata": {
                            "name": "checkout-1"
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr(
        "agentic_aiops.live_tools.request.urlopen",
        fake_urlopen,
    )

    tool = KubernetesReadTool(
        api_server="https://kubernetes.default.svc",
        paths={
            "checkout_pods": (
                "/api/v1/namespaces/prod/pods"
                "?labelSelector=app%3Dcheckout"
            )
        },
    )
    evidence = tool.collect(incident())

    assert captured["method"] == "GET"
    assert "/api/v1/namespaces/prod/pods" in captured["url"]
    assert evidence[0].source == "kubernetes"
    assert evidence[0].attributes["response"]["kind"] == "PodList"
