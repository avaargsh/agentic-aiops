from agentic_aiops.eval_gate import evaluate_golden_release


def post(status="VERIFIED", evidence=("prometheus://query/latency/value/0.18",)):
    return {
        "status": status,
        "verification_evidence_ids": list(evidence),
    }


def test_eval_gate_promotes_verified_provenance_chain():
    result = evaluate_golden_release(
        release_ref="checkout-sre-golden-v1",
        runtime_run_id="run-001",
        remediation_status="VERIFIED",
        provenance_valid=True,
        post_action=post(),
    )
    assert result.passed is True


def test_eval_gate_blocks_invalid_provenance():
    result = evaluate_golden_release(
        release_ref="checkout-sre-golden-v1",
        runtime_run_id="run-001",
        remediation_status="VERIFIED",
        provenance_valid=False,
        post_action=post(),
    )
    assert result.passed is False
    assert "provenance" in result.reason


def test_eval_gate_blocks_missing_post_action_evidence():
    result = evaluate_golden_release(
        release_ref="checkout-sre-golden-v1",
        runtime_run_id="run-001",
        remediation_status="VERIFIED",
        provenance_valid=True,
        post_action=post(evidence=()),
    )
    assert result.passed is False
    assert "verification evidence" in result.reason


def test_eval_gate_blocks_rollback():
    result = evaluate_golden_release(
        release_ref="checkout-sre-golden-v1",
        runtime_run_id="run-001",
        remediation_status="ROLLED_BACK",
        provenance_valid=True,
        post_action=post(status="ROLLED_BACK"),
    )
    assert result.passed is False
