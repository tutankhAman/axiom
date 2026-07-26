"""Unit and integration tests for Phase 5 experiment runner and ablation mode."""

from unittest.mock import MagicMock, patch

from agent.orchestrator import LLMOrchestrator
from bridge.state_bridge import StateBridge
from main import run_phase5
from sim.sensors import SimulationState, ZoneState


def test_orchestrator_ablation_mode_system_prompt() -> None:
    """Verify that ablation_mode=True selects the energy-only system prompt."""
    bridge = StateBridge()
    bridge.update_state(
        SimulationState(
            sim_time_hours=12.0,
            outdoor_temp=25.0,
            hvac_power_w=1000.0,
            zones={"Zone_1": ZoneState("Zone_1", 22.0, 0.0, 5.0)},
        )
    )

    orchestrator = LLMOrchestrator(bridge, ablation_mode=True)
    orchestrator.client.chat.completions.create = MagicMock()

    orchestrator.evaluate_and_act()

    # Get the system prompt passed to OpenAI completions
    call_args = orchestrator.client.chat.completions.create.call_args
    assert call_args is not None
    messages = call_args.kwargs["messages"]
    system_msg = next(m for m in messages if m["role"] == "system")

    assert "ENERGY-ONLY ABLATION MODE" in system_msg["content"]
    assert "MINIMIZE HVAC energy consumption regardless of comfort" in system_msg["content"]


def test_orchestrator_comfort_mode_system_prompt() -> None:
    """Verify that default ablation_mode=False keeps the comfort-constrained prompt."""
    bridge = StateBridge()
    bridge.update_state(
        SimulationState(
            sim_time_hours=12.0,
            outdoor_temp=25.0,
            hvac_power_w=1000.0,
            zones={"Zone_1": ZoneState("Zone_1", 22.0, 0.0, 5.0)},
        )
    )

    orchestrator = LLMOrchestrator(bridge, ablation_mode=False)
    orchestrator.client.chat.completions.create = MagicMock()

    orchestrator.evaluate_and_act()

    call_args = orchestrator.client.chat.completions.create.call_args
    assert call_args is not None
    messages = call_args.kwargs["messages"]
    system_msg = next(m for m in messages if m["role"] == "system")

    assert "ASHRAE-55 thermal comfort" in system_msg["content"]
    assert "PEAK-FLOAT SETPOINT CONTROL" in system_msg["content"]


def test_run_phase5_sync_execution(tmp_path) -> None:
    """Verify Phase 5 sync mode executes inline without spawning AgentThread."""
    output_dir = str(tmp_path / "phase5_sync_output")

    with patch("agent.orchestrator.LLMOrchestrator.evaluate_and_act") as mock_act:
        exit_code, trigger_count = run_phase5(
            output_dir=output_dir,
            sync=True,
            ablation=False,
        )

    assert exit_code == 0
    assert trigger_count >= 24
    assert mock_act.call_count == trigger_count
