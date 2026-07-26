"""Tests for MCP tools."""

from agent.mcp_tools import MCPContext, set_zone_setpoint
from bridge.state_bridge import StateBridge


def test_set_zone_setpoint_clamping() -> None:
    bridge = StateBridge()
    context = MCPContext(bridge)

    # Test out-of-bounds heating (too high) and cooling (too low)
    result = set_zone_setpoint(
        context,
        zone_id="Zone_1",
        heating_c=100.0,
        cooling_c=-10.0,
        reason="I am crazy",
    )

    assert "Success" in result

    commands = bridge.get_actuation_commands()

    # Heating clamped to max 24.0
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 24.0
    # Cooling clamped to min 22.0, but because cooling must be > heating, it should be 25.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 25.0


def test_set_zone_setpoint_normal() -> None:
    bridge = StateBridge()
    context = MCPContext(bridge)

    set_zone_setpoint(
        context,
        zone_id="Zone_1",
        heating_c=20.0,
        cooling_c=26.0,
        reason="Normal operation",
    )

    commands = bridge.get_actuation_commands()
    assert commands["HTGSETP_SCH_NO_OPTIMUM"] == 20.0
    assert commands["CLGSETP_SCH_NO_OPTIMUM"] == 26.0
