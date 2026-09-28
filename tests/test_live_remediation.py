from agentic_aiops.action_orchestrator import ProposedAction
from agentic_aiops.live_remediation import KubectlScaleExecutor, PrometheusPostActionVerifier


class FakeKubectl(KubectlScaleExecutor):
    def __init__(self):
        self.namespace = "golden-demo"; self.before_replicas = 2; self.after_replicas = 4; self.kubectl = "kubectl"; self.calls = []

    def _run(self, *args):
        self.calls.append(args)
        return "4" if "jsonpath={.status.readyReplicas}" in args else "ok"


class PromClient:
    def __init__(self, value):
        self.value = value

    def get_json(self, url):
        return {"status": "success", "data": {"result": [{"value": [1, str(self.value)]}]}}


class EventuallyPromClient:
    def __init__(self, empty_reads, value):
        self.empty_reads = empty_reads
        self.value = value
        self.calls = 0

    def get_json(self, url):
        self.calls += 1
        if self.calls <= self.empty_reads:
            return {"status": "success", "data": {"result": []}}
        return {"status": "success", "data": {"result": [{"value": [1, str(self.value)]}]}}


def action():
    return ProposedAction("scale", "deployment/checkout-api", "single-workload", True, (), "scale checkout-api 2 to 4")


def test_kubectl_executor_scales_and_waits_for_rollout():
    executor = FakeKubectl()
    result = executor.execute(action())
    assert result.changed
    assert any("--replicas=4" in call for call in executor.calls)
    assert any("rollout" in call and "status" in call for call in executor.calls)
    assert result.evidence_ids[-1].endswith("ready-replicas/4")


def test_prometheus_verifier_gates_on_post_action_latency():
    ok = PrometheusPostActionVerifier(
        "http://prometheus",
        max_latency_seconds=0.35,
        settle_seconds=0,
        sample_timeout_seconds=0,
        client=PromClient(0.18),
    )
    bad = PrometheusPostActionVerifier(
        "http://prometheus",
        max_latency_seconds=0.35,
        settle_seconds=0,
        sample_timeout_seconds=0,
        client=PromClient(0.52),
    )
    execution = FakeKubectl().execute(action())
    assert ok.verify(action(), execution).passed
    assert not bad.verify(action(), execution).passed


def test_prometheus_verifier_waits_for_first_post_action_sample():
    client = EventuallyPromClient(empty_reads=2, value=0.18)
    verifier = PrometheusPostActionVerifier(
        "http://prometheus",
        max_latency_seconds=0.35,
        settle_seconds=0,
        sample_timeout_seconds=1,
        poll_interval_seconds=0,
        client=client,
    )
    execution = FakeKubectl().execute(action())

    result = verifier.verify(action(), execution)

    assert result.passed
    assert client.calls == 3
    assert result.evidence_ids[-1].endswith("/value/0.18")
