"""Tests for the LLM Orchestrator."""

import json
from unittest.mock import MagicMock

import openai

from agent.orchestrator import LLMOrchestrator
from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState, ZoneState


def test_orchestrator_handles_timeout(caplog) -> None:
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

    orchestrator.client.chat.completions.create = MagicMock(
        side_effect=openai.APITimeoutError(request=MagicMock())
    )

    orchestrator.evaluate_and_act()

    assert "LLM evaluation timed out" in caplog.text
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

    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "set_zone_setpoint"
    mock_tool_call.function.arguments = json.dumps(
        {"heating_c": 15.0, "cooling_c": 26.0, "reason": "Optimize comfort"}
    )
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tool_call]

    orchestrator.client.chat.completions.create = MagicMock(return_value=mock_response)

    orchestrator.evaluate_and_act()

    commands = bridge.get_actuation_commands()
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 15.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 26.0


def test_coerce_scalar_handles_lists() -> None:
    from agent.orchestrator import _coerce_scalar

    assert _coerce_scalar([25.5, 26.0], 27.0) == 25.5
    assert _coerce_scalar([], 27.0) == 27.0
    assert _coerce_scalar("26.5", 27.0) == 26.5
    assert _coerce_scalar(None, 27.0) is None
    assert _coerce_scalar("invalid", 27.0) == 27.0
