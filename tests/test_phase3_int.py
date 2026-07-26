"""Integration test for Phase 3 in-memory state bridge and pre-filter simulation loop."""

import pytest

pytest.importorskip("pyenergyplus")


from unittest.mock import patch


@pytest.mark.integration
def test_phase3_bridged_simulation_integration(tmp_path) -> None:
    """Verify Phase 3 bridged simulation runs end-to-end and triggers agent thread."""
    from main import run_phase3

    output_dir = str(tmp_path / "phase3_bridged_output")

    # Mock evaluate_and_act so network calls to Ollama do not block the test suite
    with patch("agent.orchestrator.LLMOrchestrator.evaluate_and_act"):
        exit_code, trigger_count = run_phase3(output_dir=output_dir)

    assert exit_code == 0, f"Phase 3 simulation failed with exit code {exit_code}"
    # In a 2-day simulation run (~48 hours), pre-filter must trigger at least once per hour
    assert trigger_count >= 24, f"Expected agent triggers >= 24, got {trigger_count}"
