from agentic_aiops.action_orchestrator import ProposedAction
from agentic_aiops.live_remediation import KubectlScaleExecutor, PrometheusPostActionVerifier


class FakeKubectl(KubectlScaleExecutor):
    def __init__(self):
        self.namespace = "golden-demo"; self.before_replicas = 2; self.after_replicas = 4; self.kubectl = "kubectl"; self.calls = []

    def _run(self, *args):
        self.calls.append(args)
        if "jsonpath={.spec.replicas}" in args:
            return "2"
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


class AlreadyDesiredKubectl(FakeKubectl):
    def _run(self, *args):
        self.calls.append(args)
        if "jsonpath={.spec.replicas}" in args:
            return "4"
        return "4" if "jsonpath={.status.readyReplicas}" in args else "ok"


def test_kubectl_executor_reconciles_after_write_success_receipt_loss():
    executor = AlreadyDesiredKubectl()

    result = executor.execute(action())

    assert not result.changed
    assert not any("--replicas=4" in call for call in executor.calls)
    assert any("rollout" in call and "status" in call for call in executor.calls)
    assert result.evidence_ids[0].endswith("desired-replicas/4")
    assert result.evidence_ids[-1].endswith("ready-replicas/4")


def test_remediation_exposes_applied_checkpoint_before_verification():
    from agentic_aiops.action_orchestrator import OrchestratedAction
    from agentic_aiops.ledger import DecisionLedgerEntry
    from agentic_aiops.policy import ActionDecision
    from agentic_aiops.remediation import SafeRemediationRunner

    order = []

    class Verifier:
        def verify(self, proposal, execution):
            order.append("verify")
            from agentic_aiops.remediation import VerificationResult
            return VerificationResult(True, ("verify://ok",), "ok")

    proposal = action()
    orchestrated = OrchestratedAction(
        proposal=proposal,
        selected_path="execute",
        model_confidence=1.0,
        decision_id="decision-001",
        policy=ActionDecision(True, False, "allowed"),
        execution_allowed=True,
        approval_required=False,
        ledger=DecisionLedgerEntry(
            decision_type="remediation",
            selected_action="execute",
            policy_reason="allowed",
            evidence_ids=(),
        ),
    )
    runner = SafeRemediationRunner(executor=FakeKubectl(), verifier=Verifier())

    result = runner.run(
        orchestrated,
        on_applied=lambda execution: order.append("applied"),
    )

    assert result.status == "VERIFIED"
    assert order == ["applied", "verify"]
