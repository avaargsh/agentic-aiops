import json

from agentic_aiops.http_client import JsonHttpClient
from agentic_aiops.kubernetes_tool import (
    KubernetesListTool,
)
from agentic_aiops.models import Incident
from agentic_aiops.prometheus_tool import (
    PrometheusQuery,
    PrometheusReadTool,
)


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


def incident(scope=None):
    return Incident(
        incident_id="inc-1",
        title="checkout latency",
        severity="critical",
        scope=scope,
    )


def test_json_http_client_uses_get_and_bearer(
    monkeypatch,
) -> None:
    captured = {}

    def fake_urlopen(req, **kwargs):
        captured["method"] = req.get_method()
        captured["authorization"] = (
            req.headers.get("Authorization")
        )
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse({"ok": True})

    monkeypatch.setattr(
        "agentic_aiops.http_client.request.urlopen",
        fake_urlopen,
    )

    client = JsonHttpClient(
        bearer_token="token",
        timeout_seconds=2.0,
    )
    assert client.get_json(
        "https://example.test/api"
    ) == {"ok": True}

    assert captured["method"] == "GET"
    assert captured["authorization"] == "Bearer token"
    assert captured["timeout"] == 2.0


def test_prometheus_tool_queries_read_api_only() -> None:
    class Client:
        def __init__(self):
            self.urls = []

        def get_json(self, url):
            self.urls.append(url)
            return {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [],
                },
            }

    client = Client()
    tool = PrometheusReadTool(
        base_url="https://prom.example",
        queries=[
            PrometheusQuery(
                name="error_rate",
                promql="rate(errors[5m])",
            )
        ],
        client=client,
    )

    evidence = tool.collect(incident())

    assert len(client.urls) == 1
    assert "/api/v1/query?" in client.urls[0]
    assert evidence[0].source == "prometheus"


def test_kubernetes_tool_expands_scope_into_get_path() -> None:
    class Client:
        def __init__(self):
            self.urls = []

        def get_json(self, url):
            self.urls.append(url)
            return {
                "metadata": {
                    "resourceVersion": "42",
                },
                "items": [
                    {
                        "metadata": {
                            "name": "checkout-1",
                        }
                    }
                ],
            }

    client = Client()
    tool = KubernetesListTool(
        api_server=(
            "https://kubernetes.default.svc"
        ),
        resource_path_template=(
            "/api/v1/namespaces/{namespace}/pods"
        ),
        client=client,
    )

    evidence = tool.collect(
        incident(scope="namespace=prod")
    )

    assert client.urls == [
        (
            "https://kubernetes.default.svc"
            "/api/v1/namespaces/prod/pods"
        )
    ]
    assert evidence[0].source == "kubernetes"
    assert (
        evidence[0].attributes[
            "resource_version"
        ]
        == "42"
    )
