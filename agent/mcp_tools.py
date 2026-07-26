"""MCP tool surface definitions for the LLM agent."""

import logging
from typing import Any

from bridge.state_bridge import StateBridge

logger = logging.getLogger(__name__)


class MCPContext:
    """Provides tools with access to the StateBridge."""

    def __init__(self, bridge: StateBridge):
        self.bridge = bridge


def list_zones(context: MCPContext) -> list[str]:
    """Return a list of all zone IDs in the building."""
    state = context.bridge.get_latest_state()
    if not state:
        return []
    return list(state.zones.keys())


def get_zone_state(context: MCPContext, zone_id: str) -> dict[str, Any]:
    """Get the current temperature and comfort (PMV) readings for a specific zone."""
    state = context.bridge.get_latest_state()
    if not state or zone_id not in state.zones:
        return {"error": f"Zone {zone_id} not found."}

    zone = state.zones[zone_id]
    return {
        "zone_name": zone.zone_name,
        "mean_air_temp_c": zone.mean_air_temp,
        "pmv": zone.pmv,
        "ppd": zone.ppd,
    }


def get_facility_meters(context: MCPContext) -> dict[str, Any]:
    """Get the current HVAC electricity demand for the facility."""
    state = context.bridge.get_latest_state()
    return {"hvac_power_w": state.hvac_power_w if state else 0.0}


def get_grid_context(context: MCPContext) -> dict[str, Any]:
    """Get grid context including outdoor temperature and current time-of-use price."""
    state = context.bridge.get_latest_state()
    if not state:
        return {"outdoor_temp_c": 20.0, "electricity_price": 0.10}

    # Synthetic time-of-use pricing based on hour of day
    hour = int(state.sim_time_hours % 24)
    price = 0.25 if 14 <= hour <= 19 else 0.10  # Peak pricing 2pm-7pm

    return {
        "outdoor_temp_c": state.outdoor_temp,
        "electricity_price_usd_kwh": price,
        "is_peak_pricing": price == 0.25,
    }


def set_zone_setpoint(
    context: MCPContext,
    zone_id: str,
    heating_c: float,
    cooling_c: float,
    reason: str,
) -> str:
    """Set the target heating and cooling setpoints for a specific zone.

    The reason argument is mandatory to provide an audit trail of agent reasoning.
    """
    # CLAMPING: System Integration Priority #1 - Protect the simulation from out-of-bounds writes
    clamped_heat = max(15.0, min(24.0, heating_c))
    clamped_cool = max(22.0, min(30.0, cooling_c))

    # Ensure cooling is higher than heating to prevent fighting
    if clamped_cool <= clamped_heat:
        clamped_cool = clamped_heat + 1.0

    current_commands = context.bridge.get_actuation_commands()

    # Map zone_id to generic schedule names since baseline IDF uses global schedules
    # (In a real multi-zone setup, each zone would have its own schedule name)
    # For now, we actuate the global baseline schedules that govern all zones
    current_commands["HTGSETP_SCH_NO_OPTIMUM"] = clamped_heat
    current_commands["CLGSETP_SCH_NO_OPTIMUM"] = clamped_cool
    current_commands["HTGSETP_SCH_NO_OPTIMUM_w_SB"] = clamped_heat
    current_commands["CLGSETP_SCH_NO_OPTIMUM_w_SB"] = clamped_cool

    context.bridge.set_actuation_commands(current_commands)

    logger.info(
        "Agent decided for %s: Heat=%.2f°C, Cool=%.2f°C | Reason: %s",
        zone_id,
        clamped_heat,
        clamped_cool,
        reason,
    )
    return (
        f"Success: Set {zone_id} schedules to Heat={clamped_heat:.2f}C, Cool={clamped_cool:.2f}C."
    )


# OpenAI Tool Schemas
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_zones",
            "description": "Return a list of all valid zone IDs in the building.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_zone_state",
            "description": "Get current temperature and comfort (PMV) for a specific zone.",
            "parameters": {
                "type": "object",
                "properties": {"zone_id": {"type": "string", "description": "The ID of the zone"}},
                "required": ["zone_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_facility_meters",
            "description": "Get the current HVAC electricity demand for the facility in Watts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_grid_context",
            "description": "Get outdoor temperature and current time-of-use electricity price.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_zone_setpoint",
            "description": "Set the target heating and cooling setpoints for a specific zone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string"},
                    "heating_c": {
                        "type": "number",
                        "description": "Heating setpoint in Celsius (min 15.0, max 24.0)",
                    },
                    "cooling_c": {
                        "type": "number",
                        "description": "Cooling setpoint in Celsius (min 22.0, max 30.0)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Explanation of chosen setpoints based on PMV/energy goals.",
                    },
                },
                "required": ["zone_id", "heating_c", "cooling_c", "reason"],
            },
        },
    },
]
