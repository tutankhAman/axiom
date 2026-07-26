"""LLM orchestration for batched tool execution against Ollama."""

import json
import logging
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

    def __init__(self, bridge: StateBridge, model: str = "qwen2.5:7b-instruct") -> None:
        self.bridge = bridge
        self.model = model
        # Ollama provides an OpenAI-compatible API on port 11434
        self.client = openai.OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # API key is ignored by Ollama, but required by OpenAI client
        )
        self.context = MCPContext(bridge)

    def _execute_tool(self, tool_call: Any) -> str:
        """Route and execute a single tool call."""
        func_name = tool_call.function.name

        try:
            kwargs = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse tool arguments for %s: %s", func_name, e)
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
                return f"Error: Tool '{func_name}' not found."
        except Exception as e:
            logger.error("Error executing tool %s: %s", func_name, e)
            return f"Error executing tool: {e}"

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

        system_prompt = (
            "You are an AI building control agent. Your goal is to minimize HVAC power "
            "while keeping zone PMV comfort strictly between -0.5 and +0.5. "
            "You control the global baseline schedules HTGSETP_SCH_NO_OPTIMUM "
            "and CLGSETP_SCH_NO_OPTIMUM by emitting set_zone_setpoint tool calls. "
            "Always emit a tool call if comfort is violated. "
            "You may widen setpoints to save energy during off-peak hours."
        )

        user_prompt = (
            f"Current Time: {state.sim_time_hours:.2f}h (Hour {hour}). Grid: {price_tier}\n"
            f"Outdoor Temp: {state.outdoor_temp:.1f}C. HVAC Power: {state.hvac_power_w:.1f}W\n"
            f"Zone States:\n{zones_summary}\n\n"
            "Evaluate comfort and energy, and use set_zone_setpoint to adjust if necessary."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=TOOLS_SCHEMA,  # type: ignore
                timeout=15.0,  # Strict timeout to prevent hanging the loop
            )

            message = response.choices[0].message
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    self._execute_tool(tool_call)
            else:
                logger.debug("LLM responded with no tool calls. Holding current setpoints.")

        except Exception as e:
            # FALLBACK PATH: Log error and suppress. Zero-Order Hold continues.
            logger.error("LLM evaluation failed: %s. Falling back to Zero-Order Hold.", e)
