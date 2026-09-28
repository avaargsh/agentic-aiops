from pathlib import Path


def test_disposable_k8s_stack_contains_real_incident_components():
    manifest = Path("demo/k8s/golden-stack.yaml").read_text()
    assert "name: checkout-api" in manifest
    assert "replicas: 2" in manifest
    assert "checkout_request_latency_seconds" in manifest
    assert "name: prometheus" in manifest
    assert "job_name: checkout-api" in manifest
    assert "name: load-generator" in manifest


def test_incident_script_keeps_write_action_explicit():
    script = Path("scripts/golden-incident.sh").read_text()
    assert "approve-scale" in script
    assert "scale deploy/checkout-api --replicas=4" in script


def test_temporal_compose_uses_supported_sql_backend():
    compose = Path("compose.golden.yml").read_text()
    assert "DB=postgres12" in compose
    assert "POSTGRES_SEEDS=postgresql" in compose
    assert "DB=sqlite" not in compose
