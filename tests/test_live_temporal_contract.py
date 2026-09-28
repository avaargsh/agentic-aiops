from pathlib import Path

def test_live_cli_removed_manual_approval_flag():
    source = Path("examples/live_golden_incident.py").read_text()
    legacy_flag = "--" + "approved"
    assert legacy_flag not in source
    assert "start" in source
    assert "continue" in source
    assert "status" in source

def test_live_shell_returns_control_to_temporal():
    source = Path("scripts/run-live-golden-incident.sh").read_text()
    assert "approval_resolved" in source
    assert "continue --run-id" in source
