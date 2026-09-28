from agentic_aiops.http_client import JsonHttpClient
from agentic_aiops.kubernetes_tool import (
    KubernetesListTool,
    parse_scope,
)
from agentic_aiops.models import Incident


def test_parse_scope() -> None:
    assert parse_scope(
        "cluster=prod-a,namespace=checkout"
    ) == {
        "cluster": "prod-a",
        "namespace": "checkout",
    }


def test_kubernetes_list_tool_is_get_only(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return (
                b'{"metadata":{"resourceVersion":"42"},'
                b'"items":[{"metadata":{"name":"checkout-1"}},'
                b'{"metadata":{"name":"checkout-2"}}]}'
            )

    def fake_urlopen(
        req,
        timeout,
        context,
    ):
        captured["url"] = req.full_url
        captured["method"] = req.method
        return Response()

    monkeypatch.setattr(
        "agentic_aiops.http_client.request.urlopen",
        fake_urlopen,
    )

    tool = KubernetesListTool(
        api_server="https://kube.example",
        resource_path_template=(
            "/api/v1/namespaces/{namespace}/pods"
        ),
        client=JsonHttpClient(
            bearer_token="demo-token",
        ),
    )

    evidence = tool.collect(
        Incident(
            "inc-1",
            "latency",
            "sev2",
            scope=(
                "cluster=prod-a,"
                "namespace=checkout"
            ),
        )
    )

    assert captured["method"] == "GET"
    assert captured["url"].endswith(
        "/api/v1/namespaces/checkout/pods"
    )
    assert len(evidence) == 1
    assert "2 objects returned" in evidence[0].observation
    assert evidence[0].attributes[
        "resource_version"
    ] == "42"
