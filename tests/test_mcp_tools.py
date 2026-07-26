"""Tests for MCP tools."""

from agent.mcp_tools import MCPContext, get_building_context, set_zone_setpoint
from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState, ZoneState


def test_set_zone_setpoint_clamping() -> None:
    bridge = StateBridge()
    context = MCPContext(bridge)
    # Set simulated state at hour 10.0 (morning ramp period, 26.0-27.0°C band)
    bridge.update_state(
        SimulationState(
            sim_time_hours=10.0,
            outdoor_temp=28.0,
            hvac_power_w=3000.0,
            is_occupied=True,
            zones={"Core_ZN": ZoneState("Core_ZN", 25.0, 0.1, 5.0)},
        )
    )

    # Test out-of-bounds cooling (too low: -10.0) -> clamps to 26.0 morning ramp floor
    result = set_zone_setpoint(
        context,
        heating_c=100.0,
        cooling_c=-10.0,
        reason="Test out of bounds",
    )

    assert "Success" in result
    commands = bridge.get_actuation_commands()
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 15.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 26.0


def test_set_zone_setpoint_peak_shedding() -> None:
    bridge = StateBridge()
    context = MCPContext(bridge)
    # Set simulated state at hour 15.0 (peak occupied, 29.0-30.0°C band)
    bridge.update_state(
        SimulationState(
            sim_time_hours=15.0,
            outdoor_temp=33.0,
            hvac_power_w=5000.0,
            is_occupied=True,
            zones={"Core_ZN": ZoneState("Core_ZN", 26.0, 0.3, 8.0)},
        )
    )

    set_zone_setpoint(
        context,
        heating_c=15.0,
        cooling_c=29.5,  # Within peak band 29.0-30.0°C
        reason="Peak coasting operation",
    )

    commands = bridge.get_actuation_commands()
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 15.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 29.5


def test_get_building_context() -> None:
    bridge = StateBridge()
    context = MCPContext(bridge)

    bridge.update_state(
        SimulationState(
            sim_time_hours=14.0,
            outdoor_temp=5.0,
            hvac_power_w=5000.0,
            is_occupied=True,
            zones={"Core_ZN": ZoneState("Core_ZN", 20.0, -0.6, 12.0)},
        )
    )

    ctx_data = get_building_context(context)
    assert ctx_data["is_peak_pricing"] is True
    assert ctx_data["comfort_status"] == "slight_cold"
    assert ctx_data["worst_pmv"] == -0.6
