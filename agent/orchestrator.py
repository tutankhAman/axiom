"""LLM orchestration for batched tool execution against Ollama."""

import json
import logging
import os
from typing import Any

import openai

from agent.mcp_tools import (
    TOOLS_SCHEMA,
    MCPContext,
    get_facility_meters,
    get_grid_context,
    get_zone_state,
    list_zones,
    set_zone_setpoint,
)
from bridge.state_bridge import StateBridge

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """Handles communication with the local LLM and executes returned tool calls."""

    def __init__(
        self,
        bridge: StateBridge,
        model: str = "qwen2.5:3b-instruct",
        ablation_mode: bool = False,
    ) -> None:
        self.bridge = bridge
        self.ablation_mode = ablation_mode
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        self.model = os.getenv("LLM_MODEL", model)

        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.context = MCPContext(bridge)

    def _execute_tool(self, tool_call: Any) -> str:
        """Route and execute a single tool call."""
        func_name = tool_call.function.name

        try:
            kwargs = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logger.exception("Failed to parse tool arguments for %s", func_name)
            return "Error: Invalid JSON arguments."

        logger.debug("Executing tool: %s with args %s", func_name, kwargs)

        try:
            if func_name == "list_zones":
                return json.dumps(list_zones(self.context))
            elif func_name == "get_zone_state":
                return json.dumps(get_zone_state(self.context, **kwargs))
            elif func_name == "get_facility_meters":
                return json.dumps(get_facility_meters(self.context))
            elif func_name == "get_grid_context":
                return json.dumps(get_grid_context(self.context))
            elif func_name == "set_zone_setpoint":
                return set_zone_setpoint(self.context, **kwargs)
            else:
                logger.error("Tool '%s' not found.", func_name)
                return f"Error: Tool '{func_name}' not found."
        except Exception:
            logger.exception("Error executing tool %s", func_name)
            return "Error executing tool."

    def evaluate_and_act(self) -> None:
        """Fetch state, build batched prompt, call LLM, and execute tool calls."""
        state = self.bridge.get_latest_state()
        if not state:
            return

        zones_summary = "\n".join(
            f"- {z}: Temp={d.mean_air_temp}C, PMV={d.pmv}" for z, d in state.zones.items()
        )

        # Synthetic grid info
        hour = int(state.sim_time_hours % 24)
        price_tier = "PEAK ($0.25/kWh)" if 14 <= hour <= 19 else "OFF-PEAK ($0.10/kWh)"

        # History and trajectory context
        history = self.bridge.get_history()
        history_str = ""
        if history:
            history_str = "Recent History (last 3 triggers):\n"
            for h in history:
                h_state = h['state']
                h_sp = h['setpoints']
                h_core = h_state.zones.get('Core_ZN')
                h_pmv = h_core.pmv if h_core else "N/A"
                h_hsp = h_sp.get("HTGSETP_SCH_NO_OPTIMUM", "N/A")
                history_str += f"  T={h_state.sim_time_hours:.2f}h: outdoor={h_state.outdoor_temp:.1f}C, hvac={h_state.hvac_power_w:.1f}W, Core_ZN PMV={h_pmv}, heat_sp={h_hsp}\n"
        else:
            history_str = "Recent History: None yet.\n"

        # Current setpoints
        curr_cmds = self.bridge.get_actuation_commands()
        curr_heat = curr_cmds.get("HTGSETP_SCH_NO_OPTIMUM", 20.0)
        curr_cool = curr_cmds.get("CLGSETP_SCH_NO_OPTIMUM", 25.0)

        if self.ablation_mode:
            system_prompt = (
                "You are an AI building control agent in ENERGY-ONLY ABLATION MODE. "
                "Your sole objective is to MINIMIZE HVAC energy consumption regardless of comfort. "
                "You may ignore PMV comfort bounds and aggressively widen setpoints to save power. "
                "You control HTGSETP_SCH_NO_OPTIMUM and CLGSETP_SCH_NO_OPTIMUM by emitting "
                "set_zone_setpoint tool calls."
            )
        else:
            system_prompt = (
                "You are an AI building control agent. Your goal is to minimize HVAC power "
                "while keeping zone PMV comfort strictly between -0.5 and +0.5.\n\n"
                "STRATEGY RULES (apply in order, use your judgment only when none fire):\n"
                "0. DEFAULT OCCUPIED STATE: If everything is normal, maintain Heat=21.0°C, Cool=24.0°C.\n"
                "1. DO NOT FREEZE OCCUPANTS. If PMV < -0.5 in ANY zone, you MUST increase heating setpoint (e.g. 21.5-22.5°C).\n"
                "2. If all zones PMV ∈ [-0.2, +0.5] AND outdoor < 5°C → heating may drop slightly to 19.0-20.0°C (building has internal gains).\n"
                "3. If hour ∈ [14,19] (PEAK pricing) AND PMV > -0.3 → widen heating band to 18.0°C to reduce demand.\n"
                "4. If |PMV| > 0.5 in any zone → tighten the violated direction first, then optimise energy.\n"
                "5. Absolute limits: heat_min=15.0°C, heat_max=24.0°C, cool_min=22.0°C, cool_max=30.0°C.\n\n"
                "DEMAND RESPONSE PROTOCOL:\n"
                "- PRE-COOLING/HEATING WINDOW (hours 11-13, just before peak): If PMV allows, pre-heat/cool the building "
                "using cheap off-peak power, so the building's thermal mass can coast through the peak afternoon hours.\n"
                "- PEAK SHEDDING (hours 14-19): Widen setpoints to shed load. Accept PMV closer to the ±0.5 bounds.\n\n"
                "Your task: Make the SMALLEST ADJUSTMENT that satisfies both comfort and energy goals. "
                "Prefer increments of 0.5-1.0°C rather than jumping to extremes. You control the global schedules "
                "HTGSETP_SCH_NO_OPTIMUM and CLGSETP_SCH_NO_OPTIMUM by emitting set_zone_setpoint tool calls. "
                "Always emit a tool call if comfort is violated."
            )

        # Call tools explicitly to get the weather forecast and other grid context before formulating the user prompt
        # We don't have to invoke the LLM for it since we can just use the python functions locally
        grid_ctx = get_grid_context(self.context)
        forecast_12h = grid_ctx.get("forecast_12h_c", [])
        forecast_str = f"12h Forecast: {[round(t,1) for t in forecast_12h[:6]]}... (C)"

        user_prompt = (
            f"Current Time: {state.sim_time_hours:.2f}h (Hour {hour}). Grid: {price_tier}\n"
            f"Outdoor Temp: {state.outdoor_temp:.1f}C. {forecast_str}\n"
            f"HVAC Power: {state.hvac_power_w:.1f}W (Cumulative: {state.cumulative_hvac_kwh:.2f} kWh)\n"
            f"Occupancy: {'OCCUPIED' if state.is_occupied else 'UNOCCUPIED'}\n\n"
            f"Current active setpoints: Heat={curr_heat:.1f}C, Cool={curr_cool:.1f}C\n\n"
            f"{history_str}\n"
            f"Zone States:\n{zones_summary}\n\n"
            "Evaluate comfort and energy, and use set_zone_setpoint to adjust if necessary."
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # ty: ignore[invalid-argument-type]
                tools=TOOLS_SCHEMA,  # type: ignore
                timeout=15.0,  # Strict timeout to prevent hanging the loop
            )

            message = response.choices[0].message
            if message.tool_calls:
                messages.append(message)  # type: ignore[arg-type]
                has_getter_tool = False
                for tool_call in message.tool_calls:
                    if tool_call.function.name != "set_zone_setpoint":
                        has_getter_tool = True
                    result = self._execute_tool(tool_call)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
                if has_getter_tool:
                    try:
                        self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,  # ty: ignore[invalid-argument-type]
                            tools=TOOLS_SCHEMA,  # type: ignore
                            timeout=15.0,
                        )
                    except Exception:
                        logger.exception("Follow-up LLM completion failed after tool execution.")
            else:
                logger.debug("LLM responded with no tool calls. Holding current setpoints.")

        except Exception:
            # FALLBACK PATH: Log error and suppress. Zero-Order Hold continues.
            logger.exception("LLM evaluation failed. Falling back to Zero-Order Hold.")
