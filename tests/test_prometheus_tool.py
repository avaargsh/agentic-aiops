from agentic_aiops.http_client import JsonHttpClient
from agentic_aiops.models import Incident
from agentic_aiops.prometheus_tool import (
    PrometheusQuery,
    PrometheusReadTool,
)


def test_prometheus_read_tool(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return (
                b'{"status":"success","data":'
                b'{"resultType":"vector","result":'
                b'[{"metric":{"pod":"checkout-1"},'
                b'"value":[1,"0.92"]}]}}'
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

    tool = PrometheusReadTool(
        base_url="https://prom.example",
        queries=[
            PrometheusQuery(
                name="cpu",
                promql="rate(cpu_total[5m])",
            )
        ],
        client=JsonHttpClient(),
    )

    evidence = tool.collect(
        Incident(
            "inc-1",
            "cpu high",
            "sev2",
        )
    )

    assert captured["method"] == "GET"
    assert "/api/v1/query?" in captured["url"]
    assert len(evidence) == 1
    assert "1 series returned" in evidence[0].observation
    assert evidence[0].attributes["query_name"] == "cpu"
