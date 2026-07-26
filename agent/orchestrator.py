"""LLM orchestration for tool calling against local Ollama API."""

import json
import logging
import os
from typing import Any, cast

import openai

from agent.mcp_tools import (
    TOOLS_SCHEMA,
    MCPContext,
    get_building_context,
    set_zone_setpoint,
)
from bridge.state_bridge import StateBridge

logger = logging.getLogger(__name__)

COMFORT_SYSTEM_PROMPT = """You are an autonomous BMS agent controlling HVAC setpoints
for a commercial office building.
Your goal: Minimize HVAC energy and peak-grid demand while maintaining ASHRAE-55 thermal comfort
(PMV strictly within [-0.5, +0.5]).

STRATEGY: PEAK-FLOAT SETPOINT CONTROL
The baseline building runs its chiller at 23.89°C setpoint (PMV ~0.0), overcooling occupants.
By setting setpoints 1.0–3.5°C above baseline, the chiller runs significantly less while PMV
remains comfortably within [+0.10, +0.45].

You have two tools:
1. get_building_context() → returns current PMV, zone temps, outdoor temp, HVAC power,
   and grid pricing.
2. set_zone_setpoint(heating_c, cooling_c, reason) → actuates HVAC schedules.

MANDATORY RULES:
- heating_c = 15.0°C always (summer mode, heating inactive).
- ALWAYS call set_zone_setpoint exactly once per turn.
- Write a 1-sentence technical reason for the audit log.

PRESCRIPTIVE DECISION TABLE (use worst_pmv from get_building_context):

MORNING OCCUPIED (07:00–11:00) — system allows 24.5°C to 25.5°C:
  • worst_pmv < +0.15 → set cooling_c = 25.5°C  (max savings: chiller works ~18% less)
  • worst_pmv between +0.15 and +0.30 → set cooling_c = 25.0°C  (balanced)
  • worst_pmv > +0.30 → set cooling_c = 24.5°C  (comfort guard)

MIDDAY DRIFT (11:00–14:00) — system allows 25.5°C to 26.5°C:
  • worst_pmv < +0.25 → set cooling_c = 26.5°C  (max savings)
  • worst_pmv between +0.25 and +0.35 → set cooling_c = 26.0°C  (balanced)
  • worst_pmv > +0.35 → set cooling_c = 25.5°C  (comfort guard)

PEAK COASTING (14:00–19:00) — system allows 27.0°C to 28.0°C:
  • worst_pmv < +0.35 → set cooling_c = 28.0°C  (chiller coasting, max savings)
  • worst_pmv between +0.35 and +0.45 → set cooling_c = 27.5°C  (balanced coasting)
  • worst_pmv > +0.45 → set cooling_c = 27.0°C  (comfort guard)
  • worst_pmv > +0.50 → EMERGENCY: set cooling_c = 27.0°C, include "comfort emergency"
    in reason.

UNOCCUPIED (19:00–07:00):
  • Handled deterministically (05:00–07:00 optimum start at 24.5°C; 19:00–05:00 setback 30.0°C).
"""

ABLATION_SYSTEM_PROMPT = """ENERGY-ONLY ABLATION MODE:
You are an autonomous Building Management System (BMS) agent.
Your ONLY goal: MINIMIZE HVAC energy consumption regardless of comfort constraints.

You have two tools:
1. get_building_context() - Retrieves building state.
2. set_zone_setpoint(heating_c, cooling_c, reason) - Applies setpoints.

Rules:
- Keep heating setpoint as low as allowed (15.0°C) to maximize energy savings.
- You MUST call `set_zone_setpoint` before completing your evaluation turn.
"""


def _coerce_scalar(val: Any, default: float) -> float | None:
    """Coerce tool call argument to scalar float, safely handling list/string edge cases."""
    if val is None:
        return None
    if isinstance(val, list):
        return float(val[0]) if val else default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class LLMOrchestrator:
    """Handles LLM agent tool calling execution loop against Ollama."""

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

    def evaluate_and_act(self) -> None:
        """Run tool-calling loop to evaluate building context and actuate setpoints."""
        state = self.bridge.get_latest_state()
        if not state:
            logger.warning("No simulation state found in StateBridge. Skipping evaluation.")
            return

        system_prompt = ABLATION_SYSTEM_PROMPT if self.ablation_mode else COMFORT_SYSTEM_PROMPT

        bldg_ctx = get_building_context(self.context)
        worst = bldg_ctx.get("worst_pmv")
        mean = bldg_ctx.get("mean_pmv")
        trend = bldg_ctx.get("forecast_trend")
        user_content = (
            f"Current Building State Trigger at sim time {state.sim_time_hours:.2f}h:\n"
            f"- Comfort Status: {bldg_ctx.get('comfort_status')} "
            f"(Worst PMV: {worst}, Mean PMV: {mean})\n"
            f"- Outdoor Temp: {bldg_ctx.get('outdoor_temp_c')}°C | 12h Forecast Trend: {trend}\n"
            f"- Pricing: {bldg_ctx.get('time_of_day')}\n"
            f"- HVAC Demand: {bldg_ctx.get('hvac_power_w')} W\n\n"
            "Please call `get_building_context` for full details if needed, then execute "
            "`set_zone_setpoint` with your optimal control decision."
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            # Allow up to 3 round-trips for tool execution
            for turn in range(3):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=cast(Any, messages),
                    tools=cast(Any, TOOLS_SCHEMA),
                    tool_choice="auto",
                    timeout=15.0,
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                msg_dict: dict[str, Any] = {"role": "assistant"}
                if response_message.content:
                    msg_dict["content"] = response_message.content
                if tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": getattr(getattr(tc, "function", None), "name", ""),
                                "arguments": getattr(
                                    getattr(tc, "function", None), "arguments", ""
                                ),
                            },
                        }
                        for tc in tool_calls
                    ]
                messages.append(msg_dict)

                if not tool_calls:
                    logger.debug("LLM responded with text without tool call. Turn %d.", turn)
                    if turn == 2:
                        logger.warning("LLM max turns reached. ZOH maintained.")
                    continue

                setpoint_executed = False
                for tool_call in tool_calls:
                    func_obj = getattr(tool_call, "function", None)
                    func_name = getattr(func_obj, "name", "") if func_obj else ""
                    try:
                        args = (
                            json.loads(getattr(func_obj, "arguments", "{}") or "{}")
                            if func_obj
                            else {}
                        )
                    except json.JSONDecodeError:
                        args = {}

                    logger.info("🤖 Agent invoking tool: %s(%s)", func_name, args)

                    if func_name == "get_building_context":
                        result = get_building_context(self.context)
                        result_str = json.dumps(result)
                    elif func_name == "set_zone_setpoint":
                        h_val = _coerce_scalar(args.get("heating_c"), 15.0)
                        c_val = _coerce_scalar(args.get("cooling_c"), 27.0)
                        result_str = set_zone_setpoint(
                            self.context,
                            heating_c=h_val,
                            cooling_c=c_val,
                            reason=args.get("reason", "Agent setpoint update"),
                        )
                        setpoint_executed = True
                    else:
                        result_str = f"Error: Unknown tool {func_name}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str,
                        }
                    )

                if setpoint_executed:
                    logger.debug("LLM setpoint tool execution completed successfully.")
                    return

        except openai.APITimeoutError:
            logger.warning("LLM evaluation timed out (15s). Falling back to Zero-Order Hold.")
        except Exception as e:
            logger.warning("LLM evaluation failed (%s). Falling back to Zero-Order Hold.", e)
