"""Tests for the LLM Orchestrator."""

import json
from unittest.mock import MagicMock

import openai

from agent.orchestrator import LLMOrchestrator
from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState, ZoneState


def test_orchestrator_handles_timeout(caplog) -> None:
    bridge = StateBridge()
    # Push dummy state
    bridge.update_state(
        SimulationState(
            sim_time_hours=12.0,
            outdoor_temp=25.0,
            hvac_power_w=1000.0,
            zones={"Zone_1": ZoneState("Zone_1", 22.0, 0.0, 5.0)},
        )
    )

    orchestrator = LLMOrchestrator(bridge)

    # Mock the openai client to throw a timeout
    orchestrator.client.chat.completions.create = MagicMock(
        side_effect=openai.APITimeoutError(request=MagicMock())
    )

    # This should not raise an exception, it should catch it and log a fallback
    orchestrator.evaluate_and_act()

    assert "LLM evaluation failed" in caplog.text
    assert "Falling back to Zero-Order Hold" in caplog.text
    # Actuation commands should be empty as fallback occurred before any writes
    assert len(bridge.get_actuation_commands()) == 0


def test_orchestrator_executes_tool_call() -> None:
    bridge = StateBridge()
    bridge.update_state(
        SimulationState(
            sim_time_hours=12.0,
            outdoor_temp=25.0,
            hvac_power_w=1000.0,
            zones={"Zone_1": ZoneState("Zone_1", 22.0, 0.0, 5.0)},
        )
    )

    orchestrator = LLMOrchestrator(bridge)

    # Create a mock response
    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "set_zone_setpoint"
    mock_tool_call.function.arguments = json.dumps(
        {"zone_id": "Zone_1", "heating_c": 21.0, "cooling_c": 25.0, "reason": "Optimize comfort"}
    )
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [mock_tool_call]

    orchestrator.client.chat.completions.create = MagicMock(return_value=mock_response)

    orchestrator.evaluate_and_act()

    commands = bridge.get_actuation_commands()
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 21.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 25.0
